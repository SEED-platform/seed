# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from copy import copy

from django.db import models
from django.core.exceptions import ValidationError

from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedToken

from quantityfield.units import ureg

from seed.landing.models import Organization
from seed.models.columns import Column
from seed.models.properties import PropertyState
from seed.models.tax_lots import TaxLotState


def _cast_params_to_floats(params):
    """Helper to turn dict values to floats or remove them if non-numeric

    :param params: dict{str: <value>}
    :return: dict{str: float}
    """
    tmp_params = {}
    for key, value in params.items():
        # handle booleans as special case b/c float(True) == 1.0 which we don't want
        if isinstance(value, bool):
            continue

        if isinstance(value, ureg.Quantity):
            value = value.magnitude

        try:
            tmp_params[key] = float(value)
        except Exception:
            continue
    return tmp_params


class ExpressionEvaluator:
    """Wrapper class providing repeated evaluation expressions with different parameters"""

    # grammar used to parse and transform expressions
    EXPRESSION_GRAMMAR = """
    ?start: sum

    // rules with lowest precedence
    ?sum: product
        | sum "+" product                       -> add
        | sum "-" product                       -> sub

    // rules with higher precedence
    ?product: atom
        | product "*" atom                      -> mul
        | product "/" atom                      -> div
        | product "%" atom                      -> mod

    // rules with highest precedence
    ?atom: NUMBER                               -> number
         | "-" atom                             -> neg
         | atom "**" atom                       -> pow
         | "$" NAME                             -> param
         | "(" sum ")"
         | "abs(" sum ")"                       -> abs
         | "min(" sum "," sum ( "," sum )* ")"  -> min
         | "max(" sum "," sum ( "," sum )* ")"  -> max

    %import common.CNAME -> NAME
    %import common.NUMBER
    %import common.WS_INLINE

    %ignore WS_INLINE
    """

    @v_args(inline=True)
    class EvaluateTree(Transformer):
        """Transforms expression tree into a result by applying operations.
        Should be used with the expression grammar above
        """
        from operator import (
            add,
            sub,
            mul,
            truediv as div,
            neg,
            mod
        )

        number = float
        min = min
        max = max
        pow = pow
        abs = abs

        def __init__(self):
            self.params = {}

        def param(self, name):
            try:
                return self.params[name]
            except KeyError:
                raise KeyError("Parameter not found: %s" % name)

        def set_params(self, params):
            """Set the parameters available when parsing

            :param params: dict, key is parameter name (without $ prefix), value is value
            """
            self.params = params

    def __init__(self, expression, validate=True):
        """Construct an expression evaluator.

        :param expression: str
        :param validate: bool, optional
        """
        self._expression = expression
        if validate:
            self.is_valid(expression)

        self._transformer = self.EvaluateTree()
        self._parser = Lark(self.EXPRESSION_GRAMMAR, parser='lalr', transformer=self._transformer)

    @classmethod
    def is_valid(cls, expression):
        """Validate the expression. Raises an InvalidExpression exception if invalid

        :param expression: str
        :return: bool
        """
        try:
            Lark(cls.EXPRESSION_GRAMMAR, parser='lalr').parse(expression)
        except UnexpectedToken as e:
            raise InvalidExpression(expression, e.pos_in_stream)

        return True

    def evaluate(self, parameters=None):
        """Evaluate the expression with the provided parameters

        :param parameters: dict, keys are parameter names and values are values
        :return: float
        """
        if parameters is None:
            parameters = {}

        self._transformer.set_params(parameters)
        return self._parser.parse(self._expression)


class InvalidExpression(Exception):
    """Raised when parsing an expression"""
    def __init__(self, expression, error_position=None):
        super().__init__()
        self.expression = expression
        self.error_position = error_position

    def __str__(self):
        expression_message = self.expression
        if self.error_position is not None:
            error_pos_to_end = self.expression[self.error_position:]
            truncated_error = (error_pos_to_end[:5] + '...') if len(error_pos_to_end) > 8 else error_pos_to_end
            expression_message = f'starting at "{truncated_error}"'

        return f'Expression is not valid: {expression_message}'


class DerivedColumn(models.Model):
    """
    The DerivedColumn model represents a user defined expression which includes
    references to other columns.

    For example, if a user wanted to calculate the percentage of conditioned floor
    area they could use conditioned floor area and gross floor area:
        ($conditioned_floor_area / $gross_floor_area) * 100
    """
    PROPERTY_TYPE = 0
    TAXLOT_TYPE = 1
    INVENTORY_TYPES = (
        (PROPERTY_TYPE, 'Property'),
        (TAXLOT_TYPE, 'Tax Lot'),
    )

    INVENTORY_TYPE_TO_CLASS = {
        PROPERTY_TYPE: PropertyState,
        TAXLOT_TYPE: TaxLotState,
    }

    name = models.CharField(max_length=255, blank=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    inventory_type = models.IntegerField(choices=INVENTORY_TYPES)

    # expression must be valid according to the ExpressionEvaluator's grammar
    # Note that the expression can include parameter names of the format:
    #   $<valid Python identifier>
    # All parameters used in the expression must be linked to a Column through this
    # model's `source_columns` field
    expression = models.CharField(max_length=526, blank=False)
    source_columns = models.ManyToManyField(Column, through='DerivedColumnParameter')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'], name='unique_name_for_organization'
            )
        ]

    def clean(self):
        try:
            ExpressionEvaluator.is_valid(self.expression)
        except InvalidExpression as e:
            raise ValidationError({
                'expression': str(e)
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_parameter_values(self, inventory_state):
        """Construct a dictionary of column values keyed by expression parameter
        names. Note that no cleaning / validation is done to the values, they are
        straight from the database, or if a column is not found for the inventory
        its value is None.

        WARNING: this method caches the derived column sources. If any updates
        to that many-to-many field are made you must re-query for this instance.

        :param inventory_state: PropertyState | TaxlotState
        :return: dict, of the format:
            {
                <parameter name>: <column value>,
                ...
            }
        """
        assert isinstance(inventory_state, self.INVENTORY_TYPE_TO_CLASS[self.inventory_type])

        if not hasattr(self, '_cached_column_parameters'):
            self._cached_column_parameters = (
                DerivedColumnParameter.objects
                .filter(derived_column=self.id)
                .prefetch_related('source_column')
            )

        params = {}
        for parameter in self._cached_column_parameters:
            source_column_name = parameter.source_column.column_name
            value = None

            if hasattr(inventory_state, source_column_name):
                value = getattr(inventory_state, source_column_name)
            else:
                value = inventory_state.extra_data.get(source_column_name)

            params[parameter.parameter_name] = value

        return params

    def evaluate(self, inventory_state=None, parameters=None):
        """Evaluate the expression. Caller must provide `parameters`, `inventory_state`,
        or both. Values from the inventory take priority over the parameters dict.
        Values that cannot be coerced into floats (from the inventory or params dict)
        are removed before evaluating the expression.

        If the expression can't be evaluated due to invalid/missing parameters or
        a ZeroDivisionError occurs, this method returns None.

        WARNING: this method caches parts of the model. If the instance or linked
        sources are updated you must re-query to reset the cache.

        :param inventory_state: PropertyState | TaxLotState, optional, instance to get parameter data from
        :param parameters: dict, optional, defines mapping of expression parameter names to values
        :return: float | None
        """
        if not hasattr(self, '_cached_evaluator'):
            self._cached_evaluator = ExpressionEvaluator(self.expression)

        if parameters is None:
            parameters = {}

        inventory_parameters = {}
        if inventory_state is not None:
            tmp_params = self.get_parameter_values(inventory_state)
            inventory_parameters = _cast_params_to_floats(tmp_params)

        merged_parameters = copy(parameters)
        merged_parameters.update(inventory_parameters)
        merged_parameters = _cast_params_to_floats(merged_parameters)

        try:
            return self._cached_evaluator.evaluate(merged_parameters)
        except KeyError:
            # was missing one or more parameters
            return None
        except ZeroDivisionError:
            # tried to divide by zero
            return None
        except Exception as e:
            # unknown error
            raise Exception(f'Unhandled exception evaluating derived column:\n'
                            f'    derived column id: {self.id}\n'
                            f'    parameters: {merged_parameters}\n'
                            f'    expression: {self.expression}\n'
                            f'    exception: {e}')


class DerivedColumnParameter(models.Model):
    """
    The DerivedColumnParameter model is used to associate a source column with
    a parameter in an expression.
    """
    derived_column = models.ForeignKey(DerivedColumn, on_delete=models.CASCADE)
    source_column = models.ForeignKey(Column, on_delete=models.PROTECT)

    # stores the parameter name which is used for referencing the linked source column
    # in the derived column's expression
    # parameter_name must be a valid identifier according to Python
    # see: https://docs.python.org/3/reference/lexical_analysis.html#identifiers
    parameter_name = models.CharField(max_length=50, blank=False)

    class Meta:
        constraints = [
            # can't have two source columns with the same parameter_name
            models.UniqueConstraint(
                fields=['derived_column', 'parameter_name'], name='unique_parameter_name'
            ),
            # can't reference the same source column more than once
            models.UniqueConstraint(
                fields=['derived_column', 'source_column'], name='unique_reference_to_source_column'
            )
        ]

    def clean(self):
        if not self.parameter_name.isidentifier():
            raise ValidationError({
                'parameter_name': 'Not a valid identifier, see https://docs.python.org/3/reference/lexical_analysis.html#identifiers'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

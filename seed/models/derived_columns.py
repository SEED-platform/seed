# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from __future__ import annotations

import copy
from typing import Any, Union

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedToken
from quantityfield.units import ureg

from seed.landing.models import Organization
from seed.models.columns import Column
from seed.models.properties import PropertyState, PropertyView
from seed.models.tax_lots import TaxLotState, TaxLotView
from seed.utils.cache import get_cache_raw


def _cast_params_to_floats(params: dict[str, Any]) -> dict[str, float]:
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
        from operator import add, mod, mul, neg, sub  # type: ignore[misc]
        from operator import truediv as div  # type: ignore[misc]

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

    def __init__(self, expression: str, validate: bool = True):
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
    def is_valid(cls, expression: str) -> bool:
        """Validate the expression. Raises an InvalidExpression exception if invalid

        :param expression: str
        :return: bool
        """
        try:
            Lark(cls.EXPRESSION_GRAMMAR, parser='lalr').parse(expression)
        except UnexpectedToken as e:
            raise InvalidExpression(expression, e.pos_in_stream)

        return True

    def evaluate(self, parameters: Union[None, dict[str, float]] = None) -> float:
        """Evaluate the expression with the provided parameters

        :param parameters: dict, keys are parameter names and values are values
        :return: float
        """
        if parameters is None:
            parameters = {}

        self._transformer.set_params(parameters)
        return self._parser.parse(self._expression)  # type: ignore[return-value]


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
                fields=['organization', 'name', 'inventory_type'], name='unique_name_for_organization'
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
        created = not self.pk
        self.full_clean()
        save_response = super().save(*args, **kwargs)
        if self.inventory_type == 0:
            inventory_type = 'PropertyState'
        elif self.inventory_type == 1:
            inventory_type = 'TaxLotState'
        if created:
            # check if the column name already exists for the table_name
            if Column.objects.filter(organization=self.organization, table_name=inventory_type, column_name=self.name).exists():
                raise ValidationError(f'Column name {inventory_type}.{self.name} already exists, must be unique')

            Column.objects.create(
                derived_column=self,
                column_name=self.name,
                display_name=self.name,
                column_description=self.name,
                table_name=inventory_type,
                organization=self.organization,
                is_extra_data=False,
            )
        return save_response

    def get_parameter_values(self, inventory_state: Union[PropertyState, TaxLotState]) -> dict[str, Any]:
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
        import logging
        logger = logging.getLogger(__name__)
        logger.error("++++")
        logger.error("get_parameter_values")

        # check cache for parameter_dicts by org.id by derived_column.id.
        cached_derived_columns = get_cache_raw("property_derived_columns", {})  # get from cache
        derived_columns_dicts = cached_derived_columns.get(inventory_state.organization.id, {})  # by org id
        derived_column_dict = derived_columns_dicts.get(self.id, {})  # by derived column id
        parameter_dicts = derived_column_dict.get("parameters", None)  # the parameters

        # if absent, query for parameter_dicts.
        if parameter_dicts is None:
            logger.error("creating parameter_dicts")

            parameters = DerivedColumnParameter.objects.filter(derived_column_id=self.id)
            parameter_dicts = parameters.values(
                'parameter_name',
                source_column_name=F('source_column__column_name'),
                source_column_derived_column=F('source_column__derived_column'),
            )

        else:
            logger.error("found parameter_dicts")

        logger.error(parameter_dicts)

        # populate parameter_values, key are parameter_name, value are state value.
        parameter_values = {}
        for parameter in parameter_dicts:
            source_column_name = parameter['source_column_name']
            source_column_derived_column_id = parameter["source_column_derived_column_id"]

            if source_column_derived_column_id is not None:
                derived_column_dict = derived_columns_dicts.get(source_column_derived_column_id)  # by derived column id
                derived_column = DerivedColumn(
                    id=source_column_derived_column_id,
                    name=derived_column_dict["name"],
                    expression=derived_column_dict["expression"],
                )
                value = derived_column.evaluate(inventory_state)

            elif hasattr(inventory_state, source_column_name):
                value = getattr(inventory_state, source_column_name)
            else:
                value = inventory_state.extra_data.get(source_column_name)

            parameter_values[parameter['parameter_name']] = value

        return parameter_values

    def evaluate(self, inventory_state: Union[None, PropertyState, TaxLotState] = None, parameters: Union[None, dict[str, float]] = None):
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
        import logging
        logger = logging.getLogger(__name__)
        logger.error("+++++++++++")
        logger.error(f"evaluating derived column {self.id} for state {inventory_state.id}")
        logger.error("+++++++++++")

        if not hasattr(self, '_cached_evaluator'):
            self._cached_evaluator = ExpressionEvaluator(self.expression)

        if parameters is None:
            parameters = {}

        inventory_parameters = {}
        if inventory_state is not None:
            tmp_params = self.get_parameter_values(inventory_state)
            inventory_parameters = _cast_params_to_floats(tmp_params)

        merged_parameters = copy.copy(parameters)
        merged_parameters.update(inventory_parameters)
        merged_parameters = _cast_params_to_floats(merged_parameters)

        # determine if any source columns are derived_columns
        # self.check_for_source_columns_derived(inventory_state, merged_parameters)

        if any([val is None for val in merged_parameters.values()]):
            return None

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

    def check_for_source_columns_derived(self, inventory_state=None, merged_parameters={}):
        dcps = self.derivedcolumnparameter_set.all()
        for dcp in dcps:
            column = Column.objects.get(pk=dcp.source_column_id)
            if column.derived_column:
                dc = column.derived_column
                val = dc.evaluate(inventory_state)
                merged_parameters[dcp.parameter_name] = val

    def update_derived_data(self) -> None:
        """For every state with this derieved column, update the derived data for this column
        """
        inventory_type = PropertyView if self.inventory_type == 0 else TaxLotView
        views = inventory_type.objects.filter(state__organization_id=self.organization_id)
        with transaction.atomic():
            for view in views:
                state = view.state
                state.derived_data[self.name] = self.evaluate(state)
                state.save()


@receiver(post_save, sender=DerivedColumn)
def post_save_derived_column(sender, instance, **kwargs):
    """Every time the expression is updated, update the derived data for the relevant states
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"post_save_derived_column - {instance.id}")

    # TODO: this only has to happen when instance.expression is modifed. How might we ensure this
    # only happens whem needed?
    instance.update_derived_data()


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


@receiver(post_save, sender=DerivedColumnParameter)
def post_save_derived_column_parameter(sender, instance, created, **kwargs):
    """On save of a DerivedColumnParameter, it's DerivedColumn should update all relevant states derived data.
    """
    # TODO: DerivedColumnParameter with the same DerivedColumn are often create/update one right after
    # the other. How might we ensure this does get called more than needed? Perhaps with bulk creates?
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"post_save_derived_column_parameter - {instance.id}")

    derived_column = instance.derived_column
    if hasattr(derived_column, '_cached_column_parameters'):
        del derived_column._cached_column_parameters
    derived_column.update_derived_data()

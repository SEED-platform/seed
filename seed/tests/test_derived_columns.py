# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from string import Template, ascii_letters, digits

from django.core.exceptions import ValidationError

from hypothesis.extra.django import TestCase
from hypothesis import strategies as st, assume, given, example, settings

from seed.landing.models import SEEDUser as User
from seed.test_helpers.fake import FakeDerivedColumnFactory, FakeColumnFactory, FakePropertyStateFactory
from seed.models.columns import Column
from seed.models.derived_columns import (
    ExpressionEvaluator,
    DerivedColumn,
    DerivedColumnParameter,
    InvalidExpression,
)
from seed.utils.organizations import create_organization

no_deadline = settings(deadline=None)

# using 32 width b/c 64 was causing NaNs in multiplication tests (overflow I assume?)
good_floats = st.floats(allow_nan=False, allow_infinity=False, width=32)


@st.composite
def pow_st(draw, base_st=good_floats, exponent_st=good_floats.filter(lambda x: abs(x) < 10)):
    """Strategy for creating pythonic exponentiation, e.g. 1**2, 3**4, etc
    Avoids divide by zero by default

    :param base_st: Strategy, should return valid exponent bases
    :param exponent_st: Strategy, should return valid exponents
    :return: str
    """
    base = draw(base_st)
    exponent = draw(exponent_st)
    # avoid divide by zero errors
    assume(not (base == 0 and exponent < 0))
    return f'{base}**{exponent}'


@st.composite
def func_st(draw, func_name_st, args_st=good_floats, min_args=1, max_args=None):
    """Strategy which returns a string representing a function. Use min/max_args
    to create variadic funcs, or set them equal to specify the exact number

    E.g. min(1, 2, 3)
    :param func_name_st: Strategy, should return function names
    :param args_st: Strategy, should return valid argument values
    :param min_args: int, minimum number of arguments to generate
    :param max_args: int, maximum number of arguments to generate
    :return: str
    """
    func_name = draw(func_name_st)
    args = draw(st.lists(args_st, min_size=min_args, max_size=max_args))

    return f'{func_name}({", ".join(map(str, args))})'


@st.composite
def arithmetic_st(
    draw,
    operators,
    operand_st=good_floats,
    max_operands=10,
    in_parens_st=st.just(False)
):
    """Strategy for generating a chain of binary operators and operands
    E.g. 1 + 2 + 3, 4.2 * 2.1 * 0 * ..., etc

    :param operators: list[str], list of operators to choose from
    :param operand_st: Strategy, for selecting values to use in operations
    :max_operands: int, maximum number of operands
    :return: str
    """
    operands = draw(
        st.lists(
            operand_st,
            min_size=2,
            max_size=max_operands
        )
    )

    n_operators = len(operands) - 1
    operators = draw(
        st.lists(
            st.sampled_from(operators),
            min_size=n_operators,
            max_size=n_operators
        )
    )

    result = ''
    # insert an operator between each operand
    for idx, operator in enumerate(operators):
        result += f'{operands[idx]} {operators[idx]} '
    result += str(operands[-1])

    if draw(in_parens_st):
        result = f'({result})'

    return result


@st.composite
def parameter_name_st(draw):
    """Strategy for creating valid parameter names. e.g. _hello, test123, etc

    :return: str
    """
    prefix = draw(
        st.text(ascii_letters + '_', min_size=1, max_size=1)
    )
    body = draw(
        st.text(digits + ascii_letters + '_')
    )
    return f'{prefix}{body}'


# atomic strategies (excluding parameter names)
atomic_no_params_st = good_floats.map(str) \
    | pow_st() \
    | func_st(st.sampled_from(['min', 'max']), min_args=2) \
    | func_st(st.just('abs'), min_args=1, max_args=1)

# function for recursive strategy
# avoiding the division operator b/c it can cause unexpected divide by zero issues
recursive_st_func = lambda children: \
    arithmetic_st(operators=['+', '-', '*'], operand_st=children, max_operands=3, in_parens_st=st.booleans()) \
    | func_st(st.sampled_from(['min', 'max']), children, min_args=2) \
    | func_st(st.just('abs'), st.one_of(children), min_args=1, max_args=1)

# strategy for generating complex / nested expressions WITHOUT parameters
full_expression_no_params_st = st.recursive(atomic_no_params_st, recursive_st_func, max_leaves=50)


@st.composite
def full_expression_with_params_st(draw, parameters=st.dictionaries(parameter_name_st(), good_floats, min_size=1)):
    """Strategy for generating complex / nested expressions that include parameters

    :param parameters: Strategy, should provide dictionaries where keys are valid
        python var names and values are numeric
    :return: tuple(str, dict), the generated expression and parameters
    """
    params = draw(parameters)

    template_params = [f'${param_name}' for param_name in params.keys()]
    # NOTE: this won't ensure all (or even any) param names end up in the expression
    # however our evaluator should be fine with us passing extra parameters
    expression = draw(
        st.recursive(
            atomic_no_params_st | st.sampled_from(template_params),
            recursive_st_func,
            max_leaves=50,
        )
    )

    return expression, params


class TestExpressionEvaluator(TestCase):
    """NOTE:
    This collection of tests uses the hypothesis testing library
    See: https://hypothesis.readthedocs.io/en/latest/index.html

    Instead of making assertions about specific data, we tell hypothesis what the data _basically_
    looks like, and it runs our tests many times over different types of data it generates.
    This allows us to test cases we would have never though of and find edge cases.

    We create data specifications (ie what the data should look like) with "strategies".
    We have written custom strategies for generating different types of expressions above.
    They all end with the `_st` suffix.
    We then tell hypothesis which strategy to use for a test (ie what the data input is) by using the
    `@given` decorator.
    """

    @no_deadline
    @given(arithmetic_st(operators=['+']))
    @example('1 + 2 + 3 + -100')
    def test_evaluator_can_add(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(arithmetic_st(operators=['-']))
    @example('1 - 2 - 3 - -100')
    def test_evaluator_can_subtract(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(arithmetic_st(operators=['*']))
    @example('1 * 2 * 3 * -100')
    def test_evaluator_can_multiply(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(arithmetic_st(operators=['/'], operand_st=good_floats.filter(lambda x: x != 0)))
    @example('1 / 2 / 3 / -100')
    def test_evaluator_can_divide(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(arithmetic_st(operators=['%'], operand_st=good_floats.filter(lambda x: x != 0), max_operands=2))
    @example('10 % 15')
    def test_evaluator_can_mod(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(pow_st())
    @example('2**5')
    def test_evaluator_can_pow(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(func_st(st.just('min'), min_args=2))
    @example('min(1, 2, 3, -100)')
    def test_evaluator_can_min(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(func_st(st.just('max'), min_args=2))
    @example('max(1, 2, 3, -100)')
    def test_evaluator_can_max(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(func_st(st.just('abs'), min_args=1, max_args=1))
    @example('abs(-100)')
    def test_evaluator_can_abs(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(full_expression_no_params_st)
    @example('1 / (2 - 3) * min(abs(-100), 2) / 10 - max(1, 2)')
    def test_evaluator_is_all_that_and_a_bag_of_chips(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(full_expression_with_params_st())
    @example((
        '1 / (2 - 3) * min(abs(-100), $a) / 10 - max(1, $b)',
        {'a': -2, 'b': 2}
    ))
    def test_evaluator_gets_fancy_with_parameters(self, s):
        expression, params = s
        # substitute the parameters so `eval` can evaluate the string
        templated_expression = Template(expression).substitute(params)
        expected = eval(templated_expression)

        actual = ExpressionEvaluator(expression).evaluate(params)
        self.assertEqual(expected, actual)

    def test_evaluator_raises_helpful_exception_when_expression_is_invalid(self):
        # -- Setup
        expression = '1 + HELLO'

        # -- Act, Assert
        with self.assertRaises(InvalidExpression) as ctx:
            ExpressionEvaluator.is_valid(expression)

        exception = ctx.exception
        self.assertEqual(expression, exception.expression)
        self.assertEqual(expression.index('H'), exception.error_position)


class TestDerivedColumns(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Test',
            'last_name': 'User',
        }
        self.user = User.objects.create_user(**user_details)
        self.org, _, _ = create_organization(self.user)

        self.col_factory = FakeColumnFactory(organization=self.org).get_column

        self.numeric_core_columns = Column.objects.filter(
            organization=self.org,
            is_extra_data=False,
            table_name='PropertyState',
            data_type='integer'
        )

        self.derived_col_factory = FakeDerivedColumnFactory(
            organization=self.org,
            inventory_type=DerivedColumn.PROPERTY_TYPE
        )

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

    def _derived_column_for_property_factory(self, expression, column_parameters):
        """Factory to create DerivedColumn, DerivedColumnParameters, and a PropertyState
        which can be used to evaluate the DerivedColumn expression.

        :param expression: str, expression for the DerivedColumn
        :param column_parameters: dict, Columns to be added as parameters. Of the format:
            {
                <parameter name>: {
                    'source_column': Column,
                    'value': <value>,
                },
                ...
            }
            NOTE:
                - <parameter name> is used for the DerivedColumnParameter.parameter_name
                - `value` is used to set the value of the property state. If None,
                  and the column is extra_data, it is not added the property state
        :return: dict, of the format:
            {
                'property_state': PropertyState,
                'derived_column': DerivedColumn,
                'derived_column_parameters': [DerivedColumnParameters]
            }
        """
        derived_column = self.derived_col_factory.get_derived_column(expression)

        # link the parameter columns to the derived column
        derived_column_parameters = []
        for param_name, param_config in column_parameters.items():
            derived_column_parameters.append(DerivedColumnParameter.objects.create(
                parameter_name=param_name,
                derived_column=derived_column,
                source_column=param_config['source_column'],
            ))

        # make a property state which has all the values for the expression
        property_state_config = {
            'extra_data': {}
        }
        for param_name, param_config in column_parameters.items():
            col = param_config['source_column']
            param_value = param_config['value']
            if col.is_extra_data:
                # don't add extra data with value of None
                # this is to assist testing properties with missing extra data columns
                if param_value is not None:
                    property_state_config['extra_data'][col.column_name] = param_value
            else:
                property_state_config[col.column_name] = param_value

        property_state = self.property_state_factory.get_property_state(**property_state_config)

        return {
            'property_state': property_state,
            'derived_column': derived_column,
            'derived_column_parameters': derived_column_parameters
        }

    def test_derived_column_created_successfully_on_save_when_expression_is_valid(self):
        # -- Setup
        expression = '$a + $b'

        # -- Act
        derived_column = DerivedColumn.objects.create(
            name='hello',
            expression=expression,
            organization=self.org,
            inventory_type=DerivedColumn.PROPERTY_TYPE
        )

        # -- Assert
        self.assertIsNotNone(derived_column)

    def test_derived_column_raises_exception_on_save_when_expression_is_invalid(self):
        # -- Setup
        expression = '$a + BAD $b'

        # -- Act, Assert
        with self.assertRaises(ValidationError):
            DerivedColumn.objects.create(
                name='hello',
                expression=expression,
                organization=self.org,
                inventory_type=DerivedColumn.PROPERTY_TYPE
            )

    def test_derived_column_get_parameter_values_is_successful(self):
        # -- Setup
        # expression which sums all the parameters
        expression = '$a + $b + $c + $c'
        column_parameters = {
            'a': {
                'source_column': self.col_factory('foo', is_extra_data=True),
                'value': 1,
            },
            'b': {
                'source_column': self.col_factory('bar', is_extra_data=True),
                'value': 1,
            },
            'c': {
                'source_column': self.numeric_core_columns[0],
                'value': 1,
            },
            'd': {
                'source_column': self.numeric_core_columns[1],
                'value': 1,
            },
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models['derived_column']
        property_state = models['property_state']

        expected_parameter_values = {
            param_name: param_config['value'] for param_name, param_config in column_parameters.items()
        }

        # -- Act
        result = derived_column.get_parameter_values(property_state)

        # -- Assert
        self.assertDictEqual(expected_parameter_values, result)

    def test_derived_column_get_parameter_values_returns_none_for_missing_parameters(self):
        # -- Setup
        expression = '$a + $b'
        column_parameters = {
            # this parameter will be missing on the property state
            'a': {
                'source_column': self.col_factory('foo', is_extra_data=True),
                'value': None,
            },
            'b': {
                'source_column': self.col_factory('bar', is_extra_data=True),
                'value': 1,
            }
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models['derived_column']
        property_state = models['property_state']

        # verify the property state is missing the expected column
        self.assertTrue('a' not in property_state.extra_data)

        expected_parameter_values = {
            'a': None,
            'b': 1
        }

        # -- Act
        result = derived_column.get_parameter_values(property_state)

        # -- Assert
        self.assertDictEqual(expected_parameter_values, result)

    def test_derived_column_evaluate_is_successful_when_property_state_has_valid_values(self):
        # -- Setup
        expression = '$a + $b'
        column_parameters = {
            'a': {
                'source_column': self.col_factory('foo', is_extra_data=True),
                'value': 1,
            },
            'b': {
                'source_column': self.numeric_core_columns[0],
                'value': 1,
            }
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models['derived_column']
        property_state = models['property_state']

        # -- Act
        result = derived_column.evaluate(property_state)

        # -- Assert
        self.assertEqual(2, result)

    def test_derived_column_evaluate_returns_none_when_missing_parameters(self):
        # -- Setup
        # put a parameter, x, which won't exist
        expression = '$a + $x'
        column_parameters = {
            'a': {
                'source_column': self.col_factory('foo', is_extra_data=True),
                'value': 1,
            },
            'b': {
                'source_column': self.numeric_core_columns[0],
                'value': 1,
            }
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models['derived_column']
        property_state = models['property_state']

        # -- Act
        result = derived_column.evaluate(property_state)

        # -- Assert
        self.assertIsNone(result)

    def test_derived_column_evaluate_returns_none_when_parameter_is_nonnumeric(self):
        # -- Setup
        expression = '$a + 1'
        column_parameters = {
            'a': {
                'source_column': self.col_factory('foo', is_extra_data=True),
                'value': 'HELLO!!!!!',
            }
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models['derived_column']
        property_state = models['property_state']

        # -- Act
        result = derived_column.evaluate(property_state)

        # -- Assert
        self.assertIsNone(result)

    def test_derived_column_evaluate_falls_back_to_passed_params_if_not_in_inventory(self):
        """Test that `evaluate` uses values from the `parameters` argument if not
        provided by the inventory state
        """
        # -- Setup
        expression = '$a + $b'
        column_parameters = {
            'a': {
                'source_column': self.col_factory('foo', is_extra_data=True),
                'value': 1,
            }
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models['derived_column']
        property_state = models['property_state']

        # -- Act
        fallback_params = {
            'b': 1
        }
        result = derived_column.evaluate(property_state, parameters=fallback_params)

        # -- Assert
        self.assertEqual(2, result)

    def test_derived_column_evaluate_prioritizes_values_from_inventory_over_passed_params(self):
        """Test that `evaluate` uses prioritizes values from the inventory over
        the passed parameters dict
        """
        # -- Setup
        expression = '$a + $b'
        column_parameters = {
            'a': {
                'source_column': self.col_factory('foo', is_extra_data=True),
                'value': 1,
            },
            'b': {
                'source_column': self.col_factory('bar', is_extra_data=True),
                'value': 1,
            },
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models['derived_column']
        property_state = models['property_state']

        # -- Act
        fallback_params = {
            'a': 100,
            'b': 100
        }
        result = derived_column.evaluate(property_state, parameters=fallback_params)

        # -- Assert
        self.assertEqual(2, result)

    def test_derived_column_evaluate_is_successful_when_only_using_passed_parameters(self):
        """Test that `evaluate` can work without an inventory being passed in"""
        # -- Setup
        expression = '$a + $b'
        column_parameters = {
            'a': {
                'source_column': self.col_factory('foo', is_extra_data=True),
                'value': 1,
            },
            'b': {
                'source_column': self.col_factory('bar', is_extra_data=True),
                'value': 1,
            },
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models['derived_column']

        # -- Act
        fallback_params = {
            'a': 100,
            'b': 100
        }
        # look Ma no inventory
        result = derived_column.evaluate(parameters=fallback_params)

        # -- Assert
        self.assertEqual(200, result)

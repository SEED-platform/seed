"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from json import dumps
from string import Template, ascii_letters, digits

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase

from seed.data_importer.match import match_and_link_incoming_properties_and_taxlots
from seed.landing.models import SEEDUser as User
from seed.lib.progress_data.progress_data import ProgressData
from seed.models import ASSESSED_RAW, DATA_STATE_MAPPING, DATA_STATE_MATCHING, Property, PropertyView
from seed.models.columns import Column
from seed.models.derived_columns import DerivedColumn, DerivedColumnParameter, ExpressionEvaluator, InvalidExpressionError
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeDerivedColumnFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
)
from seed.tests.util import AccessLevelBaseTestCase, AssertDictSubsetMixin, DataMappingBaseTestCase
from seed.utils.organizations import create_organization

no_deadline = settings(deadline=None)

# using 32 width b/c 64 was causing NaNs in multiplication tests (overflow I assume?)
good_floats = st.floats(allow_nan=False, allow_infinity=False, width=32)


@st.composite
def pow_st(draw, base_st=good_floats, exponent_st=good_floats.filter(lambda x: abs(x) < 10)):
    """Strategy for creating pythonic exponentiation, e.g., 1**2, 3**4, etc
    Avoids divide by zero by default

    :param base_st: Strategy, should return valid exponent bases
    :param exponent_st: Strategy, should return valid exponents
    :return: str
    """
    base = draw(base_st)
    exponent = draw(exponent_st)
    # avoid divide by zero errors
    assume(not (base == 0 and exponent < 0))
    return f"{base}**{exponent}"


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

    return f"{func_name}({', '.join(map(str, args))})"


@st.composite
def arithmetic_st(draw, operators, operand_st=good_floats, max_operands=10, in_parens_st=st.just(False)):
    """Strategy for generating a chain of binary operators and operands
    E.g. 1 + 2 + 3, 4.2 * 2.1 * 0 * ..., etc

    :param operators: list[str], list of operators to choose from
    :param operand_st: Strategy, for selecting values to use in operations
    :max_operands: int, maximum number of operands
    :return: str
    """
    operands = draw(st.lists(operand_st, min_size=2, max_size=max_operands))

    n_operators = len(operands) - 1
    operators = draw(st.lists(st.sampled_from(operators), min_size=n_operators, max_size=n_operators))

    result = ""
    # insert an operator between each operand
    for idx, operator in enumerate(operators):
        result += f"{operands[idx]} {operator} "
    result += str(operands[-1])

    if draw(in_parens_st):
        result = f"({result})"

    return result


@st.composite
def parameter_name_st(draw):
    """Strategy for creating valid parameter names. e.g., _hello, test123, etc

    :return: str
    """
    prefix = draw(st.text(ascii_letters + "_", min_size=1, max_size=1))
    body = draw(st.text(digits + ascii_letters + "_"))
    return f"{prefix}{body}"


# atomic strategies (excluding parameter names)
atomic_no_params_st = (
    good_floats.map(str) | pow_st() | func_st(st.sampled_from(["min", "max"]), min_args=2) | func_st(st.just("abs"), min_args=1, max_args=1)
)


# function for recursive strategy
# avoiding the division operator b/c it can cause unexpected divide by zero issues
def recursive_st_func(children):
    return (
        arithmetic_st(operators=["+", "-", "*"], operand_st=children, max_operands=3, in_parens_st=st.booleans())
        | func_st(st.sampled_from(["min", "max"]), children, min_args=2)
        | func_st(st.just("abs"), st.one_of(children), min_args=1, max_args=1)
    )


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

    template_params = [f"${param_name}" for param_name in params]
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

    We create data specifications (i.e., what the data should look like) with "strategies".
    We have written custom strategies for generating different types of expressions above.
    They all end with the `_st` suffix.
    We then tell hypothesis which strategy to use for a test (i.e., what the data input is) by using the
    `@given` decorator.
    """

    @no_deadline
    @given(arithmetic_st(operators=["+"]))
    @example("1 + 2 + 3 + -100")
    def test_evaluator_can_add(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(arithmetic_st(operators=["-"]))
    @example("1 - 2 - 3 - -100")
    def test_evaluator_can_subtract(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(arithmetic_st(operators=["*"]))
    @example("1 * 2 * 3 * -100")
    def test_evaluator_can_multiply(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(arithmetic_st(operators=["/"], operand_st=good_floats.filter(lambda x: x != 0)))
    @example("1 / 2 / 3 / -100")
    def test_evaluator_can_divide(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(arithmetic_st(operators=["%"], operand_st=good_floats.filter(lambda x: x != 0), max_operands=2))
    @example("10 % 15")
    def test_evaluator_can_mod(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(pow_st())
    @example("2**5")
    def test_evaluator_can_pow(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(func_st(st.just("min"), min_args=2))
    @example("min(1, 2, 3, -100)")
    def test_evaluator_can_min(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(func_st(st.just("max"), min_args=2))
    @example("max(1, 2, 3, -100)")
    def test_evaluator_can_max(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(func_st(st.just("abs"), min_args=1, max_args=1))
    @example("abs(-100)")
    def test_evaluator_can_abs(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(full_expression_no_params_st)
    @example("1 / (2 - 3) * min(abs(-100), 2) / 10 - max(1, 2)")
    def test_evaluator_is_all_that_and_a_bag_of_chips(self, s):
        expected = eval(s)
        actual = ExpressionEvaluator(s).evaluate()
        self.assertEqual(expected, actual)

    @no_deadline
    @given(full_expression_with_params_st())
    @example(("1 / (2 - 3) * min(abs(-100), $a) / 10 - max(1, $b)", {"a": -2, "b": 2}))
    def test_evaluator_gets_fancy_with_parameters(self, s):
        expression, params = s
        # substitute the parameters so `eval` can evaluate the string
        templated_expression = Template(expression).substitute(params)
        expected = eval(templated_expression)

        actual = ExpressionEvaluator(expression).evaluate(params)
        self.assertEqual(expected, actual)

    def test_evaluator_raises_helpful_exception_when_expression_is_invalid(self):
        # -- Setup
        expression = "1 + HELLO"

        # -- Act, Assert
        with pytest.raises(InvalidExpressionError) as ctx:
            ExpressionEvaluator.is_valid(expression)

        exception = ctx.value
        self.assertEqual(expression, exception.expression)
        self.assertEqual(expression.index("H"), exception.error_position)


class TestDerivedColumns(TestCase):
    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
            "email": "test_user@demo.com",
            "first_name": "Test",
            "last_name": "User",
        }
        self.user = User.objects.create_user(**user_details)
        self.org, _, _ = create_organization(self.user)

        self.col_factory = FakeColumnFactory(organization=self.org).get_column

        self.numeric_core_columns = Column.objects.filter(
            organization=self.org, is_extra_data=False, table_name="PropertyState", data_type="integer"
        )

        self.derived_col_factory = FakeDerivedColumnFactory(organization=self.org, inventory_type=DerivedColumn.PROPERTY_TYPE)

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

    def _derived_column_for_property_factory(self, expression, column_parameters, name=None, create_property_state=True):
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
        derived_column = self.derived_col_factory.get_derived_column(expression=expression, name=name)

        # link the parameter columns to the derived column
        derived_column_parameters = []
        for param_name, param_config in column_parameters.items():
            derived_column_parameters.append(
                DerivedColumnParameter.objects.create(
                    parameter_name=param_name,
                    derived_column=derived_column,
                    source_column=param_config["source_column"],
                )
            )

        # make a property state which has all the values for the expression
        property_state_config = {"extra_data": {}}
        for param_name, param_config in column_parameters.items():
            col = param_config["source_column"]
            param_value = param_config["value"]
            if col.is_extra_data:
                # don't add extra data with value of None
                # this is to assist testing properties with missing extra data columns
                if param_value is not None:
                    property_state_config["extra_data"][col.column_name] = param_value
            else:
                property_state_config[col.column_name] = param_value

        property_state = None
        if create_property_state:
            property_state = self.property_state_factory.get_property_state(**property_state_config)

        return {"property_state": property_state, "derived_column": derived_column, "derived_column_parameters": derived_column_parameters}

    def test_derived_column_created_successfully_on_save_when_expression_is_valid(self):
        # -- Setup
        expression = "$a + $b"

        # -- Act
        derived_column = DerivedColumn.objects.create(
            name="hello", expression=expression, organization=self.org, inventory_type=DerivedColumn.PROPERTY_TYPE
        )

        # -- Assert
        self.assertIsNotNone(derived_column)

    def test_derived_column_raises_exception_on_save_when_expression_is_invalid(self):
        # -- Setup
        expression = "$a + BAD $b"

        # -- Act, Assert
        with pytest.raises(ValidationError):
            DerivedColumn.objects.create(
                name="hello", expression=expression, organization=self.org, inventory_type=DerivedColumn.PROPERTY_TYPE
            )

    def test_derived_column_get_parameter_values_is_successful(self):
        # -- Setup
        # expression which sums all the parameters
        expression = "$a + $b + $c + $c"
        column_parameters = {
            "a": {
                "source_column": self.col_factory("foo", is_extra_data=True),
                "value": 1,
            },
            "b": {
                "source_column": self.col_factory("bar", is_extra_data=True),
                "value": 1,
            },
            "c": {
                "source_column": self.numeric_core_columns[0],
                "value": 1,
            },
            "d": {
                "source_column": self.numeric_core_columns[1],
                "value": 1,
            },
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models["derived_column"]
        property_state = models["property_state"]

        expected_parameter_values = {param_name: param_config["value"] for param_name, param_config in column_parameters.items()}

        # -- Act
        result = derived_column.get_parameter_values(property_state)

        # -- Assert
        self.assertDictEqual(expected_parameter_values, result)

    def test_derived_column_get_parameter_values_returns_none_for_missing_parameters(self):
        # -- Setup
        expression = "$a + $b"
        column_parameters = {
            # this parameter will be missing on the property state
            "a": {
                "source_column": self.col_factory("foo", is_extra_data=True),
                "value": None,
            },
            "b": {
                "source_column": self.col_factory("bar", is_extra_data=True),
                "value": 1,
            },
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models["derived_column"]
        property_state = models["property_state"]

        # verify the property state is missing the expected column
        self.assertTrue("a" not in property_state.extra_data)

        expected_parameter_values = {"a": None, "b": 1}

        # -- Act
        result = derived_column.get_parameter_values(property_state)

        # -- Assert
        self.assertDictEqual(expected_parameter_values, result)

    def test_derived_column_evaluate_is_successful_when_property_state_has_valid_values(self):
        # -- Setup
        expression = "$a + $b"
        column_parameters = {
            "a": {
                "source_column": self.col_factory("foo", is_extra_data=True),
                "value": 1,
            },
            "b": {
                "source_column": self.numeric_core_columns[0],
                "value": 1,
            },
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models["derived_column"]
        property_state = models["property_state"]

        # -- Act
        result = derived_column.evaluate(property_state)

        # -- Assert
        self.assertEqual(property_state.derived_data, {})  # for the moment, this is always empty
        self.assertEqual(2, result)

    def test_derived_column_evaluate_returns_none_when_missing_parameters(self):
        # -- Setup
        # put a parameter, x, which won't exist
        expression = "$a + $x"
        column_parameters = {
            "a": {
                "source_column": self.col_factory("foo", is_extra_data=True),
                "value": 1,
            },
            "b": {
                "source_column": self.numeric_core_columns[0],
                "value": 1,
            },
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models["derived_column"]
        property_state = models["property_state"]

        # -- Act
        result = derived_column.evaluate(property_state)

        # -- Assert
        self.assertIsNone(result)

    def test_derived_column_evaluate_returns_none_when_parameter_is_nonnumeric(self):
        # -- Setup
        expression = "$a + 1"
        column_parameters = {
            "a": {
                "source_column": self.col_factory("foo", is_extra_data=True),
                "value": "HELLO!!!!!",
            }
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models["derived_column"]
        property_state = models["property_state"]

        # -- Act
        result = derived_column.evaluate(property_state)

        # -- Assert
        self.assertIsNone(result)

    def test_derived_column_evaluate_falls_back_to_passed_params_if_not_in_inventory(self):
        """Test that `evaluate` uses values from the `parameters` argument if not
        provided by the inventory state
        """
        # -- Setup
        expression = "$a + $b"
        column_parameters = {
            "a": {
                "source_column": self.col_factory("foo", is_extra_data=True),
                "value": 1,
            }
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models["derived_column"]
        property_state = models["property_state"]

        # -- Act
        fallback_params = {"b": 1}
        result = derived_column.evaluate(property_state, parameters=fallback_params)

        # -- Assert
        self.assertEqual(2, result)

    def test_derived_column_evaluate_prioritizes_values_from_inventory_over_passed_params(self):
        """Test that `evaluate` uses prioritizes values from the inventory over
        the passed parameters dict
        """
        # -- Setup
        expression = "$a + $b"
        column_parameters = {
            "a": {
                "source_column": self.col_factory("foo", is_extra_data=True),
                "value": 1,
            },
            "b": {
                "source_column": self.col_factory("bar", is_extra_data=True),
                "value": 1,
            },
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models["derived_column"]
        property_state = models["property_state"]

        # -- Act
        fallback_params = {"a": 100, "b": 100}
        result = derived_column.evaluate(property_state, parameters=fallback_params)

        # -- Assert
        self.assertEqual(2, result)

    def test_derived_column_evaluate_is_successful_when_only_using_passed_parameters(self):
        """Test that `evaluate` can work without an inventory being passed in"""
        # -- Setup
        expression = "$a + $b"
        column_parameters = {
            "a": {
                "source_column": self.col_factory("foo", is_extra_data=True),
                "value": 1,
            },
            "b": {
                "source_column": self.col_factory("bar", is_extra_data=True),
                "value": 1,
            },
        }

        models = self._derived_column_for_property_factory(expression, column_parameters)
        derived_column = models["derived_column"]

        # -- Act
        fallback_params = {"a": 100, "b": 100}
        # look Ma no inventory
        result = derived_column.evaluate(parameters=fallback_params)

        # -- Assert
        self.assertEqual(200, result)

    def test_derived_column_evaluation_with_derived_column_as_source_column(self):
        """
        Test that a derived column can be evaluated when a derived column is used in its definition
        """
        # -- Setup
        # expression which sums all the parameters
        expression = "$a + 2"
        derived_column_name = "dc1"
        column_parameters = {
            "a": {
                "source_column": self.col_factory("foo", is_extra_data=True),
                "value": 1,
            },
        }

        models = self._derived_column_for_property_factory(expression, column_parameters, name=derived_column_name)
        derived_column = models["derived_column"]
        property_state = models["property_state"]

        self.assertEqual(derived_column.evaluate(property_state), 3)

        column_with_derived_column = Column.objects.filter(derived_column=derived_column.id).first()
        expression = "$b + 2"
        derived_column_name_2 = "dc2"
        column_parameters = {
            "b": {
                "source_column": column_with_derived_column,
                "value": None,  # not necessary if property state is already created
            },
        }
        models = self._derived_column_for_property_factory(
            expression, column_parameters, name=derived_column_name_2, create_property_state=False
        )
        derived_column2 = models["derived_column"]

        # Derived Column 2 (defined by a different derived column) can be evaluated
        self.assertEqual(derived_column2.evaluate(property_state), 5)

    def test_derived_column_duplicate_name(self):
        """Test that a derived column cannot be created with the same name as another column"""

        expression = "$a + 2"
        # gross_floor_area is already created and should fail
        derived_column_name = "gross_floor_area"
        column_parameters = {
            "a": {
                "source_column": self.col_factory("foo", is_extra_data=True),
                "value": 1,
            },
        }

        with pytest.raises(Exception) as exc:  # noqa: PT011
            self._derived_column_for_property_factory(expression, column_parameters, name=derived_column_name)
        # validation errors return as a list of errors, so check the string representation of the list
        self.assertEqual(str(exc.value), "['Column name PropertyState.gross_floor_area already exists, must be unique']")


class TestDerivedColumnsPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.column = Column.objects.filter(
            organization=self.org, is_extra_data=False, table_name="PropertyState", data_type="integer"
        ).first()

        self.derived_column = DerivedColumn.objects.create(
            name="hello", expression="$a", organization=self.org, inventory_type=DerivedColumn.PROPERTY_TYPE
        )
        self.cycle = self.cycle_factory.get_cycle()

    def test_derived_columns_create(self):
        url = reverse("api:v3:derived_columns-list") + "?organization_id=" + str(self.org.id)
        post_params = dumps(
            {
                "name": "new column",
                "expression": "$param_a / 100",
                "inventory_type": "Property",
                "parameters": [{"parameter_name": "param_a", "source_column": self.column.id}],
            }
        )

        # root owner user can
        self.login_as_root_owner()
        response = self.client.post(url, post_params, content_type="application/json")
        assert response.status_code == 200

        # root member user cannot
        self.login_as_root_member()
        response = self.client.post(url, post_params, content_type="application/json")
        assert response.status_code == 403

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, post_params, content_type="application/json")
        assert response.status_code == 403

    def test_derived_columns_update(self):
        url = reverse("api:v3:derived_columns-detail", args=[self.derived_column.id]) + "?organization_id=" + str(self.org.id)
        post_params = dumps({"name": "new column"})

        # root owner user can
        self.login_as_root_owner()
        response = self.client.put(url, post_params, content_type="application/json")
        assert response.status_code == 200

        # root member user cannot
        self.login_as_root_member()
        response = self.client.put(url, post_params, content_type="application/json")
        assert response.status_code == 403

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, post_params, content_type="application/json")
        assert response.status_code == 403

    def test_derived_columns_delete(self):
        url = reverse("api:v3:derived_columns-detail", args=[self.derived_column.id]) + "?organization_id=" + str(self.org.id)

        # root member user cannot
        self.login_as_root_member()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403

        # root owner user can
        self.login_as_root_owner()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 200

    def test_derived_column_evaluate_permissions(self):
        property = self.property_factory.get_property()
        property.access_level_instance = self.org.root
        property.save()

        property_state = self.property_state_factory.get_property_state()
        PropertyView.objects.create(property=property, cycle=self.cycle, state=property_state)

        url = reverse("api:v3:derived_columns-evaluate", args=[self.derived_column.id])
        params = {"cycle_id": self.cycle.id, "organization_id": self.org.pk, "inventory_ids": f"{property.pk}"}

        # root member user can
        response = self.client.get(url, params, content_type="application/json")
        data = json.loads(response.content)
        assert response.status_code == 200
        assert data["results"] == [{"id": property.pk, "value": None}]

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, params, content_type="application/json")
        data = json.loads(response.content)
        assert response.status_code == 200
        assert data["results"] == []


class TestDerivedColumnUpdates(AssertDictSubsetMixin, DataMappingBaseTestCase):
    def setUp(self):
        # set up user and org
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_superuser(**user_details)
        selfvars = self.set_up(ASSESSED_RAW, user_name=user_details["username"], user_password=user_details["password"])
        _, self.org, self.import_file, self.import_record, self.cycle = selfvars
        self.client.login(**user_details)

        # set up import file
        self.import_file.mapping_done = True
        self.import_file.save()
        self.base_details = {
            "import_file_id": self.import_file.id,
            "data_state": DATA_STATE_MAPPING,
        }
        progress_data = ProgressData(func_name="match_buildings", unique_id=self.import_file.id)
        sub_progress_data = ProgressData(func_name="match_sub_progress", unique_id=self.import_file.id)
        self.action_args = [self.import_file.id, progress_data.key, sub_progress_data.key]

        # set up factory
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_factory = FakePropertyFactory(organization=self.org)

        # -- Setup derived column
        expression = "$a + $b"
        self.column_a = Column.objects.get(column_name="gross_floor_area", table_name="PropertyState")
        self.column_b = Column.objects.get(column_name="energy_score", table_name="PropertyState")
        column_parameters = {
            "a": {
                "source_column": self.column_a,
                "value": 1,
            },
            "b": {
                "source_column": self.column_b,
                "value": 1,
            },
        }
        self.derived_col_factory = FakeDerivedColumnFactory(organization=self.org, inventory_type=DerivedColumn.PROPERTY_TYPE)
        models = self._derived_column_for_property_factory(expression, column_parameters)
        self.derived_column = models["derived_column"]

    def _derived_column_for_property_factory(self, expression, column_parameters, name=None, create_property_state=True):
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
        derived_column = self.derived_col_factory.get_derived_column(expression=expression, name=name)

        # link the parameter columns to the derived column
        derived_column_parameters = []
        for param_name, param_config in column_parameters.items():
            derived_column_parameters.append(
                DerivedColumnParameter.objects.create(
                    parameter_name=param_name,
                    derived_column=derived_column,
                    source_column=param_config["source_column"],
                )
            )

        # make a property state which has all the values for the expression
        property_state_config = {"extra_data": {}}
        for param_name, param_config in column_parameters.items():
            col = param_config["source_column"]
            param_value = param_config["value"]
            if col.is_extra_data:
                # don't add extra data with value of None
                # this is to assist testing properties with missing extra data columns
                if param_value is not None:
                    property_state_config["extra_data"][col.column_name] = param_value
            else:
                property_state_config[col.column_name] = param_value

        property_state = None
        if create_property_state:
            property_state = self.property_state_factory.get_property_state(**property_state_config)

        return {"property_state": property_state, "derived_column": derived_column, "derived_column_parameters": derived_column_parameters}

    def test_derived_data_updates_on_import_creation(self):
        # Set Up
        self.base_details[self.column_a.column_name] = 2
        self.base_details[self.column_b.column_name] = 2
        self.base_details["raw_access_level_instance_id"] = self.org.root.id
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        match_and_link_incoming_properties_and_taxlots(*self.action_args)
        v = PropertyView.objects.first()

        self.assertEqual(v.state.derived_data, {self.derived_column.name: 4})  # for the moment, this is always empty

    def test_derived_data_updates_on_import_merge(self):
        # this causes all the states to match
        self.base_details["custom_id_1"] = "86HJPCWQ+2VV-1-3-2-3"
        self.base_details["no_default_data"] = False

        # create preexisting-state
        self.state = self.property_state_factory.get_property_state(**self.base_details)
        self.state.data_state = DATA_STATE_MATCHING
        self.state.save()
        self.existing_property = self.property_factory.get_property()
        v = PropertyView.objects.create(property=self.existing_property, cycle=self.cycle, state=self.state)
        self.assertEqual(v.state.derived_data, {})  # for the moment, this is always empty

        # Set Up
        self.base_details[self.column_a.column_name] = 2
        self.base_details[self.column_b.column_name] = 2
        self.base_details["raw_access_level_instance_id"] = self.org.root.id
        s = self.property_state_factory.get_property_state(**self.base_details)
        s.save()

        # Action
        match_and_link_incoming_properties_and_taxlots(*self.action_args)
        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(PropertyView.objects.count(), 1)
        v = PropertyView.objects.first()

        self.assertEqual(v.state.derived_data, {self.derived_column.name: 4})  # for the moment, this is always empty

    def test_derived_data_on_merge(self):
        # Create views
        self.state_1 = self.property_state_factory.get_property_state(gross_floor_area=2)
        self.property_1 = self.property_factory.get_property()
        self.view_1 = PropertyView.objects.create(property=self.property_1, cycle=self.cycle, state=self.state_1)

        self.state_2 = self.property_state_factory.get_property_state(energy_score=2, gross_floor_area=20)
        self.property_2 = self.property_factory.get_property()
        self.view_2 = PropertyView.objects.create(property=self.property_2, cycle=self.cycle, state=self.state_2)

        # Merge the properties
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps({"property_view_ids": [self.view_2.pk, self.view_1.pk]})
        self.client.post(url, post_params, content_type="application/json")

        # Assert
        self.assertEqual(PropertyView.objects.count(), 1)
        v = PropertyView.objects.first()
        self.assertEqual(v.state.derived_data, {self.derived_column.name: 4})  # for the moment, this is always empty

    def test_derived_data_on_derived_column_creation(self):
        # Create views
        self.state = self.property_state_factory.get_property_state(year_built=2000)
        self.property = self.property_factory.get_property()
        self.view = PropertyView.objects.create(property=self.property, cycle=self.cycle, state=self.state)

        # Merge the properties
        year_built = Column.objects.get(column_name="year_built", table_name="PropertyState")
        url = reverse("api:v3:derived_columns-list") + "?organization_id=" + str(self.org.id)
        post_params = dumps(
            {
                "name": "new guy",
                "expression": "$param_a * 2",
                "inventory_type": "Property",
                "parameters": [{"parameter_name": "param_a", "source_column": year_built.id}],
            }
        )
        self.client.post(url, post_params, content_type="application/json")

        # Assert
        v = PropertyView.objects.first()
        self.assertEqual(v.state.derived_data, {"new guy": 4000})  # for the moment, this is always empty

    def test_derived_data_on_derived_column_update(self):
        # Set Up
        self.base_details[self.column_a.column_name] = 2
        self.base_details[self.column_b.column_name] = 2
        self.base_details["raw_access_level_instance_id"] = self.org.root.id
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        match_and_link_incoming_properties_and_taxlots(*self.action_args)
        v = PropertyView.objects.first()

        self.assertEqual(v.state.derived_data, {self.derived_column.name: 4})  # for the moment, this is always empty

        # Merge the properties
        url = reverse("api:v3:derived_columns-detail", args=[self.derived_column.id]) + "?organization_id=" + str(self.org.id)
        post_params = dumps(
            {
                "name": self.derived_column.name,
                "expression": "$a - $b",
            }
        )
        self.client.put(url, post_params, content_type="application/json")

        # Assert
        v = PropertyView.objects.first()
        self.assertEqual(v.state.derived_data, {self.derived_column.name: 0})  # for the moment, this is always empty

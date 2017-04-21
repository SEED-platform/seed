# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pmerriam@quickleft.com>'
"""
import itertools

from django.test import TestCase

from seed.utils.search import (
    is_numeric_expression,
    parse_expression,
    NUMERIC_EXPRESSION_REGEX,
)


# Metaclass to create individual test methods per test case.
class TestCaseFactory(type):

    def __new__(cls, name, bases, attrs):
        cases = attrs['cases']
        method_maker = attrs['method_maker']
        prefix = attrs['prefix']

        for doc, value, expected in cases:
            test = method_maker(value, expected)
            test_name = '{0}_{1}'.format(prefix, doc.lower().replace(' ', '_'))
            if test_name in attrs:
                raise KeyError("Test name {0} duplicated".format(test_name))
            test.__name__ = test_name
            test.__doc__ = doc
            attrs[test_name] = test
        return super(TestCaseFactory, cls).__new__(cls, name, bases, attrs)


def make_is_numeric_expression_method(value, expected):
    def run(self):
        result = is_numeric_expression(value)
        self.assertEquals(bool(expected), bool(result))
    return run


class IsNumericExpressionTests(TestCase):
    __metaclass__ = TestCaseFactory
    method_maker = make_is_numeric_expression_method
    prefix = "test_is_numeric_expression"

    # test name, input, expected output
    cases = [
        # Non expressions
        ('not_expression_1', '1234', False),
        ('not_expression_2', '', False),
        ('not_expression_3', None, False),
        # Incomplete expressions
        ('not_expression_4', "=", False),
        ('not_expression_5', "==", False),
        ('not_expression_6', "!=", False),
        ('not_expression_7', "!", False),
        ('not_expression_8', "<>", False),
        ('not_expression_9', "<", False),
        ('not_expression_10', "<=", False),
        ('not_expression_11', ">", False),
        ('not_expression_12', ">=", False),
        # Basic expressions
        ('equality_1', "=1234", True),
        ('equality_2', "==1234", True),
        ('inequality_1', "!=1234", True),
        ('inequality_2', "!1234", True),
        ('inequality_3', "<>1234", True),
        ('less_than', "<1234", True),
        ('less_than_or_equal', "<=1234", True),
        ('greater_than', ">1234", True),
        ('greater_than_or_equal', ">=1234", True),
        # Whitespace
        ('whitespace_1', "=  1234", True),
        ('whitespace_2', " == 1234 ", True),
        # Nulls checks
        ('is_null_1', "=null", True),
        ('is_null_2', "==null", True),
        ('is_not_null_1', "!=null", True),
        ('is_not_null_2', "!null", True),
        ('is_not_null_3', "<>null", True),
        # Complex Expressions
        ('complex_1', ">123,<456", True),
        ('complex_2', ">123, <456", True),
        ('complex_3', ">123 , <456", True),
        ('complex_4', ">123,<456,!null", True),
        ('complex_5', ">123,<", True),
    ]


def query_to_child_tuples(query):
    """
    Takes a Q object and extracts the underlying queries.  Returns an iterable
    of 3-tuples who's values are (negated, field_lookup, value)
    """
    if isinstance(query, tuple):
        return query
    return list(itertools.chain.from_iterable((
        (
            [tuple(itertools.chain.from_iterable(([query.negated], c)))]
            if isinstance(c, tuple)
            else query_to_child_tuples(c)
        )
        for c in query.children
    )))


def make_parse_expression_method(value, expected):
    def run(self):
        parts = NUMERIC_EXPRESSION_REGEX.findall(value)
        result = parse_expression("field", parts)
        query_children = query_to_child_tuples(result)
        self.assertEquals(expected, query_children)
    return run


class ExpressionParserTests(TestCase):
    __metaclass__ = TestCaseFactory
    method_maker = make_parse_expression_method
    prefix = "test_numeric_expression_parser"

    # test name, input, expected output
    cases = [
        ("equality_1", "=1234", [(False, "field", "1234")]),
        ("equality_2", "==1234", [(False, "field", "1234")]),
        ("inequality_1", "!=1234", [(True, "field", "1234")]),
        ("inequality_2", "!1234", [(True, "field", "1234")]),
        ("inequality_3", "<>1234", [(True, "field", "1234")]),
        ("greater_than", ">1234", [(False, "field__gt", "1234")]),
        ("greater_than_or_equal", ">=1234", [(False, "field__gte", "1234")]),
        ("less_than", "<1234", [(False, "field__lt", "1234")]),
        ("less_than_or_equal", "<=1234", [(False, "field__lte", "1234")]),
        # null
        ("is_null_1", "=null", [(False, "field__isnull", True)]),
        ("is_null_2", "==null", [(False, "field__isnull", True)]),
        ("is_not_null_1", "!null", [(False, "field__isnull", False)]),
        ("is_not_null_2", "!=null", [(False, "field__isnull", False)]),
        ("is_not_null_3", "<>null", [(False, "field__isnull", False)]),
        # complex expressions
        ("complex_1", "!=1234,<1234", [(True, "field", "1234"), (False, "field__lt", "1234")]),
        ("complex_2", ">1234,<4567", [(False, "field__gt", "1234"), (False, "field__lt", "4567")]),
        # invalid
        ("invalid_null_1", ">null", []),
        ("invalid_null_2", ">=null", []),
        ("invalid_null_3", "<null", []),
        ("invalid_null_4", "<=null", []),
    ]

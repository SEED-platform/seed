# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pmerriam@quickleft.com>'
"""
import itertools

from django.test import TestCase

from seed.utils.search import (
    is_string_expression,
    parse_expression,
    STRING_EXPRESSION_REGEX,
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


def make_is_string_expression_method(value, expected):
    def run(self):
        result = is_string_expression(value)
        self.assertEquals(expected, bool(result), (expected, result, value))
    return run


class IsStringExpressionTests(TestCase):
    __metaclass__ = TestCaseFactory
    method_maker = make_is_string_expression_method
    prefix = "test_is_string_expression"

    # test name, input, expected output
    cases = [
        # Non expressions
        ('not_expression_1', 'abcd', False),
        ('not_expression_2', '', False),
        ('not_expression_3', None, False),
        # Invalid operators
        ('not_expression_9', "<abc", False),
        ('not_expression_10', "<=abc", False),
        ('not_expression_11', ">abc", False),
        ('not_expression_12', ">=abc", False),
        # Incomplete expressions
        ('not_expression_4', "=", False),
        ('not_expression_5', "==", False),
        ('not_expression_6', "!=", False),
        ('not_expression_7', "!", False),
        ('not_expression_8', "<>", False),
        # Basic expressions
        ('equality_1', "=abcd", True),
        ('equality_2', "==abcd", True),
        ('inequality_1', "!=abcd", True),
        ('inequality_2', "!abcd", True),
        ('inequality_3', "<>abcd", True),
        # Empty string expressions
        ('empty_string_expression_1', "==''", True),
        ('empty_string_expression_2', '=""', True),
        # Whitespace
        ('whitespace_1', "=  abcd", True),
        ('whitespace_2', " == abcd ", True),
        # Internal whitespace
        ('internal_whitespace_1', "=  ab cd", True),
        ('internal_whitespace_2', "=  123 abcd", True),
        # Nulls checks
        ('is_null_1', "=null", True),
        ('is_null_2', "==null", True),
        ('is_not_null_1', "!=null", True),
        ('is_not_null_2', "!null", True),
        ('is_not_null_3', "<>null", True),
        # Complex Expressions
        ('complex_1', "!=abc,<>xyz", True),
        ('complex_2', "!abc, !xyz", True),
        ('complex_3', "!=abc , !=xyz", True),
        ('complex_4', "!abc,!xyz,!null", True),
        ('complex_5', "!abc,==", True),
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
        parts = STRING_EXPRESSION_REGEX.findall(value)
        result = parse_expression("field", parts)
        query_children = query_to_child_tuples(result)
        self.assertEquals(expected, query_children)
    return run


class ExpressionParserTests(TestCase):
    __metaclass__ = TestCaseFactory
    method_maker = make_parse_expression_method
    prefix = "test_string_expression_parser"

    # test name, input, expected output
    cases = [
        ("equality_1", "=abcd", [(False, "field", "abcd")]),
        ("equality_2", "==abcd", [(False, "field", "abcd")]),
        ("inequality_1", "!=abcd", [(True, "field", "abcd")]),
        ("inequality_2", "!abcd", [(True, "field", "abcd")]),
        ("inequality_3", "<>abcd", [(True, "field", "abcd")]),
        # null
        ("is_null_1", "=null", [(False, "field__isnull", True)]),
        ("is_null_2", "==null", [(False, "field__isnull", True)]),
        ("is_not_null_1", "!null", [(False, "field__isnull", False)]),
        ("is_not_null_2", "!=null", [(False, "field__isnull", False)]),
        ("is_not_null_3", "<>null", [(False, "field__isnull", False)]),
        # complex expressions
        ("complex_1", "!=abcd,<>wxyz", [(True, "field", "abcd"), (True, "field", "wxyz")]),
        ("complex_2", "!null,!=wxyz", [(False, "field__isnull", False), (True, "field", "wxyz")]),
        # invalid
        ("invalid_null_1", ">null", []),
        ("invalid_null_2", ">=null", []),
        ("invalid_null_3", "<null", []),
        ("invalid_null_4", "<=null", []),
    ]

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pmerriam@quickleft.com'
"""
import operator
import re
from functools import reduce

from django.db.models import Q
from past.builtins import basestring

SUFFIXES = ['__lt', '__gt', '__lte', '__gte', '__isnull']
DATE_FIELDS = ['year_ending']


def strip_suffix(k, suffix):
    match = k.find(suffix)
    if match >= 0:
        return k[:match]
    else:
        return k


def strip_suffixes(k, suffixes):
    return reduce(strip_suffix, suffixes, k)


def is_column(k, columns):
    sanitized = strip_suffixes(k, SUFFIXES)
    if sanitized in columns:
        return True
    return False


def is_date_field(k):
    sanitized = strip_suffixes(k, SUFFIXES)
    if sanitized in DATE_FIELDS:
        return True
    return False


def is_string_query(q):
    return isinstance(q, basestring)


def is_exact_match(q):
    # Surrounded by matching quotes?
    if is_string_query(q):
        return re.match(r"""^(["'])(.+)\1$""", q)
    return False


def is_empty_match(q):
    # Empty matching quotes?
    if is_string_query(q):
        return re.match(r"""^(["'])\1$""", q)
    return False


def is_not_empty_match(q):
    # Exclamation mark and empty matching quotes?
    if is_string_query(q):
        return re.match(r"""^!(["'])\1$""", q)
    return False


def is_case_insensitive_match(q):
    # Carat and matching quotes? eg ^"sacramento"
    if is_string_query(q):
        return re.match(r"""^\^(["'])(.+)\1$""", q)
    return False


def is_exclude_filter(q):
    # Starts with an exclamation point, no quotes
    if is_string_query(q):
        return re.match(r"""!([\w_ ]+)""", q)
    return False


def is_exact_exclude_filter(q):
    # Starts with an exclamation point, has matching quotes
    if is_string_query(q):
        return re.match(r"""^!(["'])(.+)\1$""", q)
    return False


NUMERIC_EXPRESSION_REGEX = re.compile((
    r'('  # open expression grp
    r'(?P<operator>==|=|>|>=|<|<=|<>|!|!=)'  # operator
    r'\s*'  # whitespace
    r'(?P<value>(?:-?[0-9]+)|(?:null))\s*(?:,|$)'  # numeric value or the string null
    r')'  # close expression grp
))


def is_numeric_expression(q):
    """
    Checks whether a value looks like an expression, meaning that it contains a
    substring that begins with a comparison operator followed by a numeric
    value, optionally separated by whitespace.
    """
    if is_string_query(q):
        return NUMERIC_EXPRESSION_REGEX.findall(q)
    return False


STRING_EXPRESSION_REGEX = re.compile((
    r'('  # open expression grp
    r'(?P<operator>==|(?<!<|>)=|<>|!|!=)'  # operator
    r'\s*'  # whitespace
    r'(?P<value>\'\'|""|null|[a-zA-Z0-9\s]+)\s*(?:,|$)'  # open value grp
    r')'  # close expression grp
))


def is_string_expression(q):
    """
    Checks whether a value looks like an expression, meaning that it contains a
    substring that begins with a comparison operator followed by a numeric
    value, optionally separated by whitespace.
    """
    if is_string_query(q):
        return STRING_EXPRESSION_REGEX.findall(q)
    return False


OPERATOR_MAP = {
    "==": ("", False),
    "=": ("", False),
    ">": ("__gt", False),
    ">=": ("__gte", False),
    "<": ("__lt", False),
    "<=": ("__lte", False),
    "!": ("", True),
    "!=": ("", True),
    "<>": ("", True),
}

NULL_OPERATORS = {"=", "==", "!", "!=", "<>"}
EQUALITY_OPERATORS = {"=", "=="}


def _translate_expression_parts(op, val):
    """
    Given the string representation of a mathematical operator, return the
    django orm query suffix (__lt, __isnull, etc) and appropriate value to be
    used for the query.

    Returns `None` if the comparison is invalid ("> null").
    """
    if val == "null":
        if op not in NULL_OPERATORS:
            raise ValueError("Invalid operation on null")
        elif op in EQUALITY_OPERATORS:
            return "__isnull", True, None
        else:
            return "__isnull", False, None

    suffix, is_negated = OPERATOR_MAP[op]
    return suffix, val, is_negated


def parse_expression(k, parts):
    """
    Parse a complex expression into a Q object.
    """
    query_filters = []

    for src, op, val in parts:
        try:
            suffix, q_val, is_negated = _translate_expression_parts(op, val)
        except ValueError:
            continue
        lookup = "{field}{suffix}".format(
            field=k,
            suffix=suffix,
        )
        q_object = Q(**{lookup: q_val})
        if is_negated:
            query_filters.append(~q_object)
        else:
            query_filters.append(q_object)
    return reduce(operator.and_, query_filters, Q())

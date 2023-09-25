# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author 'Piper Merriam <pmerriam@quickleft.com'
"""
import operator
import re
from dataclasses import dataclass
from enum import Enum
from functools import reduce
from typing import Any, Union

from django.db import models
from django.db.models import Q
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce, Replace
from django.http.request import QueryDict
from past.builtins import basestring

from seed.models.columns import Column

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
    # Carat and matching quotes? e.g., ^"sacramento"
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


class FilterException(Exception):
    pass


class QueryFilterOperator(Enum):
    EQUAL = 'exact'
    LT = 'lt'
    LTE = 'lte'
    GT = 'gt'
    GTE = 'gte'
    CONTAINS = 'icontains'
    ISNULL = 'isnull'


@dataclass
class QueryFilter:
    field_name: str
    operator: Union[QueryFilterOperator, None]
    is_negated: bool

    @classmethod
    def parse(cls, filter):
        """Parse a filter string into a QueryFilter

        :param filter: string in the format <field_name>, or <field_name>__<lookup_expression>
        """
        field_name, _, lookup = filter.partition('__')
        is_negated = lookup == 'ne'
        operator = None
        if lookup and not is_negated:
            try:
                operator = QueryFilterOperator(lookup)
            except ValueError:
                valid_lookups = [op.value for op in list(QueryFilterOperator)]
                raise FilterException(f'Invalid lookup expression "{lookup}"; expected one of {valid_lookups}')

        return cls(field_name, operator, is_negated)

    def to_q(self, value: Any) -> Q:
        if self.operator:
            expression = f'{self.field_name}__{self.operator.value}'
        else:
            expression = self.field_name
        q_dict = {expression: value}

        if self.is_negated:
            return ~Q(**q_dict)
        else:
            return Q(**q_dict)


# represents a dictionary usable with a QuerySet annotation:
#   `QuerySet.annotation(**AnnotationDict)`
AnnotationDict = dict[str, models.Func]


def _build_extra_data_annotations(column_name: str, data_type: str) -> tuple[str, AnnotationDict]:
    """Creates a dictionary of annotations which will cast the extra data column_name
    into the provided data_type, for usage like: `*View.annotate(**annotations)`

    Why is this necessary? In some cases, extra_data only stores string values.
    This means anytime you try to filter numeric values in extra data, it won't
    behave as expected. Thus, we cast extra data to the defined column data_type
    at query time to make sure our filters and sorts will work.

    :param column_name: the Column.column_name for a Column which is extra_data
    :param data_type: the Column.data_type for the column
    :returns: the annotated field name which contains the casted result, along with
              a dict of annotations
    """
    # annotations require a few characters to be removed...
    cleaned_column_name = column_name \
        .replace(' ', '_') \
        .replace("'", '-') \
        .replace('"', '-') \
        .replace('`', '-') \
        .replace(';', '-')
    text_field_name = f'_{cleaned_column_name}_to_text'
    final_field_name = f'_{cleaned_column_name}_final'

    annotations: AnnotationDict = {
        # use postgresql json string operator `->>`
        text_field_name: KeyTextTransform(column_name, 'state__extra_data'),
    }
    if data_type == 'integer':
        annotations.update({
            final_field_name: Cast(
                # Remove comma separators
                Replace(text_field_name, models.Value(','), models.Value('')), output_field=models.IntegerField())
        })
    elif data_type in ['number', 'float', 'area', 'eui', 'ghg', 'ghg_intensity']:
        annotations.update({
            final_field_name: Cast(
                # Remove comma separators
                Replace(text_field_name, models.Value(','), models.Value('')), output_field=models.FloatField())
        })
    elif data_type in ['date', 'datetime']:
        annotations.update({
            final_field_name: Cast(text_field_name, output_field=models.DateTimeField())
        })
    elif data_type == 'boolean':
        annotations.update({
            final_field_name: Cast(text_field_name, output_field=models.BooleanField())
        })
    else:
        # treat as string
        annotations.update({
            final_field_name: Coalesce(text_field_name, models.Value(''), output_field=models.TextField()),
        })

    return final_field_name, annotations


def _parse_view_filter(filter_expression: str, filter_value: Union[str, bool], columns_by_name: dict[str, dict]) -> tuple[Q, AnnotationDict]:
    """Parse a filter expression into a Q object

    :param filter_expression: should be a valid Column.column_name, with an optional
                              Django field lookup suffix (e.g., `__gt`, `__icontains`, etc)
                              https://docs.djangoproject.com/en/4.0/topics/db/queries/#field-lookups
                              One custom field lookup suffix is allowed, `__ne`,
                              which negates the expression (i.e., column_name != filter_value)
    :param filter_value: the value evaluated against the filter_expression
    :param columns_by_name: mapping of Column.column_name to dict representation of Column
    :return: query object
    """
    filter = QueryFilter.parse(filter_expression)
    column = columns_by_name.get(filter.field_name)
    if column is None or column['related']:
        return Q(), {}

    column_name = column["column_name"]
    annotations: AnnotationDict = {}
    if column['is_extra_data']:
        new_field_name, annotations = _build_extra_data_annotations(column['column_name'], column['data_type'])
        updated_filter = QueryFilter(new_field_name, filter.operator, filter.is_negated)
    else:
        updated_filter = QueryFilter(f'state__{column_name}', filter.operator, filter.is_negated)

    # isnull filtering should not coerce booleans to the column type
    if filter_expression.endswith('__isnull') and isinstance(filter_value, bool):
        new_filter_value = filter_value
    else:
        try:
            new_filter_value = Column.cast_column_value(column['data_type'], filter_value)
        except Exception:
            raise FilterException(f'Invalid data type for "{column_name}". Expected a valid {column["data_type"]} value.')

    return updated_filter.to_q(new_filter_value), annotations


def _parse_view_sort(sort_expression: str, columns_by_name: dict[str, dict]) -> tuple[Union[None, str], AnnotationDict]:
    """Parse a sort expression

    :param sort_expression: should be a valid Column.column_name. Optionally prefixed
                            with '-' to indicate descending order.
    :param columns_by_name: mapping of Column.column_name to dict representation of Column
    :return: the parsed sort expression or None if not valid followed by a dictionary of annotations
    """
    column_name = sort_expression.lstrip('-')
    direction = '-' if sort_expression.startswith('-') else ''
    if column_name == 'id':
        return sort_expression, {}
    elif column_name in columns_by_name:
        column = columns_by_name[column_name]
        column_name = column["column_name"]
        if column['related']:
            return None, {}
        elif column['is_extra_data']:
            new_field_name, annotations = _build_extra_data_annotations(column_name, column['data_type'])
            return f'{direction}{new_field_name}', annotations
        else:
            return f'{direction}state__{column_name}', {}
    else:
        return None, {}


def build_view_filters_and_sorts(filters: QueryDict, columns: list[dict]) -> tuple[Q, AnnotationDict, list[str]]:
    """Build a query object usable for `*View.filter(...)` as well as a list of
    column names for usable for `*View.order_by(...)`.

    Filters are specified in a similar format as Django queries, as `column_name`
    or `column_name__lookup`, where `column_name` is a valid Column.column_name,
    and `__lookup` (which is optional) is any valid Django field lookup:
      https://docs.djangoproject.com/en/4.0/topics/db/queries/#field-lookups

    One special lookup which is not provided by Django is `__ne` which negates
    the filter expression.

    Query string examples:
    - `?city=Denver` - inventory where City is Denver
    - `?city__ne=Denver` - inventory where City is NOT Denver
    - `?site_eui__gte=100` - inventory where Site EUI >= 100
    - `?city=Denver&site_eui__gte=100` - inventory where City is Denver AND Site EUI >= 100
    - `?my_custom_column__lt=1000` - inventory where the extra data field `my_custom_column` < 1000

    Sorts are specified with the `order_by` parameter, with any valid Column.column_name
    as the value. By default the column is sorted in ascending order, columns prefixed
    with `-` will be sorted in descending order.

    Query string examples:
    - `?order_by=site_eui` - sort by Site EUI in ascending order
    - `?order_by=-site_eui` - sort by Site EUI in descending order
    - `?order_by=city&order_by=site_eui` - sort by City, then Site EUI

    This function basically does the following:
    - Ignore any filter/sort that doesn't have a corresponding column
    - Handle cases for extra data
    - Convert filtering values into their proper types (e.g., str -> int)

    :param filters: QueryDict from a request
    :param columns: list of all valid Columns in dict format
    :return: filters, annotations and sorts
    """
    columns_by_name = {}
    for column in columns:
        if (column['related']):
            continue
        columns_by_name[column['name']] = column

    new_filters = Q()
    annotations = {}
    for filter_expression, filter_value in filters.items():
        # when the filter value is "", we want to be sure to include None and "".
        if filter_value == '':
            # if not "", exclude null
            if filter_expression.endswith('__ne'):
                is_null_filter_expression = filter_expression.replace('__ne', '__isnull')
                is_null_filter_value = False

            # if exactly "", only return null
            elif filter_expression.endswith('__exact'):
                is_null_filter_expression = filter_expression.replace('__exact', '__isnull')
                is_null_filter_value = True

            parsed_filters, parsed_annotations = _parse_view_filter(
                is_null_filter_expression,
                is_null_filter_value,
                columns_by_name
            )

            # if column data_type is "string", also filter on the empty string
            filter = QueryFilter.parse(filter_expression)
            column_data_type = columns_by_name.get(filter.field_name, {}).get("data_type")
            if column_data_type in ['string', 'None']:
                empty_string_parsed_filters, _ = _parse_view_filter(filter_expression, filter_value, columns_by_name)

                if filter_expression.endswith('__ne'):
                    parsed_filters &= empty_string_parsed_filters

                elif filter_expression.endswith('__exact'):
                    parsed_filters |= empty_string_parsed_filters

        else:
            parsed_filters, parsed_annotations = _parse_view_filter(filter_expression, filter_value, columns_by_name)

        new_filters &= parsed_filters
        annotations.update(parsed_annotations)

    order_by = []
    for sort_expression in filters.getlist('order_by', ['id']):
        parsed_sort, parsed_annotations = _parse_view_sort(sort_expression, columns_by_name)
        if parsed_sort is not None:
            order_by.append(parsed_sort)
            annotations.update(parsed_annotations)

    return new_filters, annotations, order_by

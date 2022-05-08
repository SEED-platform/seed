# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author

Search methods pertaining to buildings.

"""
from __future__ import annotations

import json
import logging
import operator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import reduce
from typing import Any, Callable, Union

from django.db import models
from django.db.models import Q
from django.db.models.functions import Cast, NullIf, Replace
from django.http.request import QueryDict, RawPostDataException
from past.builtins import basestring

from seed.lib.superperms.orgs.models import Organization

from .models import (
    Column,
    Property,
    PropertyState,
    PropertyView,
    TaxLot,
    TaxLotState,
    TaxLotView
)

_log = logging.getLogger(__name__)


def _search(q, fieldnames, queryset):
    """returns a queryset for matching objects
    :param str or unicode q: search string
    :param list fieldnames: list of model fieldnames
    :param queryset: "optional" queryset to filter from, will all return an empty queryset if missing.
    :returns: :queryset: queryset of matching buildings
    """
    if q == '':
        return queryset
    qgroup = reduce(operator.or_, (
        Q(**{fieldname + '__icontains': q}) for fieldname in fieldnames
    ))
    return queryset.filter(qgroup)


def search_properties(q, fieldnames=None, queryset=None):
    if queryset is None:
        return PropertyState.objects.none()
    if fieldnames is None:
        fieldnames = [
            'pm_parent_property_id'
            'jurisdiction_property_id'
            'address_line_1',
            'property_name',
        ]
    return _search(q, fieldnames, queryset)


def search_taxlots(q, fieldnames=None, queryset=None):
    if queryset is None:
        return TaxLotState.objects.none()
    if fieldnames is None:
        fieldnames = [
            'jurisdiction_tax_lot_id',
            'address'
            'block_number'
        ]
    return _search(q, fieldnames, queryset)


def parse_body(request):
    """parses the request body for search params, q, etc

    :param request: django wsgi request object
    :return: dict

    Example::

        {
            'exclude': dict, exclude dict for django queryset
            'order_by': str, query order_by, defaults to 'tax_lot_id'
            'sort_reverse': bool, True if ASC, False if DSC
            'page': int, pagination page
            'number_per_page': int, number per pagination page
            'show_shared_buildings': bool, whether to search across all user's orgs
            'q': str, global search param
            'other_search_params': dict, filter params
            'project_id': str, project id if exists in body
        }
    """
    try:  # keep this in here to allow non-DRF to call this function
        body = json.loads(request.body)
    except RawPostDataException:  # if this exception is thrown, we are in DRF land and just access the request.data
        body = request.data
    except ValueError:  # but if this is thrown then we do like we always did and just move forward with empty body
        body = {}

    return process_search_params(
        params=body,
        user=request.user,
        is_api_request=getattr(request, 'is_api_request', False),
    )


def process_search_params(params, user, is_api_request=False):
    """
    Given a python representation of a search query, process it into the
    internal format that is used for searching, filtering, sorting, and pagination.

    :param params: a python object representing the search query
    :param user: the user this search is for
    :param is_api_request: bool, boolean whether this search is being done as an api request.
    :returns: dict

    Example::

        {
            'exclude': dict, exclude dict for django queryset
            'order_by': str, query order_by, defaults to 'tax_lot_id'
            'sort_reverse': bool, True if ASC, False if DSC
            'page': int, pagination page
            'number_per_page': int, number per pagination page
            'show_shared_buildings': bool, whether to search across all user's orgs
            'q': str, global search param
            'other_search_params': dict, filter params
            'project_id': str, project id if exists in body
        }
    """
    q = params.get('q', '')
    other_search_params = params.get('filter_params', {})
    exclude = other_search_params.pop('exclude', {})
    # inventory_type = params.pop('inventory_type', None)
    order_by = params.get('order_by', 'id')
    sort_reverse = params.get('sort_reverse', False)
    if isinstance(sort_reverse, basestring):
        sort_reverse = sort_reverse == 'true'
    page = int(params.get('page', 1))
    number_per_page = int(params.get('number_per_page', 10))
    if 'show_shared_buildings' in params:
        show_shared_buildings = params.get('show_shared_buildings')
    elif not is_api_request:
        show_shared_buildings = getattr(
            user, 'show_shared_buildings', False
        )
    else:
        show_shared_buildings = False

    return {
        'organization_id': params.get('organization_id'),
        'exclude': exclude,
        'order_by': order_by,
        'sort_reverse': sort_reverse,
        'page': page,
        'number_per_page': number_per_page,
        'show_shared_buildings': show_shared_buildings,
        'q': q,
        'other_search_params': other_search_params,
        'project_id': params.get('project_id')
    }


def build_shared_buildings_orgs(orgs):
    """returns a list of sibling and parent orgs"""
    other_orgs = []
    for org in orgs:
        if org.parent_org:
            # this is a child org, so get all of the other
            # child orgs of this org's parents.
            other_orgs.extend(org.parent_org.child_orgs.all())
            other_orgs.append(org.parent_org)
        else:
            # this is a parent org, so get all of the child orgs
            other_orgs.extend(org.child_orgs.all())
            other_orgs.append(org)
    # remove dups
    other_orgs = list(set(other_orgs))
    return other_orgs


def get_orgs_w_public_fields():
    """returns a list of orgs that have publicly shared fields"""
    return list(Organization.objects.filter(
        column__shared_field_type=Column.SHARED_PUBLIC
    ).distinct())


def get_inventory_fieldnames(inventory_type):
    """returns a list of field names that will be searched against
    """
    return {
        'property': [
            'address_line_1', 'pm_property_id',
            'jurisdiction_property_identifier'
        ],
        'taxlot': ['jurisdiction_taxlot_id', 'address'],
        'property_view': ['property_id', 'cycle_id', 'state_id'],
        'taxlot_view': ['taxlot_id', 'cycle_id', 'state_id'],
    }[inventory_type]


def search_inventory(inventory_type, q, fieldnames=None, queryset=None):
    """returns a queryset for matching Taxlot(View)/Property(View)
    :param str or unicode q: search string
    :param list fieldnames: list of  model fieldnames
    :param queryset: optional queryset to filter from
    :returns: :queryset: queryset of matching buildings
    """
    Model = {
        'property': Property, 'property_view': PropertyView,
        'taxlot': TaxLot, 'taxlot_view': TaxLotView,
    }[inventory_type]
    if not fieldnames:
        fieldnames = get_inventory_fieldnames(inventory_type)
    if queryset is None:
        queryset = Model.objects.none()
    if q == '':
        return queryset
    qgroup = reduce(operator.or_, (
        Q(**{fieldname + '__icontains': q}) for fieldname in fieldnames
    ))
    return queryset.filter(qgroup)


def create_inventory_queryset(inventory_type, orgs, exclude, order_by, other_orgs=None):
    """creates a queryset of properties or taxlots within orgs.
    If ``other_orgs``, properties/taxlots in both orgs and other_orgs
    will be represented in the queryset.

    :param inventory_type: property or taxlot.
    :param orgs: queryset of Organization inst.
    :param exclude: django query exclude dict.
    :param order_by: django query order_by str.
    :param other_orgs: list of other orgs to ``or`` the query
    """
    # return immediately if no inventory type
    # i.e. when called by get_serializer in LabelViewSet
    # as there should be no inventory
    if not inventory_type:
        return []
    Model = {
        'property': Property, 'property_view': PropertyView,
        'taxlot': TaxLot, 'taxlot_view': TaxLotView,
    }[inventory_type]

    distinct_order_by = order_by.lstrip('-')

    if inventory_type.endswith('view'):
        filter_key = "{}__organization_id__in".format(
            inventory_type.split('_')[0]
        )
    else:
        filter_key = "organization_id__in"
    orgs_filter_dict = {filter_key: orgs}
    other_orgs_filter_dict = {filter_key: other_orgs}

    if other_orgs:
        return Model.objects.order_by(order_by, 'pk').filter(
            (
                Q(**orgs_filter_dict) | Q(**other_orgs_filter_dict)
            ),
        ).exclude(**exclude).distinct(distinct_order_by, 'pk')
    else:
        result = Model.objects.order_by(order_by, 'pk').filter(
            **orgs_filter_dict
        ).exclude(**exclude).distinct(distinct_order_by, 'pk')

    return result


def inventory_search_filter_sort(inventory_type, params, user):
    """
    Given a parsed set of params, perform the search, filter, and sort for
    Properties or Taxlots
    """
    sort_reverse = params['sort_reverse']
    order_by = params['order_by']
    order_by = "-{}".format(order_by) if sort_reverse else order_by

    # get all buildings for a user's orgs and sibling orgs
    orgs = user.orgs.all().filter(pk=params['organization_id'])
    other_orgs = []
    # this is really show all orgs TODO better param/func name?
    if params['show_shared_buildings']:
        other_orgs = build_shared_buildings_orgs(orgs)

    inventory = create_inventory_queryset(
        inventory_type,
        orgs,
        params['exclude'],
        order_by,
        other_orgs=other_orgs,
    )

    if inventory:
        # full text search across a couple common fields
        inventory = search_inventory(
            inventory_type, params['q'], queryset=inventory
        )

    return inventory


class FilterException(Exception):
    pass


class QueryFilterOperator(Enum):
    EQUAL = 'exact'
    LT = 'lt'
    LTE = 'lte'
    GT = 'gt'
    GTE = 'gte'
    CONTAINS = 'icontains'


@dataclass
class QueryFilter:
    field_name: str
    operator: Union[QueryFilterOperator, None]
    is_negated: bool

    @classmethod
    def parse(cls, filter: str) -> QueryFilter:
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
    behave as expected. Thus we cast extra data to the defined column data_type
    at query time to make sure our filters and sorts will work.

    :param column_name: the Column.column_name for a Column which is extra_data
    :param data_type: the Column.data_type for the column
    :returns: the annotated field name which contains the casted result, along with
              a dict of annotations
    """
    full_field_name = f'state__extra_data__{column_name}'
    text_field_name = f'_{column_name}_to_text'
    stripped_field_name = f'_{column_name}_stripped'
    cleaned_field_name = f'_{column_name}_cleaned'
    final_field_name = f'_{column_name}_final'

    annotations: AnnotationDict = {
        text_field_name: Cast(full_field_name, output_field=models.TextField()),
        # after casting a json field to text, the resulting value will be wrapped
        # in double quotes which need to be removed
        stripped_field_name: Replace(text_field_name, models.Value('"'), output_field=models.TextField()),
        cleaned_field_name: NullIf(stripped_field_name, models.Value('null'), output_field=models.TextField())
    }
    if data_type == 'integer':
        annotations.update({
            final_field_name: Cast(cleaned_field_name, output_field=models.IntegerField())
        })
    elif data_type in ['number', 'float', 'area', 'eui']:
        annotations.update({
            final_field_name: Cast(cleaned_field_name, output_field=models.FloatField())
        })
    elif data_type in ['date', 'datetime']:
        annotations.update({
            final_field_name: Cast(cleaned_field_name, output_field=models.DateTimeField())
        })
    elif data_type == 'boolean':
        annotations.update({
            final_field_name: Cast(cleaned_field_name, output_field=models.BooleanField())
        })
    else:
        # treat it as a string (just cast to text and strip)
        annotations = {
            text_field_name: Cast(full_field_name, output_field=models.TextField()),
            final_field_name: Replace(text_field_name, models.Value('"'), output_field=models.TextField()),
        }

    return final_field_name, annotations


def _parse_view_filter(filter_expression: str, filter_value: str, columns_by_name: dict[str, dict]) -> tuple[Q, AnnotationDict]:
    """Parse a filter expression into a Q object

    :param filter_expression: should be a valid Column.column_name, with an optional
                              Django field lookup suffix (e.g. `__gt`, `__icontains`, etc)
                              https://docs.djangoproject.com/en/4.0/topics/db/queries/#field-lookups
                              One custom field lookup suffix is allowed, `__ne`,
                              which negates the expression (i.e. column_name != filter_value)
    :param filter_value: the value evaluated against the filter_expression
    :param columns_by_name: mapping of Column.column_name to dict representation of Column
    :return: query object
    """
    DATA_TYPE_PARSERS: dict[str, Callable] = {
        'number': float,
        'float': float,
        'integer': int,
        'string': str,
        'geometry': str,
        'datetime': datetime.fromisoformat,
        'date': datetime.fromisoformat,
        'boolean': lambda v: v.lower() == 'true',
        'area': float,
        'eui': float,
    }

    filter = QueryFilter.parse(filter_expression)
    column = columns_by_name.get(filter.field_name)
    if column is None:
        return Q(), {}

    updated_filter = None
    annotations: AnnotationDict = {}
    if filter.field_name == 'campus':
        # campus is the only column found on the canonical property (TaxLots don't have this column)
        # all other columns are found in the state
        updated_filter = QueryFilter(f'property__{filter.field_name}', filter.operator, filter.is_negated)
    elif column['is_extra_data']:
        new_field_name, annotations = _build_extra_data_annotations(column['column_name'], column['data_type'])
        updated_filter = QueryFilter(new_field_name, filter.operator, filter.is_negated)
    else:
        updated_filter = QueryFilter(f'state__{filter.field_name}', filter.operator, filter.is_negated)

    parser = DATA_TYPE_PARSERS.get(column['data_type'], str)
    try:
        new_filter_value = parser(filter_value)
    except Exception:
        raise FilterException(f'Invalid data type for "{filter.field_name}". Expected a valid {column["data_type"]} value.')

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
    elif column_name == 'campus':
        # campus is the only column which is found exclusively on the Property, not the state
        return f'property__{sort_expression}', {}
    elif column_name in columns_by_name:
        column = columns_by_name[column_name]
        if column['is_extra_data']:
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
    - Convert filtering values into their proper types (e.g. str -> int)

    :param filters: QueryDict from a request
    :param columns: list of all valid Columns in dict format
    :return: filters, annotations and sorts
    """
    columns_by_name = {
        c['column_name']: c
        for c in columns
    }

    new_filters = Q()
    annotations = {}
    for filter_expression, filter_value in filters.items():
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

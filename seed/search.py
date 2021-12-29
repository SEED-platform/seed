# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author

Search methods pertaining to buildings.

"""
from datetime import datetime
import json
import logging
import operator
from typing import Callable, Union

from functools import reduce

from django.db.models import Q
from django.http.request import RawPostDataException, QueryDict
from past.builtins import basestring

from seed.lib.superperms.orgs.models import Organization
from .models import (
    Property,
    PropertyState,
    PropertyView,
    TaxLot,
    TaxLotState,
    TaxLotView,
    Column,
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


def _parse_view_filter(filter_expression: str, filter_value: str, columns_by_name: dict[str, dict]) -> Q:
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
    data_type_parsers: dict[str, Callable] = {
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

    column_name, _, _ = filter_expression.partition('__')
    column = columns_by_name.get(column_name)
    if column is None:
        return Q()

    # users indicate negation with a trailing `__ne` (which is not a real Django filter)
    # so we need to remove it if found
    is_negated = filter_expression.endswith('__ne')
    if is_negated:
        filter_expression, _, _ = filter_expression.rpartition('__ne')

    new_filter_expression = None
    if column_name == 'campus':
        # campus is the only column found on the canonical property (TaxLots don't have this column)
        # all other columns are found in the state
        new_filter_expression = f'property__{filter_expression}'
    elif column['is_extra_data']:
        new_filter_expression = f'state__extra_data__{filter_expression}'
    else:
        new_filter_expression = f'state__{filter_expression}'

    parser = data_type_parsers.get(column['data_type'], str)
    try:
        new_filter_value = parser(filter_value)
    except Exception:
        raise FilterException(f'Invalid data type for "{column_name}". Expected a valid {column["data_type"]} value.')

    new_filter_dict = {new_filter_expression: new_filter_value}
    if is_negated:
        return ~Q(**new_filter_dict)
    else:
        return Q(**new_filter_dict)


def _parse_view_sort(sort_expression: str, columns_by_name: dict[str, dict]) -> Union[None, str]:
    """Parse a sort expression

    :param sort_expression: should be a valid Column.column_name. Optionally prefixed
                            with '-' to indicate descending order.
    :param columns_by_name: mapping of Column.column_name to dict representation of Column
    :return: the parsed sort expression or None if not valid
    """
    column_name = sort_expression.lstrip('-')
    direction = '-' if sort_expression.startswith('-') else ''
    if column_name == 'id':
        return sort_expression
    elif column_name == 'campus':
        # campus is the only column which is found exclusively on the Property, not the state
        return f'property__{sort_expression}'
    elif column_name in columns_by_name:
        column = columns_by_name[column_name]
        if column['is_extra_data']:
            return f'{direction}state__extra_data__{column_name}'
        else:
            return f'{direction}state__{column_name}'
    else:
        return None


def build_view_filters_and_sorts(filters: QueryDict, columns: list[dict]) -> tuple[Q, list[str]]:
    """Build a query object usable for `*View.filter(...)` as well as a list of
    column names for usable for `*View.order_by(...)`.

    Specifically:
    - Ignore any filter/sort that doesn't have a corresponding column
    - Handle cases for extra data
    - Convert filtering values into their proper types (e.g. str -> int)

    :param filters: QueryDict from a request
    :param columns: list of all valid Columns in dict format
    :return: filters and sorts
    """
    columns_by_name = {
        c['column_name']: c
        for c in columns
    }

    new_filters = Q()
    for filter_expression, filter_value in filters.items():
        new_filters &= _parse_view_filter(filter_expression, filter_value, columns_by_name)

    order_by = []
    for sort_expression in filters.getlist('order_by', ['id']):
        parsed_sort = _parse_view_sort(sort_expression, columns_by_name)
        if parsed_sort is not None:
            order_by.append(parsed_sort)

    return new_filters, order_by

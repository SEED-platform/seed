# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import datetime

from django.db.models import Q
from seed import models
from seed.models import ASSESSED_RAW, BuildingSnapshot
from seed import search
from seed.utils import time
from seed.utils.mapping import get_mappable_types
from seed.utils.constants import ASSESSOR_FIELDS_BY_COLUMN


def get_source_type(import_file, source_type=''):
    """Used for converting ImportFile source_type into an int."""

    # TODO: move source_type to a database lookup. Right now it is hard coded
    source_type_str = getattr(import_file, 'source_type', '') or ''
    source_type_str = source_type or source_type_str
    source_type_str = source_type_str.upper().replace(' ', '_')

    return getattr(models, source_type_str, ASSESSED_RAW)


def serialize_building_snapshot(b, pm_cb, building):
    """returns a dict that's safe to JSON serialize"""
    b_as_dict = b.__dict__.copy()
    for key, val in b_as_dict.items():
        if isinstance(val, datetime.datetime) or isinstance(val, datetime.date):
            b_as_dict[key] = time.convert_to_js_timestamp(val)
    del(b_as_dict['_state'])
    # check if they're matched
    if b.canonical_building == pm_cb:
        b_as_dict['matched'] = True
    else:
        b_as_dict['matched'] = False
    if '_canonical_building_cache' in b_as_dict:
        del(b_as_dict['_canonical_building_cache'])
    return b_as_dict


def get_buildings_for_user_count(user):
    """returns the number of buildings in a user's orgs"""
    return BuildingSnapshot.objects.filter(
        super_organization__in=user.orgs.all(),
        canonicalbuilding__active=True,
    ).count()


def get_search_query(user, params):
    other_search_params = params.get('filter_params', {})
    q = other_search_params.get('q', '')
    order_by = params.get('order_by', 'pk')
    sort_reverse = params.get('sort_reverse', False)
    project_slug = other_search_params.get('project__slug', None)

    mappable_types = get_mappable_types()

    if project_slug:
        mappable_types['project__slug'] = 'string'

    if order_by:
        if sort_reverse:
            order_by = "-%s" % order_by
        building_snapshots = BuildingSnapshot.objects.order_by(
            order_by
        ).filter(
            super_organization__in=user.orgs.all(),
            canonicalbuilding__active=True,
        )
    else:
        building_snapshots = BuildingSnapshot.objects.filter(
            super_organization__in=user.orgs.all(),
            canonicalbuilding__active=True,
        )

    buildings_queryset = search.search_buildings(
        q, queryset=building_snapshots
    )

    buildings_queryset = search.filter_other_params(
        buildings_queryset, other_search_params, mappable_types
    )

    return buildings_queryset


def get_columns(org_id, all_fields=False):
    """
    Get default columns, to be overridden in future

    Returns::

        title: HTML presented title of column
        sort_column: semantic name used by js and for searching DB
        class: HTML CSS class for row td elements
        title_class: HTML CSS class for column td elements
        type: 'string', 'number', 'date'
        min, max: the django filter key e.g. gross_floor_area__gte
        field_type: assessor, pm, or compliance (currently not used)
        sortable: determines if the column is sortable
        checked: initial state of "edit columns" modal
        static: True if option can be toggle (ID is false because it is
            always needed to link to the building detail page)
        link: signifies that the cell's data should link to a building detail
            page

    """
    cols = []
    translator = {
        '': 'string',
        'date': 'date',
        'float': 'number',
        'string': 'string',
        'decimal': 'number',
        'datetime': 'date',
        'foreignkey': 'number'
    }
    field_types = {}
    for k, v in get_mappable_types().items():
        d = {
            "title": k.title().replace('_', ' '),
            "sort_column": k,
            "type": translator[v],
            "class": "is_aligned_right",
            "sortable": True,
            "checked": False,
            "static": False,
            "field_type": field_types.get(k),
            "link": True if '_id' in k or 'address' in k.lower() else False,
        }
        if d['sort_column'] == 'gross_floor_area':
            d['type'] = 'floor_area'
            d['subtitle'] = u"ft" + u"\u00B2"
        if d['type'] != 'string':
            d["min"] = "{0}__gte".format(k)
            d["max"] = "{0}__lte".format(k)

        cols.append(d)

    for col in cols:
        if col['sort_column'] in ASSESSOR_FIELDS_BY_COLUMN:
            assessor_field = ASSESSOR_FIELDS_BY_COLUMN[col['sort_column']]
            col['field_type'] = assessor_field['field_type']

    if all_fields:
        qs = models.Column.objects.filter(is_extra_data=True).filter(
            Q(organization=None) |
            Q(mapped_mappings__super_organization=org_id)
        ).select_related('unit').distinct()
    else:
        qs = models.Column.objects.filter(is_extra_data=True).filter(
            mapped_mappings__super_organization=org_id
        ).select_related('unit').distinct()
    for c in qs:
        t = c.unit.get_unit_type_display().lower() if c.unit else 'string'
        link = False
        if '_id' in c.column_name or 'address' in c.column_name.lower():
            link = True
        d = {
            "title": c.column_name,
            "sort_column": c.column_name,
            "type": translator[t],
            "class": "is_aligned_right",
            "field_type": "assessor",
            "sortable": True,
            "checked": False,
            "static": False,
            "link": link,
            "is_extra_data": True,
        }
        if d['type'] != 'string':
            d["min"] = "{0}__gte".format(c.column_name)
            d["max"] = "{0}__lte".format(c.column_name)
        cols.append(d)

    cols.sort(key=lambda x: x['title'])
    columns = {
        'fields': cols,
    }

    return columns

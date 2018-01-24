# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from seed import models
from seed import search
from seed.models import ASSESSED_RAW, BuildingSnapshot
from seed.utils.mapping import get_mappable_types


def get_source_type(import_file, source_type=''):
    """Used for converting ImportFile source_type into an int."""

    # TODO: move source_type to a database lookup. Right now it is hard coded
    source_type_str = getattr(import_file, 'source_type', '') or ''
    source_type_str = source_type or source_type_str
    source_type_str = source_type_str.upper().replace(' ', '_')

    return getattr(models, source_type_str, ASSESSED_RAW)


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

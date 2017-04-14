# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from rest_framework import filters

from seed import search


class LabelFilterBackend(filters.BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        if 'organization_id' in request.query_params:
            return queryset.filter(
                super_organization_id=request.query_params['organization_id'],
            )
        return queryset


class InventoryFilterBackend(filters.BaseFilterBackend):
    """
    Implements the filtering and searching of buildings as a Django Rest
    Framework filter backend.
    """

    def filter_queryset(self, request):
        params = request.query_params.dict()
        # Since this is being passed in as a query string, the object ends up
        # coming through as a string.
        params['filter_params'] = json.loads(params.get('filter_params', '{}'))
        inventory_type = params.pop('inventory_type', None)
        params = search.process_search_params(
            params=params,
            user=request.user,
            is_api_request=True,
        )
        queryset = search.inventory_search_filter_sort(
            inventory_type,
            params=params,
            user=request.user,
        )
        if 'selected' in request.data:
            # Return labels limited to the 'selected' list.  Otherwise, if selected is empty, return all
            if request.data['selected']:
                return queryset.filter(
                    id__in=request.data['selected'],
                )
        return queryset


class BuildingFilterBackend(filters.BaseFilterBackend):
    """
    Implements the filtering and searching of buildings as a Django Rest
    Framework filter backend.
    """

    def filter_queryset(self, request, queryset, view):
        # TODO: this needs to be filled in with the same logic that implements
        # search/filtering in `seed.views.main.search_buildings`.
        params = request.query_params.dict()
        # Since this is being passed in as a query string, the object ends up
        # coming through as a string.
        params['filter_params'] = json.loads(params.get('filter_params', '{}'))

        params = search.process_search_params(
            params=params,
            user=request.user,
            is_api_request=True,
        )
        buildings_queryset = search.orchestrate_search_filter_sort(
            params=params,
            user=request.user,
            skip_sort=True,
        )

        if request.query_params.get('select_all_checkbox', 'false') == 'true':
            pass
        elif 'selected_buildings' in request.query_params:
            return buildings_queryset.filter(
                id__in=request.query_params.getlist('selected_buildings'),
            )
        return buildings_queryset

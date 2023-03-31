# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json

from rest_framework import filters

from seed import search
from seed.models import VIEW_LIST_INVENTORY_TYPE, VIEW_LOCATION_TYPES


class ColumnListProfileFilterBackend(filters.BaseFilterBackend):
    @staticmethod
    def filter_queryset(request, queryset, view):
        if 'organization_id' in request.query_params:
            queryset = queryset.filter(
                organization_id=request.query_params['organization_id'],
            )
        if 'inventory_type' in request.query_params:
            result = [k for k, v in VIEW_LIST_INVENTORY_TYPE if v == request.query_params['inventory_type']]
            if len(result) == 1:
                queryset = queryset.filter(
                    inventory_type=result[0],
                )
        if 'profile_location' in request.query_params:
            result = [k for k, v in VIEW_LOCATION_TYPES if v == request.query_params['profile_location']]
            if len(result) == 1:
                queryset = queryset.filter(
                    profile_location=result[0],
                )
        return queryset


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
    Framework filter backend. This is used to constrain the inventory by
    the labels/filter endpoint. The inventory filter is implemented in the
    PropertyViewSet
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

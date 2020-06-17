# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
"""
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response

from seed.filters import ColumnListSettingFilterBackend
from seed.models import (
    ColumnListSetting,
    Organization,
    Column,
    VIEW_LIST,
    VIEW_LIST_INVENTORY_TYPE,
    VIEW_LIST_PROPERTY,
    VIEW_LOCATION_TYPES,
)
from seed.serializers.column_list_settings import (
    ColumnListSettingSerializer,
)
from seed.utils.api import OrgValidateMixin
from seed.utils.viewsets import SEEDOrgCreateUpdateModelViewSet


class ColumnListingViewSet(OrgValidateMixin, SEEDOrgCreateUpdateModelViewSet):
    """
    API endpoint for returning Column List Settings

    create:
        Create a new list setting. The list of columns is an array of column primary keys. If using Swagger, then
        this will be enters as a list with returns between each primary key.

        JSON POST Example:

            {
                "name": "some new name 3",
                "settings_location": "List View Settings",
                "inventory_type": "Tax Lot",
                "columns": [
                    {"id": 1, "pinned": false, "order": 10},
                    {"id": 5, "pinned": true, "order": 14},
                    {"id": 7, "pinned": true, "order": 14}
                ]
            }

    """
    serializer_class = ColumnListSettingSerializer
    model = ColumnListSetting
    filter_backends = (ColumnListSettingFilterBackend,)
    pagination_class = None
    # force_parent = True  # Ideally the column list settings would inherit from the parent,
    # but not yet.

    # Overridden to augment with protected ComStock list setting if enabled
    def retrieve(self, request, *args, **kwargs):
        org_id = self.get_organization(self.request)

        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization with id %s does not exist' % org_id
            }, status=status.HTTP_404_NOT_FOUND)

        if not org.comstock_enabled or kwargs['pk'] != 'null':
            return super(ColumnListingViewSet, self).retrieve(request, args, kwargs)

        result = {
            'status': 'success',
            'data': {
                'id': None,
                'name': 'ComStock',
                'settings_location': VIEW_LOCATION_TYPES[VIEW_LIST][1],
                'inventory_type': VIEW_LIST_INVENTORY_TYPE[VIEW_LIST_PROPERTY][1],
                'columns': []
            }
        }

        comstock_columns = Column.objects.filter(organization_id=org_id, comstock_mapping__isnull=False) \
            .order_by('comstock_mapping')

        for index, column in enumerate(comstock_columns):
            result['data']['columns'].append({
                "id": column.id,
                "pinned": False,
                "order": index + 1,
                "column_name": column.column_name,
                "table_name": column.table_name,
                "comstock_mapping": column.comstock_mapping
            })

        return JsonResponse(result, status=status.HTTP_200_OK)

    # Overridden to augment with protected ComStock list setting if enabled
    def list(self, request, *args, **kwargs):
        org_id = self.get_organization(self.request)

        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization with id %s does not exist' % org_id
            }, status=status.HTTP_404_NOT_FOUND)

        if not org.comstock_enabled:
            return super(ColumnListingViewSet, self).list(request, args, kwargs)

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        results = list(queryset)
        results.append({
            "id": None,
            "name": "ComStock",
            "settings_location": 0,
            "inventory_type": 0
        })

        serializer = self.get_serializer(results, many=True)

        # Add ComStock columns
        comstock_columns = Column.objects.filter(organization_id=org_id, comstock_mapping__isnull=False)\
            .order_by('comstock_mapping')
        serializer.data[len(serializer.data) - 1]['columns'] = []
        for index, column in enumerate(comstock_columns):
            serializer.data[len(serializer.data) - 1]['columns'].append({
                "id": column.id,
                "pinned": False,
                "order": index + 1,
                "column_name": column.column_name,
                "table_name": column.table_name,
                "comstock_mapping": column.comstock_mapping
            })

        return Response(serializer.data)

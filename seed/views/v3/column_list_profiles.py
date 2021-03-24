# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
"""
from django.http import JsonResponse
from django.utils.decorators import method_decorator

from drf_yasg.utils import swagger_auto_schema

from rest_framework import status
from rest_framework.response import Response

from seed.filters import ColumnListProfileFilterBackend
from seed.models import (
    ColumnListProfile,
    Organization,
    Column,
    VIEW_LIST,
    VIEW_LIST_INVENTORY_TYPE,
    VIEW_LIST_PROPERTY,
    VIEW_LOCATION_TYPES,
)
from seed.serializers.column_list_profiles import ColumnListProfileSerializer
from seed.utils.api import OrgValidateMixin
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


@method_decorator(
    name='create',
    decorator=swagger_auto_schema_org_query_param
)
@method_decorator(
    name='update',
    decorator=swagger_auto_schema_org_query_param
)
class ColumnListProfileViewSet(OrgValidateMixin, SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """
    API endpoint for returning Column List Profiles

    create:
        Create a new list profile. The list of columns is an array of column primary keys. If using Swagger, then
        this will be enters as a list with returns between each primary key.

        JSON POST Example:

            {
                "name": "some new name 3",
                "profile_location": "List View Profile",
                "inventory_type": "Tax Lot",
                "columns": [
                    {"id": 1, "pinned": false, "order": 10},
                    {"id": 5, "pinned": true, "order": 14},
                    {"id": 7, "pinned": true, "order": 14}
                ]
            }

    """
    serializer_class = ColumnListProfileSerializer
    model = ColumnListProfile
    filter_backends = (ColumnListProfileFilterBackend,)
    pagination_class = None
    # force_parent = True  # Ideally the column list profiles would inherit from the parent,
    # but not yet.

    # Overridden to augment with protected ComStock list profile if enabled
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
            return super(ColumnListProfileViewSet, self).retrieve(request, args, kwargs)

        result = {
            'status': 'success',
            'data': {
                'id': None,
                'name': 'ComStock',
                'profile_location': VIEW_LOCATION_TYPES[VIEW_LIST][1],
                'inventory_type': VIEW_LIST_INVENTORY_TYPE[VIEW_LIST_PROPERTY][1],
                'columns': self.list_comstock_columns(org_id)
            }
        }

        return JsonResponse(result, status=status.HTTP_200_OK)

    # Overridden to augment with protected ComStock list profile if enabled
    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(
                required=False,
                description="Optional org id which overrides the users (default) current org id"
            ),
            AutoSchemaHelper.query_string_field(
                name='inventory_type',
                required=True,
                description="'Property' or 'Tax Lot' for filtering."
            ),
            AutoSchemaHelper.query_string_field(
                name='profile_location',
                required=True,
                description="'List View Profile' or 'Detail View Profile' for filtering."
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        org_id = self.get_organization(self.request)

        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization with id %s does not exist' % org_id
            }, status=status.HTTP_404_NOT_FOUND)

        inventory_type = request.query_params.get('inventory_type')
        profile_location = request.query_params.get('profile_location')
        if not org.comstock_enabled or inventory_type == 'Tax Lot' or profile_location == 'Detail View Profile':
            return super(ColumnListProfileViewSet, self).list(request, args, kwargs)

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        results = list(queryset)
        base_profiles = self.get_serializer(results, many=True).data

        # Add ComStock columns
        base_profiles.append({
            "id": None,
            "name": "ComStock",
            "profile_location": profile_location,
            "inventory_type": inventory_type,
            "columns": self.list_comstock_columns(org_id)
        })

        return Response(base_profiles)

    @staticmethod
    def list_comstock_columns(org_id):
        comstock_columns = Column.objects.filter(organization_id=org_id, comstock_mapping__isnull=False) \
            .order_by('comstock_mapping')

        results = []
        for index, column in enumerate(comstock_columns):
            results.append({
                "id": column.id,
                "pinned": False,
                "order": index + 1,
                "column_name": column.column_name,
                "table_name": column.table_name,
                "comstock_mapping": column.comstock_mapping
            })

        return results

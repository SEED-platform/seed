"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from seed.filters import ColumnListProfileFilterBackend
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    VIEW_LIST,
    VIEW_LIST_INVENTORY_TYPE,
    VIEW_LIST_PROPERTY,
    VIEW_LOCATION_TYPES,
    Column,
    ColumnListProfile,
    Organization,
    PropertyState,
    PropertyView,
    TaxLotState,
    TaxLotView,
)
from seed.models.columns import EXCLUDED_API_FIELDS
from seed.serializers.column_list_profiles import ColumnListProfileSerializer
from seed.utils.api import OrgValidateMixin
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


@method_decorator(
    name="create",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_root_member_access"),
    ],
)
@method_decorator(
    name="update",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_root_member_access"),
    ],
)
@method_decorator(
    name="destroy",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_root_member_access"),
    ],
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
            return JsonResponse(
                {"status": "error", "message": f"organization with id {org_id} does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        if org.comstock_enabled and kwargs["pk"] == "null":
            return JsonResponse(
                {
                    "status": "success",
                    "data": {
                        "id": None,
                        "name": "ComStock",
                        "profile_location": VIEW_LOCATION_TYPES[VIEW_LIST][1],
                        "inventory_type": VIEW_LIST_INVENTORY_TYPE[VIEW_LIST_PROPERTY][1],
                        "columns": self.list_comstock_columns(org_id),
                    },
                },
                status=status.HTTP_200_OK,
            )

        clp = (
            ColumnListProfile.objects.filter(pk=kwargs["pk"])
            .prefetch_related("derived_columns__column", "columnlistprofilecolumn_set__column")
            .first()
        )
        if clp is None:
            return JsonResponse(
                {"status": "error", "message": f"column list profile with id {kwargs['pk']} does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return JsonResponse({"status": "success", "data": self.get_serializer(clp).data}, status=status.HTTP_200_OK)

    # Overridden to augment with protected ComStock list profile if enabled
    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(
                required=False, description="Optional org id which overrides the users (default) current org id"
            ),
            AutoSchemaHelper.query_string_field(name="inventory_type", required=True, description="'Property' or 'Tax Lot' for filtering."),
            AutoSchemaHelper.query_string_field(
                name="profile_location", required=True, description="'List View Profile' or 'Detail View Profile' for filtering."
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        org_id = self.get_organization(self.request)
        brief = json.loads(request.query_params.get("brief", "false"))

        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"organization with id {org_id} does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        inventory_type = request.query_params.get("inventory_type")
        profile_location = request.query_params.get("profile_location")
        queryset = self.filter_queryset(self.get_queryset())

        if brief:
            results = list(queryset.values("id", "name", "profile_location", "inventory_type"))
        else:
            queryset = queryset.prefetch_related("derived_columns__column", "columnlistprofilecolumn_set__column")
            results = self.get_serializer(queryset, many=True).data

        if org.comstock_enabled and inventory_type != "Tax Lot" and profile_location != "Detail View Profile":
            # Add ComStock columns
            results.append(
                {
                    "id": None,
                    "name": "ComStock",
                    "profile_location": profile_location,
                    "inventory_type": inventory_type,
                    "columns": None if brief else self.list_comstock_columns(org_id),
                }
            )

        return Response(results)

    @staticmethod
    def list_comstock_columns(org_id):
        comstock_columns = Column.objects.filter(organization_id=org_id, comstock_mapping__isnull=False).order_by("comstock_mapping")

        results = []
        for index, column in enumerate(comstock_columns):
            results.append(
                {
                    "id": column.id,
                    "pinned": False,
                    "order": index + 1,
                    "column_name": column.column_name,
                    "table_name": column.table_name,
                    "comstock_mapping": column.comstock_mapping,
                }
            )

        return results

    @has_perm_class("requires_root_member_access")
    @action(detail=True, methods=["PUT"])
    def show_populated(self, request, pk):
        column_list_profile = ColumnListProfile.objects.get(pk=pk)
        org_id = self.get_organization(self.request)
        cycle_id = request.data.get("cycle_id")
        inventory_type = request.data.get("inventory_type")
        StateTable = PropertyState if inventory_type == "Property" else TaxLotState
        ViewTable = PropertyView if inventory_type == "Property" else TaxLotView

        # get all the columns and states we need to query
        all_columns = (
            Column.objects.filter(organization_id=org_id, derived_column=None, table_name=StateTable.__name__)
            .exclude(column_name__in=EXCLUDED_API_FIELDS)
            .only("is_extra_data", "column_name")
        )
        state_ids = ViewTable.objects.filter(
            cycle_id=cycle_id,
        ).values_list("state_id", flat=True)

        # filter for only the populated columns
        num_of_nonnulls_by_column_name = Column.get_num_of_nonnulls_by_column_name(state_ids, StateTable, all_columns)
        needed_column_names = [col for col, count in num_of_nonnulls_by_column_name.items() if count > 0]
        needed_columns = Column.objects.filter(column_name__in=needed_column_names, table_name=StateTable.__name__, organization=org_id)

        # set needed columns in there
        column_list_profile.columns.set(needed_columns)
        column_list_profile.save()

        return JsonResponse({"status": "success", "data": self.get_serializer(column_list_profile).data}, status=status.HTTP_200_OK)

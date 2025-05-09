"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed import tasks
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import Column, Organization
from seed.serializers.columns import ColumnSerializer
from seed.serializers.pint import add_pint_unit_suffix
from seed.utils.api import OrgCreateUpdateMixin, OrgValidateMixin, api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


@method_decorator(name="create", decorator=swagger_auto_schema_org_query_param)
@method_decorator(name="update", decorator=swagger_auto_schema_org_query_param)
@method_decorator(name="destroy", decorator=swagger_auto_schema_org_query_param)
class ColumnViewSet(OrgValidateMixin, SEEDOrgNoPatchOrOrgCreateModelViewSet, OrgCreateUpdateMixin):
    """
    create:
        Create a new Column within a specified org or user's currently activated org.
    update:
        Update a column and modify which dataset it belongs to.
    delete:
        Deletes a single column.
    """

    raise_exception = True
    serializer_class = ColumnSerializer
    renderer_classes = (JSONRenderer,)
    model = Column
    pagination_class = None
    parser_classes = (JSONParser, FormParser)

    def get_queryset(self):
        # check if the request is properties or taxlots
        org_id = self.get_organization(self.request)
        return Column.objects.filter(organization_id=org_id)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(required=False),
            AutoSchemaHelper.query_string_field(
                name="inventory_type",
                required=False,
                description='Which inventory type is being matched (for related fields and naming)\nDefault: "property"',
            ),
            AutoSchemaHelper.query_boolean_field(
                name="only_used",
                required=False,
                description="Determine whether or not to show only the used fields "
                "(i.e., only columns that have been mapped)"
                '\nDefault: "false"',
            ),
            AutoSchemaHelper.query_boolean_field(
                name="display_units",
                required=False,
                description='If true, any columns that have units will have them added as a suffix to the display_name\nDefault: "false"',
            ),
        ],
    )
    @api_endpoint_class
    @ajax_request_class
    def list(self, request):
        """
        Retrieves all columns for the user's organization including the raw database columns. Will
        return all the columns across both the Property and Tax Lot tables. The related field will
        be true if the column came from the other table that is not the 'inventory_type' (which
        defaults to Property)
        """
        organization_id = self.get_organization(self.request)
        inventory_type = request.query_params.get("inventory_type", "property")
        only_used = json.loads(request.query_params.get("only_used", "false"))
        columns = Column.retrieve_all(organization_id, inventory_type, only_used)
        organization = Organization.objects.get(pk=organization_id)
        if json.loads(request.query_params.get("display_units", "true")):
            columns = [add_pint_unit_suffix(organization, x) for x in columns]
        return JsonResponse(
            {
                "status": "success",
                "columns": columns,
            }
        )

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_root_member_access")
    def create(self, request):
        org_id = self.get_organization(self.request)

        table_name = self.request.data.get("table_name")
        if table_name not in {"PropertyState", "TaxLotState"}:
            return JsonResponse(
                {"status": "error", "message": 'table_name must be "PropertyState" or "TaxLotState"'}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # set request data organization_id to org_id just in case it is not set or incorrectly set
            self.request.data["organization_id"] = org_id

            new_column = Column.objects.create(is_extra_data=True, **self.request.data)
            new_column.save()
        except ValidationError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse(
            {
                "status": "success",
                "column": ColumnSerializer(new_column).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    def retrieve(self, request, pk=None):
        """
        This API endpoint retrieves a Column
        """
        organization_id = self.get_organization(self.request)
        # check if column exists for the organization
        try:
            c = Column.objects.get(pk=pk)
        except Column.DoesNotExist:
            return JsonResponse({"status": "error", "message": f"column with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if c.organization.id != organization_id:
            return JsonResponse(
                {"status": "error", "message": "Organization ID mismatch between column and organization"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return JsonResponse({"status": "success", "column": ColumnSerializer(c).data})

    @ajax_request_class
    @has_perm_class("requires_root_member_access")
    def update(self, request, pk=None):
        organization_id = self.get_organization(request)

        request.data["shared_field_type"] = request.data["sharedFieldType"]
        del request.data["sharedFieldType"]

        # Ensure ComStock uniqueness across properties and taxlots together
        if request.data["comstock_mapping"] is not None:
            Column.objects.filter(organization_id=organization_id, comstock_mapping=request.data["comstock_mapping"]).update(
                comstock_mapping=None
            )

        try:
            result = super().update(request, pk)
        except IntegrityError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return result

    @ajax_request_class
    @has_perm_class("requires_root_member_access")
    def destroy(self, request, pk=None):
        org_id = self.get_organization(request)
        try:
            column = Column.objects.get(id=pk, organization_id=org_id)
        except Column.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": f"Cannot find column in org={org_id} with pk={pk}"}, status=status.HTTP_404_NOT_FOUND
            )

        if not column.is_extra_data:
            return JsonResponse({"success": False, "message": "Only extra_data columns can be deleted"}, status=status.HTTP_400_BAD_REQUEST)

        if column.table_name not in {"PropertyState", "TaxLotState"}:
            return JsonResponse(
                {"success": False, "message": f"Unexpected table_name '{column.table_name}' for column with pk={pk}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        result = tasks.delete_organization_column(column.id, org_id)
        return JsonResponse(result)

    @ajax_request_class
    @has_perm_class("requires_root_member_access")
    @action(detail=False, methods=["POST"])
    def update_multiple(self, request):
        org_id = self.get_organization(self.request)

        table_name = self.request.data.get("table_name")
        if table_name not in {"PropertyState", "TaxLotState"}:
            return JsonResponse(
                {"status": "error", "message": 'table_name must be "PropertyState" or "TaxLotState"'}, status=status.HTTP_400_BAD_REQUEST
            )

        changes = request.data.get("changes")
        key = "".join(str(x) for x in changes)
        result = tasks.update_multiple_columns(key, table_name, org_id, changes)
        return JsonResponse(result)

    @swagger_auto_schema(request_body=AutoSchemaHelper.schema_factory({"new_column_name": "string", "overwrite": "boolean"}))
    @ajax_request_class
    @has_perm_class("requires_root_member_access")
    @action(detail=True, methods=["POST"])
    def rename(self, request, pk=None):
        """
        This API endpoint renames a Column
        """
        org_id = self.get_organization(request)
        try:
            column = Column.objects.get(id=pk, organization_id=org_id)
        except Column.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": f"Cannot find column in org={org_id} with pk={pk}"}, status=status.HTTP_404_NOT_FOUND
            )

        new_column_name = request.data.get("new_column_name", None)
        overwrite = request.data.get("overwrite", False)
        if not new_column_name:
            return JsonResponse(
                {"success": False, "message": 'You must specify the name of the new column as "new_column_name"'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = column.rename_column(new_column_name, overwrite)
        if not result[0]:
            return JsonResponse(
                {"success": False, "message": f'Unable to rename column with message: "{result[1]}"'}, status=status.HTTP_400_BAD_REQUEST
            )
        else:
            return JsonResponse({"success": True, "message": result[1]})

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_string_field(
                "inventory_type", required=True, description='Inventory Type, either "property" or "taxlot"'
            ),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    @action(detail=False, methods=["GET"])
    def mappable(self, request):
        """
        List only inventory columns that are mappable
        """
        organization_id = int(self.get_organization(request))
        inventory_type = request.query_params.get("inventory_type")
        if inventory_type not in {"property", "taxlot"}:
            return JsonResponse({"status": "error", "message": 'Query param `inventory_type` must be "property" or "taxlot"'})
        columns = Column.retrieve_mapping_columns(organization_id, inventory_type)

        return JsonResponse({"status": "success", "columns": columns})

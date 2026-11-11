"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_serializer
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed import tasks
from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import Column, Organization
from seed.serializers.columns import ColumnSerializer
from seed.serializers.pint import add_pint_unit_suffix
from seed.utils.api import OrgCreateUpdateMixin, OrgValidateMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

# Column attributes that `update_multiple` must not change, since they would move or overwrite another organization's column
PROTECTED_COLUMN_ATTRIBUTES = {"id", "pk", "organization", "organization_id"}

TABLE_NAME_SCHEMA = {"type": "string", "enum": ["PropertyState", "TaxLotState"]}
# The request body may provide the organization instead of the query string
BODY_ORG_ID_SCHEMA = {"type": "integer", "description": "Organization ID (alternative to the `organization_id` query parameter)"}
query_or_body_org_id_field = AutoSchemaHelper.query_org_id_field(
    required=False, description="Organization ID; required unless `organization_id` is provided in the request body"
)
progress_schema = AutoSchemaHelper.schema_factory(
    {"status": "string", "status_message": "string", "progress": "number", "progress_key": "string", "message": "string"},
    description="Progress of the background task; poll the progress endpoint with `progress_key` for updates",
)


# Schema only: `update` renames `sharedFieldType` to `shared_field_type`
class ColumnUpdateSerializer(ColumnSerializer):
    """Column fields, with `sharedFieldType` (as returned by the column list) in place of `shared_field_type`"""

    def get_fields(self):
        fields = super().get_fields()
        fields["sharedFieldType"] = fields.pop("shared_field_type")
        return fields


# Schema only: a column as returned by `Column.retrieve_all` and `Column.retrieve_mapping_columns`
class ColumnListItemSerializer(ColumnUpdateSerializer):
    def get_fields(self):
        fields = super().get_fields()
        fields["related"] = serializers.BooleanField(
            required=False, help_text="Whether the column belongs to the other inventory type than the requested `inventory_type`"
        )
        fields["pinnedLeft"] = serializers.BooleanField(required=False, help_text="Only present (and true) for pinned columns")
        return fields


@extend_schema_serializer(many=False)
class ColumnsResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    columns = ColumnListItemSerializer(many=True)


class ColumnResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    column = ColumnSerializer()


class ColumnViewSet(OrgValidateMixin, SEEDOrgNoPatchOrOrgCreateModelViewSet, OrgCreateUpdateMixin):
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

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(
                required=False, description="Optional org id which overrides the users (default) current org id"
            ),
            AutoSchemaHelper.query_enum_field(
                "inventory_type",
                required=False,
                enum=["property", "taxlot"],
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
                description='If true, any columns that have units will have them added as a suffix to the display_name\nDefault: "true"',
            ),
        ],
        responses=ColumnsResponseSerializer,
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
        ]
    )
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

    @extend_schema(
        parameters=[query_or_body_org_id_field],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "organization_id": BODY_ORG_ID_SCHEMA,
                    "table_name": TABLE_NAME_SCHEMA,
                    "column_name": {"type": "string"},
                },
                "required": ["table_name", "column_name"],
                "additionalProperties": True,
                "description": "Other Column model fields (e.g., `display_name`, `column_description`, `data_type`) may also be set; "
                "`is_extra_data` is always true",
            }
        },
        responses={201: ColumnResponseSerializer},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def create(self, request):
        """
        Create a new extra data Column within the organization
        """
        org_id = self.get_organization(self.request)

        table_name = self.request.data.get("table_name")
        if table_name not in {"PropertyState", "TaxLotState"}:
            return JsonResponse(
                {"status": "error", "message": 'table_name must be "PropertyState" or "TaxLotState"'}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # The column always belongs to the organization and is extra data, whatever the request data says
            # (`items()` gives single values for form data too)
            fields = {**dict(self.request.data.items()), "organization_id": org_id, "is_extra_data": True}
            with transaction.atomic():
                new_column = Column.objects.create(**fields)
                new_column.save()
        except (IntegrityError, TypeError, ValueError, ValidationError) as e:
            # TypeError and ValueError come from unknown fields and invalid values
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse(
            {
                "status": "success",
                "column": ColumnSerializer(new_column).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(
                required=False, description="Optional org id which overrides the users (default) current org id"
            )
        ],
        responses=ColumnResponseSerializer,
    )
    @method_decorator(
        [
            ajax_request,
        ]
    )
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

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request={"application/json": ColumnUpdateSerializer},
        responses=ColumnSerializer,
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def update(self, request, pk=None):
        """
        Update a column
        """
        organization_id = self.get_organization(request)

        if "sharedFieldType" in request.data:
            request.data["shared_field_type"] = request.data.pop("sharedFieldType")

        try:
            # Undo the ComStock mapping changes if the column is not found or the update fails
            with transaction.atomic():
                # Ensure ComStock uniqueness across properties and taxlots together
                if request.data.get("comstock_mapping") is not None:
                    Column.objects.filter(organization_id=organization_id, comstock_mapping=request.data["comstock_mapping"]).update(
                        comstock_mapping=None
                    )

                return super().update(request, pk)
        except IntegrityError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(parameters=[AutoSchemaHelper.query_org_id_field()], responses={200: progress_schema})
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def destroy(self, request, pk=None):
        """
        Deletes a single extra data column, removing its data from the inventory in a background task
        """
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

    @extend_schema(
        parameters=[query_or_body_org_id_field],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "organization_id": BODY_ORG_ID_SCHEMA,
                    "table_name": TABLE_NAME_SCHEMA,
                    "changes": {
                        "type": "object",
                        "additionalProperties": {"type": "object", "description": "Column attribute names mapped to their new values"},
                        "description": "IDs of the organization's columns mapped to their changes",
                    },
                },
                "required": ["table_name", "changes"],
            }
        },
        responses={200: progress_schema},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    @action(detail=False, methods=["POST"])
    def update_multiple(self, request):
        """
        Updates several columns, rehashing the inventory if `is_excluded_from_hash` changes
        """
        org_id = self.get_organization(self.request)

        table_name = self.request.data.get("table_name")
        if table_name not in {"PropertyState", "TaxLotState"}:
            return JsonResponse(
                {"status": "error", "message": 'table_name must be "PropertyState" or "TaxLotState"'}, status=status.HTTP_400_BAD_REQUEST
            )

        changes = request.data.get("changes")
        if not isinstance(changes, dict) or Column.objects.filter(organization_id=org_id, pk__in=changes).count() != len(changes):
            return JsonResponse(
                {"status": "error", "message": "changes must map IDs of the organization's columns to their changes"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not all(isinstance(attributes, dict) and not PROTECTED_COLUMN_ATTRIBUTES & attributes.keys() for attributes in changes.values()):
            return JsonResponse(
                {"status": "error", "message": f"Column changes must be objects that do not change {sorted(PROTECTED_COLUMN_ATTRIBUTES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Columns are saved in a background task, so reject geometry matching criteria up front
        columns = Column.objects.filter(organization_id=org_id, pk__in=changes).in_bulk()
        if any(
            attributes.get("is_matching_criteria", columns[int(pk)].is_matching_criteria) and columns[int(pk)].is_geometry
            for pk, attributes in changes.items()
        ):
            return JsonResponse(
                {"status": "error", "message": "Geometry columns can't be matching criteria"}, status=status.HTTP_400_BAD_REQUEST
            )

        key = "".join(str(x) for x in changes)
        result = tasks.update_multiple_columns(key, table_name, org_id, changes)
        return JsonResponse(result)

    @extend_schema(
        parameters=[query_or_body_org_id_field],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "organization_id": BODY_ORG_ID_SCHEMA,
                    "new_column_name": {"type": "string"},
                    "overwrite": {
                        "type": "boolean",
                        "default": False,
                        "description": "Whether to overwrite the data of an existing column with the new name",
                    },
                },
                "required": ["new_column_name"],
            }
        },
        responses={200: AutoSchemaHelper.schema_factory({"success": "boolean", "message": "string"})},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
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

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_enum_field("inventory_type", enum=["property", "taxlot"], description="Inventory Type"),
        ],
        responses=ColumnsResponseSerializer,
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=False, methods=["GET"])
    def mappable(self, request):
        """
        List only inventory columns that are mappable
        """
        organization_id = int(self.get_organization(request))
        inventory_type = request.query_params.get("inventory_type")
        if inventory_type not in {"property", "taxlot"}:
            return JsonResponse(
                {"status": "error", "message": 'Query param `inventory_type` must be "property" or "taxlot"'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        columns = Column.retrieve_mapping_columns(organization_id, inventory_type)

        return JsonResponse({"status": "success", "columns": columns})

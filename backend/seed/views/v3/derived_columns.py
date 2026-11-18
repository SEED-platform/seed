"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from copy import deepcopy

import django.core.exceptions
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request, require_organization_id
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import Column, DerivedColumn, PropertyView, TaxLotView
from seed.serializers.derived_columns import DerivedColumnSerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper, extend_schema_org_query_param

derived_column_id_field = AutoSchemaHelper.path_id_field("Derived column ID")
# Returned (as the errors of a bad request) when a parameter's source column belongs to another organization
SOURCE_COLUMN_ORG_ERRORS = {"parameters": ["Source columns must belong to the organization"]}


# Schema only: the organization is set from the query string
@extend_schema_serializer(exclude_fields=["organization"])
class DerivedColumnWriteSerializer(DerivedColumnSerializer):
    pass


class DerivedColumnResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    derived_column = DerivedColumnSerializer()


@extend_schema_serializer(many=False)
class DerivedColumnsResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    derived_columns = DerivedColumnSerializer(many=True)


def source_columns_in_org(serializer, org_id):
    """Whether the source columns of a validated serializer's parameters all belong to the organization"""
    parameters = serializer.validated_data.get("derivedcolumnparameter_set", [])
    return all(parameter["source_column"].organization_id == int(org_id) for parameter in parameters)


@extend_schema_org_query_param
class DerivedColumnViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = DerivedColumnSerializer
    model = DerivedColumn

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_enum_field(
                "inventory_type", required=False, enum=["properties", "taxlots"], description="Inventory type to filter by"
            )
        ],
        responses=DerivedColumnsResponseSerializer,
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    def list(self, request):
        org = self.get_organization(request)

        filter_params = {
            "organization": org,
        }

        inventory_type = {
            "properties": DerivedColumn.PROPERTY_TYPE,
            "taxlots": DerivedColumn.TAXLOT_TYPE,
        }.get(request.query_params.get("inventory_type"))

        if inventory_type is not None:
            filter_params["inventory_type"] = inventory_type

        queryset = DerivedColumn.objects.filter(**filter_params)

        return JsonResponse({"status": "success", "derived_columns": DerivedColumnSerializer(queryset, many=True).data})

    @extend_schema(parameters=[derived_column_id_field], responses=DerivedColumnResponseSerializer)
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    def retrieve(self, request, pk):
        org = self.get_organization(request)

        try:
            return JsonResponse(
                {"status": "success", "derived_column": DerivedColumnSerializer(DerivedColumn.objects.get(organization=org, id=pk)).data}
            )
        except DerivedColumn.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"Derived column with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(request={"application/json": DerivedColumnWriteSerializer}, responses={200: DerivedColumnResponseSerializer})
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_owner"),
        ]
    )
    def create(self, request):
        org_id = self.get_organization(request)

        data = deepcopy(request.data)
        data.update({"organization": org_id})
        serializer = DerivedColumnSerializer(data=data)
        if not serializer.is_valid() or not source_columns_in_org(serializer, org_id):
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Bad request",
                    "errors": serializer.errors or SOURCE_COLUMN_ORG_ERRORS,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            serializer.save()

            update_derived_data(serializer.data["id"], org_id, serializer.data["inventory_type"])

            return JsonResponse(
                {
                    "status": "success",
                    "derived_column": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict

            # rename key __all__ to general to make it more user friendly
            if "__all__" in message_dict:
                message_dict["general"] = message_dict.pop("__all__")
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Bad request",
                    "errors": message_dict,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        parameters=[derived_column_id_field],
        request={"application/json": DerivedColumnWriteSerializer(partial=True)},
        responses=DerivedColumnResponseSerializer,
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_owner"),
        ]
    )
    def update(self, request, pk):
        org_id = self.get_organization(request)

        derived_column = None
        try:
            derived_column = DerivedColumn.objects.get(id=pk, organization_id=org_id)
        except DerivedColumn.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"Derived column with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        data = deepcopy(request.data)
        data.update({"organization": org_id})
        serializer = DerivedColumnSerializer(derived_column, data=data, partial=True)
        if not serializer.is_valid() or not source_columns_in_org(serializer, org_id):
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Bad request",
                    "errors": serializer.errors or SOURCE_COLUMN_ORG_ERRORS,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            serializer.save()
            if "name" in data:
                Column.objects.filter(derived_column=pk).update(
                    column_name=data["name"], display_name=data["name"], column_description=data["name"]
                )

            if "parameters" in data or "expression" in data:
                update_derived_data(serializer.data["id"], org_id, serializer.data["inventory_type"])

            return JsonResponse(
                {
                    "status": "success",
                    "derived_column": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict

            # rename key __all__ to general to make it more user friendly
            if "__all__" in message_dict:
                message_dict["general"] = message_dict.pop("__all__")
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Bad request",
                    "errors": message_dict,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        parameters=[derived_column_id_field],
        responses={200: AutoSchemaHelper.schema_factory({"status": "string", "message": "string"})},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_owner"),
        ]
    )
    def destroy(self, request, pk):
        org_id = self.get_organization(request)

        try:
            DerivedColumn.objects.get(id=pk, organization_id=org_id).delete()
        except DerivedColumn.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"Derived column with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        return JsonResponse(
            {
                "status": "success",
                "message": "Successfully deleted derived column",
            }
        )

    @extend_schema(
        parameters=[
            derived_column_id_field,
            AutoSchemaHelper.query_integer_field(name="cycle_id", required=True, description="Cycle to evaluate"),
            OpenApiParameter(
                "inventory_ids",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                required=True,
                many=True,
                explode=False,
                description="Comma-separated list of inventory IDs (i.e., Property or TaxLot)",
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "value": {"type": "number", "nullable": True, "description": "null if it can't be evaluated"},
                            },
                        },
                    },
                },
                "description": "The derived column's value for each accessible inventory in the cycle",
            }
        },
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def evaluate(self, request, pk):
        org = self.get_organization(request)

        try:
            cycle_id = request.query_params["cycle_id"]
            inventory_ids = [int(x) for x in request.query_params["inventory_ids"].split(",")]
        except (KeyError, ValueError):
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Bad request",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        derived_column = (
            DerivedColumn.objects.filter(id=pk, organization=org)
            .prefetch_related("derivedcolumnparameter_set", "derivedcolumnparameter_set__source_column")
            .first()
        )
        if derived_column is None:
            return JsonResponse(
                {"status": "error", "message": f"Derived column with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        inventory_map = {
            DerivedColumn.PROPERTY_TYPE: ("property", PropertyView),
            DerivedColumn.TAXLOT_TYPE: ("taxlot", TaxLotView),
        }
        inventory_name, view_model = inventory_map[derived_column.inventory_type]

        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        inventory_views = view_model.objects.filter(
            **{
                f"{inventory_name}_id__in": inventory_ids,
                f"{inventory_name}__organization": org,
                "cycle_id": cycle_id,
                f"{inventory_name}__access_level_instance__lft__gte": access_level_instance.lft,
                f"{inventory_name}__access_level_instance__rgt__lte": access_level_instance.rgt,
            }
        ).prefetch_related("state", inventory_name)

        results = []
        for view in inventory_views:
            results.append({"id": getattr(view, inventory_name).id, "value": derived_column.evaluate(view.state)})

        return JsonResponse({"status": "success", "results": results})


def update_derived_data(derived_column_id, org_id, inventory_type):
    from seed.tasks import update_state_derived_data

    Column.objects.filter(derived_column=derived_column_id).update(is_updating=True)
    if inventory_type == "Property":
        kwargs = {"property_state_ids": list(PropertyView.objects.filter(property__organization=org_id).values_list("state_id", flat=True))}
    else:
        kwargs = {"taxlot_state_ids": list(TaxLotView.objects.filter(taxlot__organization=org_id).values_list("state_id", flat=True))}
    update_state_derived_data(derived_column_ids=[derived_column_id], **kwargs)

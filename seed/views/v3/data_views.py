"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from copy import deepcopy

import django.core.exceptions
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_serializer, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request, require_organization_id
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models.columns import Column
from seed.models.data_views import DataView
from seed.serializers.data_views import DataViewSerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper

data_view_id_field = AutoSchemaHelper.path_id_field("Data view ID")
DATA_VIEW_PROPERTIES = {
    "name": {"type": "string"},
    "cycles": {"type": "array", "items": {"type": "integer"}},
    "filter_groups": {"type": "array", "items": {"type": "integer"}},
    "parameters": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "column": {"type": "integer"},
                "location": {"type": "string"},
                "aggregations": {"type": "array", "items": {}},
                "target": {"type": "string"},
            },
            "required": ["column", "location"],
        },
    },
}
data_view_response = inline_serializer("DataViewResponse", fields={"status": serializers.CharField(), "data_view": DataViewSerializer()})


# the list action's response is a single envelope object, not an array
@extend_schema_serializer(many=False)
class DataViewListResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    data_views = DataViewSerializer(many=True)


class DataViewViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = DataViewSerializer
    model = DataView

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={200: DataViewListResponseSerializer},
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
        organization_id = self.get_organization(request)
        data_view_queryset = DataView.objects.filter(organization=organization_id)

        return JsonResponse(
            {"status": "success", "data_views": DataViewSerializer(data_view_queryset, many=True).data}, status=status.HTTP_200_OK
        )

    @extend_schema(
        parameters=[data_view_id_field, AutoSchemaHelper.query_org_id_field()],
        responses={200: data_view_response},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    def retrieve(self, request, pk):
        organization = self.get_organization(request)

        try:
            return JsonResponse(
                {"status": "success", "data_view": DataViewSerializer(DataView.objects.get(id=pk, organization=organization)).data},
                status=status.HTTP_200_OK,
            )
        except DataView.DoesNotExist:
            return JsonResponse({"status": "error", "message": f"DataView with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        parameters=[data_view_id_field, AutoSchemaHelper.query_org_id_field()],
        responses={200: AutoSchemaHelper.schema_factory({"status": "string", "message": "string"})},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def destroy(self, request, pk):
        organization_id = self.get_organization(request)

        try:
            DataView.objects.get(id=pk, organization=organization_id).delete()
        except DataView.DoesNotExist:
            return JsonResponse({"status": "error", "message": f"DataView with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse({"status": "success", "message": f"Successfully deleted DataView ID {pk}"}, status=status.HTTP_200_OK)

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request={"application/json": {"type": "object", "properties": DATA_VIEW_PROPERTIES, "required": ["name", "cycles", "parameters"]}},
        responses={200: data_view_response},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def create(self, request):
        org_id = self.get_organization(request)
        data = deepcopy(request.data)
        data.update({"organization": org_id})
        serializer = DataViewSerializer(data=data)

        if not serializer.is_valid():
            error_response = {"status": "error", "message": "Data Validation Error", "errors": serializer.errors}

            return JsonResponse(error_response, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save()
            return JsonResponse({"status": "success", "data_view": serializer.data}, status=status.HTTP_200_OK)
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict
            return JsonResponse({"status": "error", "message": "Bad Request", "errors": message_dict}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[data_view_id_field, AutoSchemaHelper.query_org_id_field()],
        request={"application/json": {"type": "object", "properties": DATA_VIEW_PROPERTIES}},
        responses={200: data_view_response},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def update(self, request, pk):
        org_id = self.get_organization(request)

        data_view = None
        try:
            data_view = DataView.objects.get(id=pk, organization=org_id)
        except DataView.DoesNotExist:
            return JsonResponse({"status": "error", "message": f"DataView with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        data = deepcopy(request.data)
        data.update({"organization": org_id})
        serializer = DataViewSerializer(data_view, data=data, partial=True)
        if not serializer.is_valid():
            return JsonResponse(
                {"status": "error", "message": "Bad Request", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            serializer.save()
            return JsonResponse(
                {
                    "status": "success",
                    "data_view": serializer.data,
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
        parameters=[data_view_id_field, AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body({"columns": ["integer"]}, required=["columns"]),
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "data": {
                        "meta": {"organization": "integer", "data_view": "integer"},
                        "views_by_filter_group_id": "object",
                        "columns_by_id": "object",
                        "graph_data": {"labels": ["string"], "datasets": ["object"]},
                    },
                }
            )
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
    @action(detail=True, methods=["POST"])
    def evaluate(self, request, pk):
        """
        Aggregate the given columns' values over the data view's cycles and filter groups, within your access level.
        """
        organization = self.get_organization(request)
        deepcopy(request.data)
        data = deepcopy(request.data)

        try:
            data_view = DataView.objects.get(id=pk, organization=organization)
        except DataView.DoesNotExist:
            return JsonResponse({"status": "error", "message": f"DataView with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        columns = Column.objects.filter(id__in=data["columns"], organization_id=organization)
        if len(columns) != len(data["columns"]):
            return JsonResponse(
                {"status": "error", "message": f"Columns with ids {data['columns']} do not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        user_ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        response = data_view.evaluate(columns, user_ali)
        return JsonResponse({"status": "success", "data": response})

    @extend_schema(
        parameters=[data_view_id_field, AutoSchemaHelper.query_org_id_field()],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {"status": "string", "data": "object"},
                description="`data` maps each filter group ID to an object of property view IDs to display names",
            )
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
    def inventory(self, request, pk):
        """
        List the property views matching each of the data view's filter groups, within your access level.
        """
        organization = self.get_organization(request)
        deepcopy(request.data)

        try:
            data_view = DataView.objects.get(id=pk, organization=organization)
        except DataView.DoesNotExist:
            return JsonResponse({"status": "error", "message": f"DataView with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        user_ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        response = data_view.get_inventory(user_ali)
        return JsonResponse({"status": "success", "data": response})

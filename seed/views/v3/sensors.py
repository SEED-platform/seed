"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db.models import Q
from django.db.utils import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import DataLogger, PropertyView, Sensor
from seed.utils.api import OrgMixin, ProfileIdMixin
from seed.utils.api_schema import AutoSchemaHelper, EmptySerializer
from seed.utils.sensors import PropertySensorReadingsExporter

SENSOR_EDITABLE_FIELDS = ("display_name", "location_description", "description", "sensor_type", "units", "column_name")


@extend_schema(
    parameters=[
        AutoSchemaHelper.query_org_id_field(),
        AutoSchemaHelper.path_id_field("ID of the property view", name="property_pk"),
    ]
)
class SensorViewSet(generics.GenericAPIView, viewsets.ViewSet, OrgMixin, ProfileIdMixin):
    # For the Swagger page, GenericAPIView asserts a value exists for `queryset`
    queryset = Sensor.objects.none()
    serializer_class = EmptySerializer
    # Only `usage` pages its readings, and it does so itself
    pagination_class = None

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_integer_field(
                "page", False, 'Page of readings to return (only when "interval" is "Exact"), defaults to 1'
            ),
            AutoSchemaHelper.query_integer_field(
                "per_page", False, 'Number of readings per page (only when "interval" is "Exact"), defaults to 500'
            ),
        ],
        request=AutoSchemaHelper.json_body(
            {
                "interval": (("Exact", "Exact"), ("Month", "Month"), ("Year", "Year")),
                "excluded_sensor_ids": ["integer"],
                "showOnlyOccupiedReadings": "boolean",
            },
            required=["interval", "excluded_sensor_ids"],
        ),
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "readings": ["object"],
                    "column_defs": [{"field": "string", "displayName": "string", "_filter_type": "string"}],
                    "pagination": {
                        "page": "integer",
                        "start": "integer",
                        "end": "integer",
                        "num_pages": "integer",
                        "has_next": "boolean",
                        "has_previous": "boolean",
                        "total": "integer",
                    },
                },
                description='Each reading maps its "timestamp", "month", or "year" and the column_defs fields of the sensors to '
                'their (average) readings. pagination is only included when "interval" is "Exact".',
            )
        },
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(property_view_id_kwarg="property_pk"),
        ]
    )
    @action(detail=False, methods=["POST"])
    def usage(self, request, property_pk):
        """
        Retrieves sensor usage information
        """
        org_id = self.get_organization(request)
        page = request.query_params.get("page")
        per_page = request.query_params.get("per_page")

        body = dict(request.data)
        interval = body["interval"]
        excluded_sensor_ids = body["excluded_sensor_ids"]
        show_only_occupied_readings = body.get("showOnlyOccupiedReadings", False)

        property_view = PropertyView.objects.get(pk=property_pk, cycle__organization_id=org_id)
        property_id = property_view.property.id

        exporter = PropertySensorReadingsExporter(property_id, org_id, excluded_sensor_ids, show_only_occupied_readings)

        if interval != "Exact" and (page or per_page):
            return JsonResponse(
                {"success": False, "message": 'Cannot pass query parameter "page" or "per_page" unless "interval" is "Exact"'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        page = page if page is not None else 1
        per_page = per_page if per_page is not None else 500

        return exporter.readings_and_column_defs(interval, page, per_page)

    @extend_schema(
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "id": "integer",
                    "display_name": "string",
                    "location_description": "string",
                    "description": "string",
                    "sensor_type": "string",
                    "units": "string",
                    "column_name": "string",
                    "data_logger": "string",
                    "data_logger_id": "integer",
                }
            )
        }
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(property_view_id_kwarg="property_pk"),
        ]
    )
    def list(self, request, property_pk):
        """
        Retrieves sensors for the property
        """
        org_id = self.get_organization(request)

        property_view = PropertyView.objects.get(pk=property_pk, cycle__organization_id=org_id)
        property_id = property_view.property.id

        res = []
        for data_logger in DataLogger.objects.filter(property_id=property_id):
            for sensor in Sensor.objects.filter(Q(data_logger_id=data_logger.id)):
                res.append(
                    {
                        "id": sensor.id,
                        "display_name": sensor.display_name,
                        "location_description": sensor.location_description,
                        "description": sensor.description,
                        "sensor_type": sensor.sensor_type,
                        "units": sensor.units,
                        "column_name": sensor.column_name,
                        "data_logger": data_logger.display_name,
                        "data_logger_id": data_logger.id,
                    }
                )

        return res

    @extend_schema(
        parameters=[AutoSchemaHelper.path_id_field("ID of the sensor")],
        responses={204: OpenApiResponse(description="Sensor deleted")},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(property_view_id_kwarg="property_pk"),
        ]
    )
    def destroy(self, request, property_pk, pk):
        """
        Deletes a sensor of the property
        """
        org_id = self.get_organization(request)

        # get sensor
        try:
            sensor = Sensor.objects.get(pk=pk, data_logger__property__organization_id=org_id, data_logger__property__views=property_pk)
        except Sensor.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such Sensor found."}, status=status.HTTP_404_NOT_FOUND)

        # delete sensor
        sensor.delete()

        return JsonResponse(
            {
                "status": "success",
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    @extend_schema(
        parameters=[AutoSchemaHelper.path_id_field("ID of the sensor")],
        request=AutoSchemaHelper.json_body(dict.fromkeys(SENSOR_EDITABLE_FIELDS, "string")),
        responses={200: AutoSchemaHelper.schema_factory({"status": "string"})},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(property_view_id_kwarg="property_pk"),
        ]
    )
    def update(self, request, property_pk, pk):
        """
        Updates a sensor of the property
        """
        org_id = self.get_organization(request)
        data = {field: value for field, value in request.data.items() if field in SENSOR_EDITABLE_FIELDS}

        # get sensor
        sensor_query = Sensor.objects.filter(data_logger__property__organization_id=org_id, data_logger__property__views=property_pk, pk=pk)
        if sensor_query.count() != 1:
            return JsonResponse({"status": "error", "message": "No such Sensor found."}, status=status.HTTP_404_NOT_FOUND)

        # update
        try:
            sensor_query.update(**data)
        except IntegrityError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse(
            {
                "status": "success",
            },
            status=status.HTTP_200_OK,
        )

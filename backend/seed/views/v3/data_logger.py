"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from datetime import datetime, timedelta

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.utils.timezone import get_default_timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import DataLogger, PropertyView
from seed.serializers.data_loggers import DataLoggerSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import AutoSchemaHelper

DATA_LOGGER_FIELDS = {
    "display_name": "string",
    "identifier": "string",
    "location_description": "string",
    "manufacturer_name": "string",
    "model_name": "string",
    "serial_number": "string",
}
PROPERTY_VIEW_ID_PARAM = AutoSchemaHelper.query_integer_field("property_view_id", True, "ID of the property view of the data loggers")
DATA_LOGGER_ID_PARAM = AutoSchemaHelper.path_id_field("ID of the data logger")


@extend_schema(parameters=[AutoSchemaHelper.query_org_id_field()])
class DataLoggerViewSet(viewsets.ViewSet, OrgMixin):
    model = DataLogger
    serializer_class = DataLoggerSerializer
    raise_exception = True

    @extend_schema(
        parameters=[PROPERTY_VIEW_ID_PARAM],
        responses={200: AutoSchemaHelper.schema_factory([{"id": "integer", **DATA_LOGGER_FIELDS}])},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(),
        ]
    )
    def list(self, request):
        """
        Retrieves data_loggers for the property
        """
        org_id = self.get_organization(request)
        property_view_id = request.GET["property_view_id"]

        property_view = PropertyView.objects.get(pk=property_view_id, cycle__organization_id=org_id)
        property_id = property_view.property.id

        res = []
        for data_logger in DataLogger.objects.filter(property_id=property_id):
            res.append(
                {
                    "id": data_logger.id,
                    "display_name": data_logger.display_name,
                    "location_description": data_logger.location_description,
                    "manufacturer_name": data_logger.manufacturer_name,
                    "model_name": data_logger.model_name,
                    "serial_number": data_logger.serial_number,
                    "identifier": data_logger.identifier,
                }
            )

        return res

    @extend_schema(
        parameters=[PROPERTY_VIEW_ID_PARAM],
        request=AutoSchemaHelper.json_body(DATA_LOGGER_FIELDS, required=["display_name"]),
        responses={200: DataLoggerSerializer},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(),
        ]
    )
    def create(self, request):
        """
        create data_logger
        """
        org_id = self.get_organization(request)
        property_view_id = request.GET["property_view_id"]

        property_view = PropertyView.objects.get(pk=property_view_id, cycle__organization_id=org_id)
        property_id = property_view.property.id

        # for every weekday from 2020-2023, mark as occupied from 8-5
        tz_obj = get_default_timezone()
        start_time = datetime(2020, 1, 1, 0, 0, tzinfo=tz_obj)
        end_time = datetime(2023, 1, 1, 0, 0, tzinfo=tz_obj)

        day = start_time
        is_occupied_data = []
        while day < end_time:
            if day.weekday() <= 4:
                open_time = day + timedelta(hours=8)
                is_occupied_data.append((open_time.isoformat(), True))

                close_time = day + timedelta(hours=17)
                is_occupied_data.append((close_time.isoformat(), False))

            day += timedelta(days=1)

        data = request.data
        data["property"] = property_id
        data["is_occupied_data"] = is_occupied_data
        serializer = DataLoggerSerializer(data=data)

        if not serializer.is_valid():
            return JsonResponse({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        return JsonResponse(serializer.data)

    @extend_schema(parameters=[DATA_LOGGER_ID_PARAM], responses={204: OpenApiResponse(description="Data logger deleted")})
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(data_logger_id_kwarg="pk"),
        ]
    )
    def destroy(self, request, pk):
        org_id = self.get_organization(request)

        # get data logger
        try:
            data_logger = DataLogger.objects.get(property__organization_id=org_id, pk=pk)
        except DataLogger.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such DataLogger found."}, status=status.HTTP_404_NOT_FOUND)

        # delete data logger
        data_logger.delete()

        return JsonResponse(
            {
                "status": "success",
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    @extend_schema(
        parameters=[DATA_LOGGER_ID_PARAM],
        request=AutoSchemaHelper.json_body(DATA_LOGGER_FIELDS, description="Only the provided fields are updated."),
        responses={200: DataLoggerSerializer},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(data_logger_id_kwarg="pk"),
        ]
    )
    def update(self, request, pk):
        org_id = self.get_organization(request)

        try:
            datalogger = DataLogger.objects.get(pk=pk, property__organization=org_id)
        except DataLogger.DoesNotExist:
            return JsonResponse({"status": "error", "errors": "No such resource."})

        serializer = DataLoggerSerializer(datalogger, data=request.data, partial=True)

        if not serializer.is_valid():
            return JsonResponse({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # The data logger can't be moved to another property, whose access level wasn't checked
        serializer.save(property=datalogger.property)
        return JsonResponse(serializer.data)

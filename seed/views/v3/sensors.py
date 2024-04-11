from django.db.models import Q
from django.db.utils import IntegrityError
from django.http import JsonResponse
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.models import DataLogger, PropertyView, Sensor
from seed.utils.api import OrgMixin, ProfileIdMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.sensors import PropertySensorReadingsExporter


class SensorViewSet(generics.GenericAPIView, viewsets.ViewSet, OrgMixin, ProfileIdMixin):
    @ajax_request_class
    @has_perm_class("requires_member")
    @has_hierarchy_access(property_view_id_kwarg="property_pk")
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

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(property_view_id_kwarg="property_pk")
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
                        "type": sensor.sensor_type,
                        "units": sensor.units,
                        "column_name": sensor.column_name,
                        "data_logger": data_logger.display_name,
                    }
                )

        return res

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    @has_perm_class("requires_member")
    @has_hierarchy_access(property_view_id_kwarg="property_pk")
    def destroy(self, request, property_pk, pk):
        """
        Retrieves sensors for the property
        """
        org_id = self.get_organization(request)

        # get sensor
        try:
            sensor = Sensor.objects.get(pk=pk, data_logger__property__organization_id=org_id)
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

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    @has_perm_class("requires_member")
    @has_hierarchy_access(property_view_id_kwarg="property_pk")
    def update(self, request, property_pk, pk):
        org_id = self.get_organization(request)
        data = request.data

        # get sensor
        sensor_query = Sensor.objects.filter(data_logger__property__organization_id=org_id, pk=pk)
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

"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""
from datetime import datetime, timedelta

from django.http import JsonResponse
from pytz import timezone as pytztimezone
from rest_framework import status, viewsets

from config.settings.common import TIME_ZONE
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import (
    has_hierarchy_access,
    has_perm_class
)
from seed.models import DataLogger, PropertyView
from seed.serializers.data_loggers import DataLoggerSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param


class DataLoggerViewSet(viewsets.ViewSet, OrgMixin):
    model = DataLogger
    serializer_class = DataLoggerSerializer
    raise_exception = True

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @has_hierarchy_access()
    def list(self, request):
        """
        Retrieves data_loggers for the property
        """
        org_id = self.get_organization(request)
        property_view_id = request.GET['property_view_id']

        property_view = PropertyView.objects.get(
            pk=property_view_id,
            cycle__organization_id=org_id
        )
        property_id = property_view.property.id

        res = []
        for data_logger in DataLogger.objects.filter(property_id=property_id):
            res.append({
                'id': data_logger.id,
                'display_name': data_logger.display_name,
                'location_description': data_logger.location_description,
                "manufacturer_name": data_logger.manufacturer_name,
                "model_name": data_logger.model_name,
                "serial_number": data_logger.serial_number,
                "identifier": data_logger.identifier,
            })

        return res

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    @has_perm_class('requires_member')
    @has_hierarchy_access()
    def create(self, request):
        """
        create data_logger
        """
        org_id = self.get_organization(request)
        property_view_id = request.GET['property_view_id']

        property_view = PropertyView.objects.get(
            pk=property_view_id,
            cycle__organization_id=org_id
        )
        property_id = property_view.property.id

        # for every weekday from 2020-2023, mark as occupied from 8-5
        tz_obj = pytztimezone(TIME_ZONE)
        start_time = datetime(2020, 1, 1, 0, 0, tzinfo=tz_obj)
        end_time = datetime(2023, 1, 1, 0, 0, tzinfo=tz_obj)

        day = start_time
        is_occupied_data = []
        while day < end_time:
            if day.weekday() <= 4:
                open_time = day + timedelta(hours=8)
                is_occupied_data.append(
                    (open_time.isoformat(), True)
                )

                close_time = day + timedelta(hours=17)
                is_occupied_data.append(
                    (close_time.isoformat(), False)
                )

            day += timedelta(days=1)

        data = request.data
        data['property'] = property_id
        data['is_occupied_data'] = is_occupied_data
        serializer = DataLoggerSerializer(data=data)

        if not serializer.is_valid():
            return JsonResponse({
                'status': 'error',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        return JsonResponse(serializer.data)

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    @has_perm_class('requires_member')
    @has_hierarchy_access(data_logger_id_kwarg='pk')
    def destroy(self, request, pk):
        org_id = self.get_organization(request)

        # get data logger
        try:
            data_logger = DataLogger.objects.get(property__organization_id=org_id, pk=pk)
        except DataLogger.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'No such DataLogger found.'
            }, status=status.HTTP_404_NOT_FOUND)

        # delete data logger
        data_logger.delete()

        return JsonResponse({
            'status': 'success',
        }, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    @has_perm_class('requires_member')
    @has_hierarchy_access(data_logger_id_kwarg='pk')
    def update(self, request, pk):
        org_id = self.get_organization(request)

        try:
            datalogger = DataLogger.objects.get(pk=pk, property__organization=org_id)
        except DataLogger.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'errors': 'No such resource.'
            })

        serializer = DataLoggerSerializer(datalogger, data=request.data, partial=True)

        if not serializer.is_valid():
            return JsonResponse({
                'status': 'error',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return JsonResponse(serializer.data)

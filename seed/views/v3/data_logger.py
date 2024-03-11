"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from datetime import datetime, timedelta

from django.db.utils import IntegrityError
from django.http import JsonResponse
from pytz import timezone as pytztimezone
from rest_framework import status, viewsets

from config.settings.common import TIME_ZONE
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import DataLogger, PropertyView
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param


class DataLoggerViewSet(viewsets.ViewSet, OrgMixin):
    model = DataLogger
    raise_exception = True

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    @has_perm_class('requires_viewer')
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
    def create(self, request):
        """
        create data_logger
        """
        org_id = self.get_organization(request)
        property_view_id = request.GET['property_view_id']

        body = dict(request.data)
        display_name = body['display_name']
        manufacturer_name = body.get('manufacturer_name')
        model_name = body.get('model_name')
        serial_number = body.get('serial_number')
        location_description = body.get("location_description")
        identifier = body.get("identifier")

        property_view = PropertyView.objects.get(
            pk=property_view_id,
            cycle__organization_id=org_id
        )
        property_id = property_view.property.id

        data_logger = DataLogger(
            property_id=property_id,
            display_name=display_name,
            location_description=location_description,
            manufacturer_name=manufacturer_name,
            model_name=model_name,
            serial_number=serial_number,
            identifier=identifier,
        )

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

        data_logger.is_occupied_data = is_occupied_data

        try:
            data_logger.save()
        except IntegrityError:
            result = {
                'status': 'error',
                'message': f'Data Logger name {display_name} is not unique.'
            }
        else:
            result = {
                'id': data_logger.id,
                'display_name': data_logger.display_name,
                'location_description': data_logger.location_description,
                "manufacturer_name": data_logger.manufacturer_name,
                "model_name": data_logger.model_name,
                "serial_number": data_logger.serial_number,
                "identifier": data_logger.identifier,
            }

        return result

    @swagger_auto_schema_org_query_param
    @ajax_request_class
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
    def update(self, request, pk):
        org_id = self.get_organization(request)
        data = request.data

        # get data logger
        data_logger_query = DataLogger.objects.filter(property__organization_id=org_id, pk=pk)
        if data_logger_query.count() != 1:
            return JsonResponse({
                'status': 'error',
                'message': 'No such DataLogger found.'
            }, status=status.HTTP_404_NOT_FOUND)

        # update
        try:
            data_logger_query.update(**data)
        except IntegrityError:
            return JsonResponse({
                'status': 'error',
                'message': f'There is already a datalogger with name "{data["display_name"]}".'
            }, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse({
            'status': 'success',
        }, status=status.HTTP_200_OK)

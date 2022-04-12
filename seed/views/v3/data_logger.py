"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import viewsets
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (PropertyView,
                         DataLogger,
                         )
from seed.models.sensors import Sensor
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.api import OrgMixin
from django.db.utils import IntegrityError
from datetime import datetime, timedelta
from config.settings.common import TIME_ZONE
from pytz import timezone as pytztimezone


class DataLoggerViewSet(viewsets.ViewSet, OrgMixin):
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
                'location_identifier': data_logger.location_identifier,
                'number_of_sensor': len(Sensor.objects.filter(data_logger=data_logger.id).all())
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
        location_identifier = body.get("location_identifier")

        property_view = PropertyView.objects.get(
            pk=property_view_id,
            cycle__organization_id=org_id
        )
        property_id = property_view.property.id

        data_logger = DataLogger(
            property_id=property_id,
            display_name=display_name,
            location_identifier=location_identifier
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
                'location_identifier': data_logger.location_identifier,
                'number_of_sensor': 0
            }

        return result

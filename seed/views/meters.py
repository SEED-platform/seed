# !/usr/bin/env python
# encoding: utf-8

from collections import defaultdict

from config.settings.common import TIME_ZONE

from pytz import timezone

from rest_framework import viewsets
from rest_framework.decorators import list_route

from seed.data_importer.meters_parsers import PMMeterParser
from seed.data_importer.utils import kbtu_thermal_conversion_factors
from seed.decorators import ajax_request_class
from seed.lib.mcm import reader
from seed.models import (
    ImportFile,
    PropertyView,
)


class MeterViewSet(viewsets.ViewSet):

    @ajax_request_class
    @list_route(methods=['POST'])
    def parsed_meters_confirmation(self, request):
        body = dict(request.data)
        file_id = body['file_id']
        org_id = body['organization_id']

        import_file = ImportFile.objects.get(pk=file_id)
        parser = reader.MCMParser(import_file.local_file)
        raw_meter_data = list(parser.data)

        meters_parser = PMMeterParser(org_id, raw_meter_data)

        result = {}

        result["validated_type_units"] = meters_parser.validated_type_units()
        result["proposed_imports"] = meters_parser.proposed_imports()
        result["unlinkable_pm_ids"] = meters_parser.unlinkable_pm_ids

        return result

    @ajax_request_class
    @list_route(methods=['POST'])
    def property_energy_usage(self, request):
        body = dict(request.data)
        property_view_id = body['property_view_id']

        meters = PropertyView.objects.get(pk=property_view_id).property.meters.all()

        # Used to consolidate different readings (types) within the same time window
        start_end_times = defaultdict(lambda: {})

        time_format = "%Y-%m-%d %H:%M:%S"
        tz = timezone(TIME_ZONE)

        # Construct headers using this dictionary's values for frontend to use
        headers = {
            '_start_time': {'field': 'start_time'},
            '_end_time': {'field': 'end_time'},
        }

        for meter in meters:
            type = dict(meter.ENERGY_TYPES)[meter.type]

            headers[type] = {
                'field': type,
                'displayName': type + " (kBtu)",
                'cellFilter': "number: 0",
            }

            for meter_reading in meter.meter_readings.all():
                start_time = meter_reading.start_time.astimezone(tz=tz).strftime(time_format)
                end_time = meter_reading.end_time.astimezone(tz=tz).strftime(time_format)

                times_key = "-".join([start_time, end_time])

                start_end_times[times_key]['start_time'] = start_time
                start_end_times[times_key]['end_time'] = end_time
                start_end_times[times_key][type] = meter_reading.reading.magnitude

        result = {
            'readings': list(start_end_times.values()),
            'headers': list(headers.values())
        }

        return result

    @ajax_request_class
    @list_route(methods=['GET'])
    def valid_types_units(self, request):
        return {
            type: list(units.keys())
            for type, units
            in kbtu_thermal_conversion_factors("US").items()
        }

# !/usr/bin/env python
# encoding: utf-8

from collections import defaultdict

from config.settings.common import TIME_ZONE

from pytz import timezone

from seed.data_importer.utils import kbtu_thermal_conversion_factors

from seed.lib.superperms.orgs.models import Organization
from seed.models import Property


class PropertyMeterReadingsExporter():
    def __init__(self, property_id, org_id):
        self.meters = Property.objects.get(pk=property_id).meters.all()
        self.org_meter_display_settings = Organization.objects.get(pk=org_id).display_meter_units
        self.factors = kbtu_thermal_conversion_factors("US")

    def readings_and_headers(self):
        # Used to consolidate different readings (types) within the same time window
        start_end_times = defaultdict(lambda: {})

        time_format = "%Y-%m-%d %H:%M:%S"
        tz = timezone(TIME_ZONE)

        # Construct headers using this dictionary's values for frontend to use
        headers = {
            '_start_time': {'field': 'start_time'},
            '_end_time': {'field': 'end_time'},
        }

        for meter in self.meters:
            type = dict(meter.ENERGY_TYPES)[meter.type]
            display_unit = self.org_meter_display_settings[type]
            conversion_factor = self.factors[type][display_unit]

            headers[type] = {
                'field': type,
                'displayName': '{} ({})'.format(type, display_unit),
                'cellFilter': "number: 0",
            }

            for meter_reading in meter.meter_readings.all():
                start_time = meter_reading.start_time.astimezone(tz=tz).strftime(time_format)
                end_time = meter_reading.end_time.astimezone(tz=tz).strftime(time_format)

                times_key = "-".join([start_time, end_time])

                start_end_times[times_key]['start_time'] = start_time
                start_end_times[times_key]['end_time'] = end_time
                start_end_times[times_key][type] = meter_reading.reading.magnitude / conversion_factor

        return {
            'readings': list(start_end_times.values()),
            'headers': list(headers.values())
        }

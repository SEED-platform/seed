# !/usr/bin/env python
# encoding: utf-8

from calendar import (
    monthrange,
    month_name,
)

from collections import defaultdict

from config.settings.common import TIME_ZONE

from datetime import (
    datetime,
    timedelta,
)

from django.utils.timezone import make_aware

from pytz import timezone

from seed.data_importer.utils import kbtu_thermal_conversion_factors

from seed.lib.superperms.orgs.models import Organization
from seed.models import Property


class PropertyMeterReadingsExporter():
    def __init__(self, property_id, org_id):
        self.meters = Property.objects.get(pk=property_id).meters.all()
        self.org_meter_display_settings = Organization.objects.get(pk=org_id).display_meter_units
        self.factors = kbtu_thermal_conversion_factors("US")
        self.tz = timezone(TIME_ZONE)

    def readings_and_headers(self, interval):
        if interval == 'Exact':
            return self._exact_usages()
        elif interval == 'Month':
            return self._usages_by_month()

    def _exact_usages(self):
        """
        Returns readings and headers formatted to display all records and their
        start and end times.
        """

        # Used to consolidate different readings (types) within the same time window
        start_end_times = defaultdict(lambda: {})

        # Construct headers using this dictionary's values for frontend to use
        headers = {
            '_start_time': {'field': 'start_time'},
            '_end_time': {'field': 'end_time'},
        }

        time_format = "%Y-%m-%d %H:%M:%S"

        for meter in self.meters:
            type, conversion_factor = self._build_header_info(meter, headers)

            for meter_reading in meter.meter_readings.all():
                start_time = meter_reading.start_time.astimezone(tz=self.tz).strftime(time_format)
                end_time = meter_reading.end_time.astimezone(tz=self.tz).strftime(time_format)

                times_key = "-".join([start_time, end_time])

                start_end_times[times_key]['start_time'] = start_time
                start_end_times[times_key]['end_time'] = end_time
                start_end_times[times_key][type] = meter_reading.reading.magnitude / conversion_factor

        return {
            'readings': list(start_end_times.values()),
            'headers': list(headers.values())
        }

    def _usages_by_month(self):
        """
        Returns readings and headers formatted and aggregated to display all
        records in monthly intervals.

        At a high-level, following algorithm is used to acccomplish this:
            - Identify the first start time and last end time
            - For each month between, aggregate the readings found in that month
                - For more details how that monthly aggregation occurs, see _agg_interval_readings()
        """
        # Used to consolidate different readings (types) within the same month
        monthly_readings = defaultdict(lambda: {})

        # Construct headers using this dictionary's values for frontend to use
        headers = {
            '_month': {'field': 'month'},
        }

        for meter in self.meters:
            type, conversion_factor = self._build_header_info(meter, headers)

            min_time = meter.meter_readings.earliest('start_time').start_time.astimezone(tz=self.tz)
            max_time = meter.meter_readings.latest('end_time').end_time.astimezone(tz=self.tz)

            # Iterate through months
            current_month_time = min_time
            while current_month_time < max_time:
                _weekday, days_in_month = monthrange(current_month_time.year, current_month_time.month)

                unaware_end = datetime(current_month_time.year, current_month_time.month, days_in_month, 23, 59, 59)
                end_of_month = make_aware(unaware_end, timezone=self.tz)

                # Find all meters fully contained within this month (second-level granularity)
                readings = meter.meter_readings.filter(start_time__range=(current_month_time, end_of_month), end_time__range=(current_month_time, end_of_month))
                if readings.exists():
                    reading_month_total = self._agg_interval_readings(current_month_time, readings, end_of_month)

                    if reading_month_total > 0:
                        month_year = '{} {}'.format(month_name[current_month_time.month], current_month_time.year)
                        monthly_readings[month_year]['month'] = month_year
                        monthly_readings[month_year][type] = reading_month_total / conversion_factor

                current_month_time = end_of_month + timedelta(seconds=1)

        return {
            'readings': list(monthly_readings.values()),
            'headers': list(headers.values())
        }

    def _build_header_info(self, meter, headers):
        type = dict(meter.ENERGY_TYPES)[meter.type]
        display_unit = self.org_meter_display_settings[type]
        conversion_factor = self.factors[type][display_unit]

        headers[type] = {
            'field': type,
            'displayName': '{} ({})'.format(type, display_unit),
            'cellFilter': "number: 0",
        }

        return type, conversion_factor

    def _agg_interval_readings(self, current_interval_time, interval_readings, interval_end):
        """
        Returns a total of aggregated readings within a given time interval.

        This is done by the following algorithm:
            1) Use the initial interval time as the current interval time
            2) Get all readings starting at current interval time
            3) Out of those readings, use the one with the latest end time
                a) Take it's actual reading and add it to the running total
                b) Take it's end time and check for remaining readings between this end time and the interval end time
                    i) If remaining readings exist, jump to step 2 with the next earliest start time as the current interval time
                    ii) If no readings exist, end the loop.
        """

        readings_total = 0

        while current_interval_time < interval_end:
            current_time_readings = interval_readings.filter(start_time=current_interval_time)

            if current_time_readings.exists():
                largest_interval = current_time_readings.latest('end_time')
                readings_total += largest_interval.reading.magnitude

                largest_interval_end = largest_interval.end_time.astimezone(tz=self.tz)
                remaining_readings = interval_readings.filter(start_time__range=(largest_interval_end, interval_end))

                if remaining_readings.exists():
                    current_interval_time = remaining_readings.earliest('start_time').start_time.astimezone(tz=self.tz)
                else:
                    current_interval_time = interval_end

        return readings_total

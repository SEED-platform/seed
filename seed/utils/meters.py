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

    def readings_and_column_defs(self, interval):
        if interval == 'Exact':
            return self._usages_by_exact_times()
        elif interval == 'Month':
            return self._usages_by_month()
        elif interval == 'Year':
            return self._usages_by_year()

    def _usages_by_exact_times(self):
        """
        Returns readings and column definitions formatted to display all records and their
        start and end times.
        """

        # Used to consolidate different readings (types) within the same time window
        start_end_times = defaultdict(lambda: {})

        # Construct column_defs using this dictionary's values for frontend to use
        column_defs = {
            '_start_time': {
                'field': 'start_time',
                '_filter_type': 'datetime',
            },
            '_end_time': {
                'field': 'end_time',
                '_filter_type': 'datetime',
            },
        }

        time_format = "%Y-%m-%d %H:%M:%S"

        for meter in self.meters:
            type, conversion_factor = self._build_column_def(meter, column_defs)

            for meter_reading in meter.meter_readings.all():
                start_time = meter_reading.start_time.astimezone(tz=self.tz).strftime(time_format)
                end_time = meter_reading.end_time.astimezone(tz=self.tz).strftime(time_format)

                times_key = "-".join([start_time, end_time])

                start_end_times[times_key]['start_time'] = start_time
                start_end_times[times_key]['end_time'] = end_time
                start_end_times[times_key][type] = meter_reading.reading.magnitude / conversion_factor

        return {
            'readings': list(start_end_times.values()),
            'column_defs': list(column_defs.values())
        }

    def _usages_by_month(self):
        """
        Returns readings and column definitions formatted and aggregated to display all
        records in monthly intervals.

        At a high-level, following algorithm is used to acccomplish this:
            - Identify the first start time and last end time
            - For each month between, aggregate the readings found in that month
                - The highest possible reading total without overlapping times is found
                - For more details how that monthly aggregation occurs, see _max_reading_total()
        """
        # Used to consolidate different readings (types) within the same month
        monthly_readings = defaultdict(lambda: {})

        # Construct column_defs using this dictionary's values for frontend to use
        column_defs = {
            '_month': {
                'field': 'month',
                '_filter_type': 'datetime',
            },
        }

        for meter in self.meters:
            type, conversion_factor = self._build_column_def(meter, column_defs)

            min_time = meter.meter_readings.earliest('start_time').start_time.astimezone(tz=self.tz)
            max_time = meter.meter_readings.latest('end_time').end_time.astimezone(tz=self.tz)

            # Iterate through months
            current_month_time = min_time
            while current_month_time < max_time:
                _weekday, days_in_month = monthrange(current_month_time.year, current_month_time.month)

                unaware_end = datetime(current_month_time.year, current_month_time.month, days_in_month, 23, 59, 59)
                end_of_month = make_aware(unaware_end, timezone=self.tz)

                # Find all meters fully contained within this month (second-level granularity)
                interval_readings = meter.meter_readings.filter(start_time__range=(current_month_time, end_of_month), end_time__range=(current_month_time, end_of_month))
                if interval_readings.exists():
                    readings_list = list(interval_readings.order_by('-end_time'))
                    last_index = len(readings_list) - 1
                    reading_month_total = self._max_reading_total(readings_list, 0, last_index)

                    if reading_month_total > 0:
                        month_year = '{} {}'.format(month_name[current_month_time.month], current_month_time.year)
                        monthly_readings[month_year]['month'] = month_year
                        monthly_readings[month_year][type] = reading_month_total / conversion_factor

                current_month_time = end_of_month + timedelta(seconds=1)

        return {
            'readings': list(monthly_readings.values()),
            'column_defs': list(column_defs.values())
        }

    def _usages_by_year(self):
        """
        Similarly to _usages_by_month, this returns readings and column definitions
        formatted and aggregated to display all records in yearly intervals.
        """
        # Used to consolidate different readings (types) within the same year
        yearly_readings = defaultdict(lambda: {})

        # Construct column_defs using this dictionary's values for frontend to use
        column_defs = {
            '_year': {
                'field': 'year',
                '_filter_type': 'datetime',
            },
        }

        for meter in self.meters:
            type, conversion_factor = self._build_column_def(meter, column_defs)

            min_time = meter.meter_readings.earliest('start_time').start_time.astimezone(tz=self.tz)
            max_time = meter.meter_readings.latest('end_time').end_time.astimezone(tz=self.tz)

            # Iterate through years
            current_year_time = min_time
            while current_year_time < max_time:
                unaware_end = datetime(current_year_time.year, 12, 31, 23, 59, 59)
                end_of_year = make_aware(unaware_end, timezone=self.tz)

                # Find all meters fully contained within this month (second-level granularity)
                interval_readings = meter.meter_readings.filter(start_time__range=(current_year_time, end_of_year), end_time__range=(current_year_time, end_of_year))
                if interval_readings.exists():
                    readings_list = list(interval_readings.order_by('-end_time'))
                    last_index = len(readings_list) - 1
                    reading_year_total = self._max_reading_total(readings_list, 0, last_index)

                    if reading_year_total > 0:
                        year = current_year_time.year
                        yearly_readings[year]['year'] = year
                        yearly_readings[year][type] = reading_year_total / conversion_factor

                current_year_time = end_of_year + timedelta(seconds=1)

        return {
            'readings': list(yearly_readings.values()),
            'column_defs': list(column_defs.values())
        }

    def _build_column_def(self, meter, column_defs):
        type = dict(meter.ENERGY_TYPES)[meter.type]
        display_unit = self.org_meter_display_settings[type]
        conversion_factor = self.factors[type][display_unit]

        column_defs[type] = {
            'field': type,
            'displayName': '{} ({})'.format(type, display_unit),
            '_filter_type': 'reading',
        }

        return type, conversion_factor

    def _max_reading_total(self, sorted_readings, current_index, last_index):
        """
        Recursive method to find maximum possible total of readings that do not
        overlap each other within a given interval.

        This is an implementation of the algorithm used to solve the
        Weighted Job Scheduling problem.

        Note that the readings are expected to be sorted by descending end_times.
        """
        if current_index == last_index:  # Only one valid reading left to analyze
            return sorted_readings[current_index].reading.magnitude
        else:
            latest_completion = sorted_readings[current_index]

            # The max will always at least be the latest_completion reading
            max_including_reading = latest_completion.reading.magnitude

            # Find the index of the next non-conflicting reading
            latest_nonconflict_index = next(
                (
                    i
                    for i, record
                    in enumerate(sorted_readings)
                    if (record.end_time < latest_completion.start_time) and (i > current_index)
                ),
                -1
            )
            # If a non-conflicting reading is found, recurse with this new reading
            if latest_nonconflict_index > -1:
                max_including_reading += self._max_reading_total(sorted_readings, latest_nonconflict_index, last_index)

            # Since the list is sorted, excluding the current reading is done by skipping it's index.
            max_excluding_reading = self._max_reading_total(sorted_readings, current_index + 1, last_index)

            return max(max_including_reading, max_excluding_reading)

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

from seed.models import Meter
from seed.data_importer.utils import (
    kbtu_thermal_conversion_factors,
    usage_point_id,
)
from seed.lib.superperms.orgs.models import Organization
from seed.models import Property


class PropertyMeterReadingsExporter():
    """
    Returns readings and column definitions for UI-Grid. These readings can be
    returned in different intervals: exact, monthly, and yearly.

    Monthly and yearly aggregations are done here, and organization display
    settings are considered/used when returning actual reading magnitudes.
    """

    def __init__(self, property_id, org_id, excluded_meter_ids):
        self._cache_factors = None
        self._cache_org_country = None

        self.meters = Property.objects.get(pk=property_id).meters.exclude(pk__in=excluded_meter_ids)
        self.org_id = org_id
        self.org_meter_display_settings = Organization.objects.get(pk=org_id).display_meter_units
        self.tz = timezone(TIME_ZONE)

    @property
    def factors(self):
        if self._cache_factors is None:
            self._cache_factors = kbtu_thermal_conversion_factors(self._org_country)

        return self._cache_factors

    @property
    def _org_country(self):
        if self._cache_org_country is None:
            self._cache_org_country = Organization.objects.get(pk=self.org_id).get_thermal_conversion_assumption_display()

        return self._cache_org_country

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
            field_name, conversion_factor = self._build_column_def(meter, column_defs)

            for meter_reading in meter.meter_readings.all():
                start_time = meter_reading.start_time.astimezone(tz=self.tz).strftime(time_format)
                end_time = meter_reading.end_time.astimezone(tz=self.tz).strftime(time_format)

                times_key = "-".join([start_time, end_time])

                start_end_times[times_key]['start_time'] = start_time
                start_end_times[times_key]['end_time'] = end_time
                start_end_times[times_key][field_name] = meter_reading.reading / conversion_factor

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
            field_name, conversion_factor = self._build_column_def(meter, column_defs)

            min_time = meter.meter_readings.earliest('start_time').start_time.astimezone(tz=self.tz)
            max_time = meter.meter_readings.latest('end_time').end_time.astimezone(tz=self.tz)

            # Iterate through months
            current_month_time = min_time
            while current_month_time < max_time:
                _weekday, days_in_month = monthrange(current_month_time.year, current_month_time.month)

                unaware_end = datetime(current_month_time.year, current_month_time.month, days_in_month, 23, 59, 59) + timedelta(seconds=1)
                end_of_month = make_aware(unaware_end, timezone=self.tz)

                # Find all meters fully contained within this month (second-level granularity)
                interval_readings = meter.meter_readings.filter(start_time__range=(current_month_time, end_of_month), end_time__range=(current_month_time, end_of_month))
                if interval_readings.exists():
                    readings_list = list(interval_readings.order_by('end_time'))
                    reading_month_total = self._max_reading_total(readings_list)

                    if reading_month_total > 0:
                        month_year = '{} {}'.format(month_name[current_month_time.month], current_month_time.year)
                        monthly_readings[month_year]['month'] = month_year
                        monthly_readings[month_year][field_name] = reading_month_total / conversion_factor

                current_month_time = end_of_month

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
            field_name, conversion_factor = self._build_column_def(meter, column_defs)

            min_time = meter.meter_readings.earliest('start_time').start_time.astimezone(tz=self.tz)
            max_time = meter.meter_readings.latest('end_time').end_time.astimezone(tz=self.tz)

            # Iterate through years
            current_year_time = min_time
            while current_year_time < max_time:
                unaware_end = datetime((current_year_time.year + 1), 1, 1, 0, 0, 0)
                end_of_year = make_aware(unaware_end, timezone=self.tz)

                # Find all meters fully contained within this month (second-level granularity)
                interval_readings = meter.meter_readings.filter(start_time__range=(current_year_time, end_of_year), end_time__range=(current_year_time, end_of_year))
                if interval_readings.exists():
                    readings_list = list(interval_readings.order_by('end_time'))
                    reading_year_total = self._max_reading_total(readings_list)

                    if reading_year_total > 0:
                        year = current_year_time.year
                        yearly_readings[year]['year'] = year
                        yearly_readings[year][field_name] = reading_year_total / conversion_factor

                current_year_time = end_of_year

        return {
            'readings': list(yearly_readings.values()),
            'column_defs': list(column_defs.values())
        }

    def _build_column_def(self, meter, column_defs):
        type_text = meter.get_type_display()
        if meter.source == meter.GREENBUTTON:
            source = 'GB'
            source_id = usage_point_id(meter.source_id)
        elif meter.source == meter.BUILDINGSYNC:
            source = 'BS'
            source_id = meter.source_id
        else:
            source = 'PM'
            source_id = meter.source_id

        field_name = '{} - {} - {}'.format(type_text, source, source_id)

        if meter.type == Meter.COST:
            display_unit = "{} Dollars".format(self._org_country)
            conversion_factor = 1
        else:
            display_unit = self.org_meter_display_settings[type_text]
            conversion_factor = self.factors[type_text][display_unit]

        column_defs[field_name] = {
            'field': field_name,
            'displayName': '{} ({})'.format(field_name, display_unit),
            '_filter_type': 'reading',
        }

        return field_name, conversion_factor

    def _latest_nonintersecting_index(self, sorted_readings, start_index):
        """
        Using indexes, finds the latest reading before the current reading.
        Specifically, this latest reading must not end after the current reading
        starts. The index of the latest reading or -1, if none exists, is returned.

        Note that the readings are expected to be sorted by ascending end_times.

        This binary search is taken from
        https://www.geeksforgeeks.org/weighted-job-scheduling-log-n-time/
        """
        lo = 0
        hi = start_index - 1

        while lo <= hi:
            mid = (lo + hi) // 2
            current_start_time = sorted_readings[start_index].start_time

            if sorted_readings[mid].end_time <= current_start_time:
                if sorted_readings[mid + 1].end_time <= current_start_time:
                    lo = mid + 1
                else:
                    return mid
            else:
                hi = mid - 1
        return -1

    def _max_reading_total(self, sorted_readings):
        """
        Method to find maximum possible total of readings that do not
        overlap each other within a given interval.

        This is an implementation of the algorithm used to solve the
        Weighted Job Scheduling problem and is taken from
        https://www.geeksforgeeks.org/weighted-job-scheduling-log-n-time/

        At a high level, a running maximum is tracked to ultimately find the max.

        Note that the readings are expected to be sorted by ascending end_times.
        """
        # Create list to track running maximum and prefill first entry
        n = len(sorted_readings)
        running_max = [0 for _ in range(n)]
        running_max[0] = sorted_readings[0].reading

        # Fill the remaining entries in running_max
        for i in range(1, n):
            curr_max = sorted_readings[i].reading

            latest_index = self._latest_nonintersecting_index(sorted_readings, i)

            # If a latest index was found, add it's running_max value to curr_max
            if (latest_index != -1):
                curr_max += running_max[latest_index]

            # Store maximum of curr_max and the prior running_max entry
            running_max[i] = max(curr_max, running_max[i - 1])

        return running_max[n - 1]

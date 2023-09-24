"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import datetime
from calendar import monthrange
from collections import defaultdict, namedtuple
from statistics import mean, pstdev

from dateutil import relativedelta


def get_json_path(json_path, data):
    """very naive JSON path implementation. WARNING: it only handles key names that are dot separated
    e.g., 'key1.key2.key3'

    :param json_path: str
    :param data: dict
    :return: value, None if path not valid for dict
    """
    json_path = json_path.split('.')
    result = data
    for key in json_path:
        result = result.get(key, {})

    if isinstance(result, dict) and not result:
        # path was probably not valid in the data...
        return None
    else:
        return result


# simplified representation of a reading
SimpleMeterReading = namedtuple('SimpleMeterReading', ['start_time', 'end_time', 'reading'])


def _split_reading(meter_reading, snap_intervals=True):
    """Splits the meter reading into multiple readings. Readings are split at the
    start of each calendar month. This method is used to calendarize meter readings.

    If snap_intervals is enabled, all readings returned will begin and end on the
    first of the month (e.g., January 01 to February 01)
    If snap_intervals is not enabled, the original start and end are preserved in
    the first and last readings (respectively)

    Because we have to estimate the reading value (i.e., energy usage) when a reading
    doesn't cleanly fit in a calendar month (e.g., when it straddles or spans months),
    the result will not always be perfectly accurate to how much energy was really
    used in a calendar month.

    Examples - the pipe character, |, represents the start of a month, the brackets, [ ],
    represent the start and end of the meter readings.

    (1) Reading fits in a single month
    input:                   [##]
    months:            |    |    |    |
    result (snapped):       [###]
    result (no snap):        [##]

    (2) Reading straddles months
    input:               [#####]
    months:            |    |    |    |
    result (snapped):  [###][###]
    result (no snap):    [#][##]

    (3) Reading straddles and spans months
    input:               [##########]
    months:            |    |    |    |
    result (snapped):  [###][###][###]
    result (no snap):    [#][###][##]

    :param meter_reading: MeterReading | SimpleMeterReading
    :param snap_intervals: bool
    :return: List[SimpleMeterReading], in sorted order by start_date
    """
    reading_unaware_start_time = datetime.datetime(
        meter_reading.start_time.year,
        meter_reading.start_time.month,
        meter_reading.start_time.day,
        meter_reading.start_time.hour,
        meter_reading.start_time.minute,
        meter_reading.start_time.second,
    )
    reading_unaware_end_time = datetime.datetime(
        meter_reading.end_time.year,
        meter_reading.end_time.month,
        meter_reading.end_time.day,
        meter_reading.end_time.hour,
        meter_reading.end_time.minute,
        meter_reading.end_time.second,
    )

    reading_first_month = datetime.datetime(meter_reading.start_time.year, meter_reading.start_time.month, 1)
    reading_last_month = datetime.datetime(meter_reading.end_time.year, meter_reading.end_time.month, 1)
    last_month_affected = reading_last_month + relativedelta.relativedelta(months=1)

    # collect all consecutive months this reading "touches"
    current_month = reading_first_month
    months_affected = []
    while current_month < last_month_affected:
        next_month = current_month + relativedelta.relativedelta(months=1)
        months_affected.append((current_month, next_month))
        current_month = next_month

    # For each month this reading affects create a new "reading" for that month
    split_readings = []
    meter_reading_delta = reading_unaware_end_time - reading_unaware_start_time
    for idx, (month_start, month_end) in enumerate(months_affected):
        # estimate the reading value for this month by calculating
        # the fraction of the original reading this month covers and multiplying
        # the "total" (i.e., original) reading by that fraction
        overlap_start = max(month_start, reading_unaware_start_time)
        overlap_end = min(month_end, reading_unaware_end_time)
        # overlap_delta is essentially the union of time covered by this month and
        # the time covered by the original reading
        overlap_delta = overlap_end - overlap_start

        if overlap_delta.total_seconds() == 0:
            # there can be no overlap if we are given a reading which ends
            # on the first of a month and we're creating a reading for that month
            # it ends on.
            assert idx == len(months_affected) - 1, 'This should not occur, our assumptions were invalid. Please revisit this.'
            continue

        fraction_of_reading_time = overlap_delta.total_seconds() / meter_reading_delta.total_seconds()
        month_reading = fraction_of_reading_time * meter_reading.reading

        # determine the start/end time we should report for this reading
        reported_start_time, reported_end_time = month_start, month_end
        if not snap_intervals:
            if idx == 0:
                # this is the first month included, use the original start time
                reported_start_time = reading_unaware_start_time
            if idx == len(months_affected) - 1:
                # this is the last month included, use the original end time
                reported_end_time = reading_unaware_end_time

        split_readings.append(SimpleMeterReading(reported_start_time, reported_end_time, month_reading))

    return split_readings


def calendarize_meter_readings(meter_readings):
    """Aggregate readings into calendar months

    NOTE: It is OK to call this method with readings from multiple meters (we are
    just aggregating/dispersing meter data into monthly bins)

    :param: meter_readings, Iterable[SimpleMeterReading | MeterReading]
    :return: List[SimpleMeterReading]
    """
    all_meter_readings = sorted(meter_readings, key=lambda reading: reading.start_time)
    aggregated_readings_by_start_time = defaultdict(lambda: 0)
    for meter_reading in all_meter_readings:
        sr = _split_reading(meter_reading)
        for monthly_reading in sr:
            aggregated_readings_by_start_time[monthly_reading.start_time] += monthly_reading.reading

    aggregated_readings_list = []
    for start_time, reading in aggregated_readings_by_start_time.items():
        aggregated_readings_list.append(
            SimpleMeterReading(
                start_time,
                start_time + relativedelta.relativedelta(months=1),
                reading
            )
        )

    return aggregated_readings_list


SECONDS_IN_A_DAY = 86400


def calendarize_and_extrapolate_meter_readings(meter_readings, coverage_threshold=0.0):
    """For each calendar month included in the readings, calculate the average
    energy usage per unit time and use that average to calculate an estimated
    usage for that entire month.

    WARNING: This function should be called separately for each meter!
        Explanation: if you have two meters reporting usage over the month of January,
        this function will average these readings together for the month and the
        reported usage could be significantly lower than what it was in reality.
    WARNING: This function assumes meter_readings are not overlapping!

    :param meter_readings: Iterable[SimpleMeterReading | MeterReading]
    :param coverage_threshold: float, fraction of a month that must be covered
        by the readings to be included.
    :return: List[SimpleMeterReading]
    """
    split_meter_readings = []
    for meter_reading in meter_readings:
        # set snap_intervals to False so we can preserve the number of seconds
        # in each split up reading
        for split_reading in _split_reading(meter_reading, snap_intervals=False):
            split_meter_readings.append(split_reading)

    totals_by_month = defaultdict(lambda: {'total_usage': 0, 'total_seconds': 0})
    for meter_reading in split_meter_readings:
        start = meter_reading.start_time
        month_start = datetime.datetime(start.year, start.month, 1)
        totals_by_month[month_start]['total_usage'] += meter_reading.reading
        totals_by_month[month_start]['total_seconds'] += (
            meter_reading.end_time - meter_reading.start_time
        ).total_seconds()

    # calculate estimated total usage for each month
    estimated_monthly_readings = []
    for month_start, totals in totals_by_month.items():
        (_, days_in_month) = monthrange(month_start.year, month_start.month)
        seconds_in_month = days_in_month * SECONDS_IN_A_DAY

        # WARNING: this bit assumes we have non-overlapping readings! Otherwise
        # the fraction of month cannot be determined by "total seconds" of readings
        # in the month!
        fraction_of_month_covered = totals['total_seconds'] / seconds_in_month
        if fraction_of_month_covered < coverage_threshold:
            # we don't have enough data, skip this month
            continue

        average_usage_per_second = totals['total_usage'] / totals['total_seconds']

        estimated_monthly_reading = average_usage_per_second * seconds_in_month
        estimated_monthly_readings.append(
            SimpleMeterReading(
                month_start,
                month_start + relativedelta.relativedelta(months=1),
                estimated_monthly_reading
            )
        )

    estimated_monthly_readings.sort(key=lambda reading: reading.start_time)
    return estimated_monthly_readings


def reject_outliers(meter_readings, reject=1):
    """Rejects readings whose z-score is greater than the `reject` arg (i.e., standard
    deviations away from the mean).
    Useful if you aggregated meter readings and there are some 'artifacts' of
    partially covered periods.

    :param meter_readings: List[SimpleMeterReading]
    :param reject: int, z-score threshold
    """
    raw_values = [reading.reading for reading in meter_readings]
    avg = mean(raw_values)
    stdev = pstdev(raw_values)

    # weird case, but avoids divide by zero
    if stdev == 0:
        return meter_readings

    filtered_readings = []
    for reading in meter_readings:
        zscore = (reading.reading - avg) / stdev
        if abs(zscore) <= reject:
            filtered_readings.append(reading)
    return filtered_readings


def interpolate_monthly_readings(meter_readings):
    """Interpolate missing months from first to the last reading

    WARNING: This function makes some assumptions:
    - Assumes the meter readings are in sorted order (ascending start_time)
    - Assumes each reading represents a month of data from the first of a month
    to the first of the following month

    :param meter_readings: List[SimpleMeterReading]
    :return: List[SimpleMeterReading]
    """
    if len(meter_readings) == 0:
        return []

    interpolated_readings = []
    current_reading_index = 0
    current_time = meter_readings[current_reading_index].start_time
    while current_reading_index < len(meter_readings):
        current_reading = meter_readings[current_reading_index]
        assert current_reading.start_time.day == 1, f'Meter readings should start on the first day of the month; found one starting on {current_reading.start_time.day}'

        if current_time == current_reading.start_time:
            interpolated_readings.append(current_reading)
            current_reading_index += 1
        else:
            # interpolate reading
            prev_reading = interpolated_readings[-1]
            interpolated_readings.append(
                SimpleMeterReading(
                    current_time,
                    current_time + relativedelta.relativedelta(months=1),
                    prev_reading.reading
                )
            )
        current_time += relativedelta.relativedelta(months=1)

    return interpolated_readings


def get_days_in_reading(meter_reading):
    """Returns a list of datetime.datetime days that the reading covers/touches

    :param meter_reading: List[SimpleMeterReading | MeterReading]
    :return: List[datetime.datetime], days (at midnight, timezone unaware)
    """
    start = datetime.datetime(
        meter_reading.start_time.year,
        meter_reading.start_time.month,
        meter_reading.start_time.day,
    )
    end = datetime.datetime(
        meter_reading.end_time.year,
        meter_reading.end_time.month,
        meter_reading.end_time.day,
    )

    all_days = []
    current_day = start
    while current_day <= end:
        all_days.append(current_day)
        current_day += relativedelta.relativedelta(days=1)

    return all_days

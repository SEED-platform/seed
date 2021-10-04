from collections import defaultdict, namedtuple
import datetime
from statistics import mean, pstdev

from dateutil import relativedelta


def get_json_path(json_path, data):
    """very naive JSON path implementation. WARNING: it only handles key names that are dot separated
    e.g. 'key1.key2.key3'

    :param json_path: str
    :param data: dict
    :return: value, None if path not valid for dict
    """
    json_path = json_path.split('.')
    result = data
    for key in json_path:
        result = result.get(key, {})

    if type(result) is dict and not result:
        # path was probably not valid in the data...
        return None
    else:
        return result


# simplified representation of a reading
SimpleMeterReading = namedtuple('SimpleMeterReading', ['start_time', 'end_time', 'reading'])


def _split_reading(meter_reading):
    """Splits the meter reading into multiple readings, each representing a different
    calendar month (i.e. starting and ending at beginning of consecutive months).
    Another way to think of this method is that it "bins" an individual reading into
    calendar months.

    Because we have to estimate the reading value (ie energy usage) when a reading
    doesn't cleanly fit in a calendar month (e.g. when it straddles or spans months),
    the result will not always be perfectly accurate to how much energy was really
    used in a calendar month.

    Examples - the pipe character, |, represents the start of a month, the brackets, [ ],
    represent the start and end of the meter readings.

    (1) Reading fits in a single month
    reading:      [###]
    months:  |    |    |    |
    result:       [###]

    (2) Reading straddles months
    reading:   [#####]
    months:  |    |    |    |
    result:  [###][###]

    (3) Reading straddles and spans months
    reading:   [##########]
    months:  |    |    |    |
    result:  [###][###][###]

    :param meter_reading: MeterReading | SimpleMeterReading
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
    current_time = reading_first_month
    months_affected = []
    while current_time <= last_month_affected:
        months_affected.append(current_time)
        current_time += relativedelta.relativedelta(months=1)

    # For each month this reading affects create a new "reading" for that month
    split_readings = []
    meter_reading_delta = reading_unaware_end_time - reading_unaware_start_time
    for month_start, month_end in zip(months_affected, months_affected[1:]):
        # estimate the reading value for this month by calculating
        # the fraction of the original reading this month covers and multiplying
        # the "total" (ie original) reading by that fraction
        overlap_start = max(month_start, reading_unaware_start_time)
        overlap_end = min(month_end, reading_unaware_end_time)
        # overlap_delta is essentially the union of time covered by this month and
        # the time covered by the original reading
        overlap_delta = overlap_end - overlap_start
        fraction_of_reading_time = overlap_delta.total_seconds() / meter_reading_delta.total_seconds()
        month_reading = fraction_of_reading_time * meter_reading.reading
        split_readings.append(SimpleMeterReading(month_start, month_end, month_reading))

    return split_readings


def aggregate_meter_readings(meter_readings):
    """Aggregate readings into calendar months

    :param: meter_readings, QuerySet[MeterReading]
    :return: List[SimpleMeterReading]
    """
    all_meter_readings = meter_readings.order_by('start_time')
    aggregated_readings_by_start_time = defaultdict(lambda: 0)
    for meter_reading in all_meter_readings:
        for monthly_reading in _split_reading(meter_reading):
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


def reject_outliers(meter_readings, reject=1):
    """Rejects readings whose z-score is greater than the `reject` arg (i.e. standard
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

# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from datetime import datetime as dt

from django.test import TestCase

from seed.analysis_pipelines.utils import (
    SimpleMeterReading,
    _split_reading,
    calendarize_and_extrapolate_meter_readings,
    calendarize_meter_readings,
    interpolate_monthly_readings
)


class TestAnalysisUtils(TestCase):
    def test_split_reading_works_when_reading_is_within_one_month(self):
        # -- Setup
        # this reading starts and ends in January
        reading = SimpleMeterReading(
            dt(2021, 1, 1),
            dt(2021, 1, 15),
            100
        )

        # -- Act
        readings = _split_reading(reading)

        # -- Assert
        expected = [
            SimpleMeterReading(
                dt(2021, 1, 1),
                dt(2021, 2, 1),
                100
            )
        ]

        self.assertListEqual(expected, readings)

    def test_split_reading_works_when_reading_straddles_two_months(self):
        # -- Setup
        # this reading starts in January and ends in February
        # More specifically, this reading includes:
        # January:  17 days (~55%)
        # February: 15 days (~45%)
        # Total:    32 days (100%)
        reading = SimpleMeterReading(
            dt(2021, 1, 15),
            dt(2021, 2, 15),
            100
        )

        # -- Act
        readings = _split_reading(reading)

        # -- Assert
        expected = [
            SimpleMeterReading(
                dt(2021, 1, 1),
                dt(2021, 2, 1),
                54.83870967741935
            ),
            SimpleMeterReading(
                dt(2021, 2, 1),
                dt(2021, 3, 1),
                45.16129032258064
            )
        ]

        self.assertListEqual(expected, readings)

    def test_split_reading_works_when_reading_covers_multiple_months(self):
        # -- Setup
        # this reading starts in January, covers February, and ends in March
        # More specifically, this reading includes:
        # January:  17 days (~28%)
        # February: 28 days (~47%)
        # March:    15 days (~24%)
        # Total:    60 days (100%)
        reading = SimpleMeterReading(
            dt(2021, 1, 15),
            dt(2021, 3, 15),
            100
        )

        # -- Act
        readings = _split_reading(reading)

        # -- Assert
        expected = [
            SimpleMeterReading(
                dt(2021, 1, 1),
                dt(2021, 2, 1),
                28.8135593220339
            ),
            SimpleMeterReading(
                dt(2021, 2, 1),
                dt(2021, 3, 1),
                47.45762711864407
            ),
            SimpleMeterReading(
                dt(2021, 3, 1),
                dt(2021, 4, 1),
                23.728813559322035
            )
        ]

        self.assertListEqual(expected, readings)

    def test_split_reading_doesnt_return_extra_reading_when_reading_ends_on_month_start(self):
        # This test that the function treats end dates as non-inclusive
        # E.g. If a reading ends on February 1 at midnight, it will not return
        # an additional reading for the month of February-March
        # -- Setup
        reading = SimpleMeterReading(
            dt(2021, 1, 1),
            dt(2021, 2, 1),  # This is February 1 at midnight
            100
        )

        # -- Act
        readings = _split_reading(reading)

        # -- Assert
        self.assertListEqual([reading], readings)

    def test_split_reading_works_when_snap_is_disabled(self):
        # -- Setup
        # this reading starts in January, covers February, and ends in March
        # More specifically, this reading includes:
        # January:  17 days (~28%)
        # February: 28 days (~47%)
        # March:    15 days (~24%)
        # Total:    60 days (100%)
        original_start = dt(2021, 1, 15)
        original_end = dt(2021, 3, 15)
        reading = SimpleMeterReading(
            original_start,
            original_end,
            100
        )

        # -- Act
        # NOTE: we set snap to false, we expect the first and last readings to
        # keep their original start and end (respectively)
        readings = _split_reading(reading, snap_intervals=False)

        # -- Assert
        expected = [
            SimpleMeterReading(
                original_start,  # start_time should be the same!
                dt(2021, 2, 1),
                28.8135593220339
            ),
            SimpleMeterReading(
                dt(2021, 2, 1),
                dt(2021, 3, 1),
                47.45762711864407
            ),
            SimpleMeterReading(
                dt(2021, 3, 1),
                original_end,  # end_time should be the same!
                23.728813559322035
            )
        ]

        self.assertListEqual(expected, readings)

    def test_calendarize_meter_readings_works_when_readings_already_calendarized(self):
        # -- Setup
        jan, feb, mar, apr = dt(2021, 1, 1), dt(2021, 2, 1), dt(2021, 3, 1), dt(2021, 4, 1)
        original_readings = [
            SimpleMeterReading(jan, feb, 1),
            SimpleMeterReading(feb, mar, 2),
            SimpleMeterReading(mar, apr, 3),
        ]

        # -- Act
        result = calendarize_meter_readings(original_readings)

        # -- Assert
        # result should be the same as original readings
        self.assertListEqual(original_readings, result)

    def test_calendarize_meter_readings_works_when_readings_arent_sorted(self):
        # -- Setup
        jan, feb, mar, apr = dt(2021, 1, 1), dt(2021, 2, 1), dt(2021, 3, 1), dt(2021, 4, 1)
        original_readings = [
            SimpleMeterReading(mar, apr, 3),
            SimpleMeterReading(jan, feb, 1),
            SimpleMeterReading(feb, mar, 2),
        ]

        # -- Act
        result = calendarize_meter_readings(original_readings)

        # -- Assert
        expected = [
            SimpleMeterReading(jan, feb, 1),
            SimpleMeterReading(feb, mar, 2),
            SimpleMeterReading(mar, apr, 3),
        ]
        self.assertListEqual(expected, result)

    def test_calendarize_meter_readings_works_when_readings_overlap(self):
        # -- Setup
        jan, feb, mar, apr = dt(2021, 1, 1), dt(2021, 2, 1), dt(2021, 3, 1), dt(2021, 4, 1)
        original_readings = [
            SimpleMeterReading(jan, feb, 1),
            SimpleMeterReading(feb, mar, 2),
            SimpleMeterReading(mar, apr, 3),
            # overlapping months
            SimpleMeterReading(jan, feb, 1),
            SimpleMeterReading(feb, mar, 2),
            SimpleMeterReading(mar, apr, 3),
        ]

        # -- Act
        result = calendarize_meter_readings(original_readings)

        # -- Assert
        expected = [
            SimpleMeterReading(jan, feb, 2),
            SimpleMeterReading(feb, mar, 4),
            SimpleMeterReading(mar, apr, 6),
        ]
        self.assertListEqual(expected, result)

    def test_calendarize_and_extrapolate_meter_readings_correctly_extrapolates(self):
        # -- Setup
        # There are 28 days in February, so 14 days is 50% of the month
        original_readings = [
            SimpleMeterReading(
                dt(2021, 2, 1),
                dt(2021, 2, 15),
                1
            ),
        ]

        # -- Act
        result = calendarize_and_extrapolate_meter_readings(original_readings)

        # -- Assert
        expected = [
            SimpleMeterReading(
                dt(2021, 2, 1),
                dt(2021, 3, 1),
                2,  # since the original reading covered 1/2 of month, we'd expect the month total to be doubled
            )
        ]
        self.assertListEqual(expected, result)

    def test_calendarize_and_extrapolate_meter_readings_works_when_readings_are_consecutive(self):
        # -- Setup
        # These readings cover the full month of February
        original_readings = [
            SimpleMeterReading(
                dt(2021, 2, 1),
                dt(2021, 2, 15),
                1
            ),
            SimpleMeterReading(
                dt(2021, 2, 15),
                dt(2021, 3, 1),
                1
            ),
        ]

        # -- Act
        result = calendarize_and_extrapolate_meter_readings(original_readings)

        # -- Assert
        expected = [
            SimpleMeterReading(
                dt(2021, 2, 1),
                dt(2021, 3, 1),
                2,
            )
        ]
        self.assertListEqual(expected, result)

    def test_calendarize_and_extrapolate_meter_readings_filters_months_below_coverage_threshold(self):
        # -- Setup
        original_readings = [
            # January readings only cover the 1st through the 6th
            # This is ~19% of the month (6 / 31)
            SimpleMeterReading(
                dt(2021, 1, 1),
                dt(2021, 1, 3),
                1
            ),
            SimpleMeterReading(
                dt(2021, 1, 3),
                dt(2021, 1, 5),
                1
            ),
            SimpleMeterReading(
                dt(2021, 1, 5),
                dt(2021, 1, 7),
                1
            ),
            # February Readings cover the 1st through the 14th
            # This is 50% of the month (14 / 28)
            # Note that the _number_ of readings shouldn't matter -- it's about
            # monthly _coverage_
            SimpleMeterReading(
                dt(2021, 2, 1),
                dt(2021, 2, 3),
                1
            ),
            SimpleMeterReading(
                dt(2021, 2, 3),
                dt(2021, 2, 8),
                1
            ),
            SimpleMeterReading(
                dt(2021, 2, 8),
                dt(2021, 2, 12),
                1
            ),
            SimpleMeterReading(
                dt(2021, 2, 12),
                dt(2021, 2, 15),
                1
            ),
        ]

        # -- Act
        coverage_threshold = 0.5
        result = calendarize_and_extrapolate_meter_readings(original_readings, coverage_threshold)

        # -- Assert
        expected = [
            # Note that January isn't included here b/c the coverage for that month
            # is below our given threshold
            SimpleMeterReading(
                dt(2021, 2, 1),
                dt(2021, 3, 1),
                8,  # original total for Feb was 4; since original coverage was 50%, double that is 8
            )
        ]
        self.assertListEqual(expected, result)

    def test_interpolate_works_when_one_month_missing(self):
        # -- Setup
        readings = [
            SimpleMeterReading(
                dt(2021, 1, 1),
                dt(2021, 2, 1),
                1
            ),
            # NOTE: missing February!
            SimpleMeterReading(
                dt(2021, 3, 1),
                dt(2021, 4, 1),
                2
            )
        ]

        # -- Act
        results = interpolate_monthly_readings(readings)

        # -- Assert
        expected = [
            SimpleMeterReading(
                dt(2021, 1, 1),
                dt(2021, 2, 1),
                1
            ),
            SimpleMeterReading(
                dt(2021, 2, 1),
                dt(2021, 3, 1),
                1
            ),
            SimpleMeterReading(
                dt(2021, 3, 1),
                dt(2021, 4, 1),
                2
            )
        ]

        self.assertListEqual(expected, results)

    def test_interpolate_works_when_multiple_months_missing(self):
        # -- Setup
        readings = [
            SimpleMeterReading(
                dt(2021, 1, 1),
                dt(2021, 2, 1),
                1
            ),
            # NOTE: missing February!
            SimpleMeterReading(
                dt(2021, 3, 1),
                dt(2021, 4, 1),
                2
            ),
            SimpleMeterReading(
                dt(2021, 4, 1),
                dt(2021, 5, 1),
                3
            ),
            # NOTE: missing May!
            # NOTE: missing June!
            SimpleMeterReading(
                dt(2021, 7, 1),
                dt(2021, 8, 1),
                4
            )
        ]

        # -- Act
        results = interpolate_monthly_readings(readings)

        # -- Assert
        expected = [
            SimpleMeterReading(
                dt(2021, 1, 1),
                dt(2021, 2, 1),
                1
            ),
            SimpleMeterReading(
                dt(2021, 2, 1),
                dt(2021, 3, 1),
                1
            ),
            SimpleMeterReading(
                dt(2021, 3, 1),
                dt(2021, 4, 1),
                2
            ),
            SimpleMeterReading(
                dt(2021, 4, 1),
                dt(2021, 5, 1),
                3
            ),
            SimpleMeterReading(
                dt(2021, 5, 1),
                dt(2021, 6, 1),
                3
            ),
            SimpleMeterReading(
                dt(2021, 6, 1),
                dt(2021, 7, 1),
                3
            ),
            SimpleMeterReading(
                dt(2021, 7, 1),
                dt(2021, 8, 1),
                4
            )
        ]

        self.assertListEqual(expected, results)

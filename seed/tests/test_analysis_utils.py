# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from datetime import datetime as dt

from django.test import TestCase

from seed.analysis_pipelines.utils import (
    SimpleMeterReading,
    _split_reading,
    interpolate_monthly_readings,
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

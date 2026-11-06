"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.test import TestCase

from seed.data_importer import tasks
from seed.landing.models import SEEDUser as User
from seed.models import Column, ColumnMapping, Unit
from seed.utils.organizations import create_organization

logger = logging.getLogger(__name__)


class TestCleaner(TestCase):
    """Tests that our logic for constructing cleaners works."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            email="test_user@demo.com",
            username="test_user@demo.com",
            password="secret",
        )
        self.org, _, _ = create_organization(self.user, "test-organization-a")

        # Float
        float_unit = Unit.objects.create(
            unit_name="mapped_col unit",
            unit_type=Unit.FLOAT,
        )
        float_raw = Column.objects.create(
            column_name="float_raw_col",
            organization=self.org,
        )
        self.float_col = "float_mapped_col"
        float_mapped = Column.objects.create(
            table_name="PropertyState",
            column_name=self.float_col,
            unit=float_unit,
            organization=self.org,
            is_extra_data=True,
        )
        mapping = ColumnMapping.objects.create(super_organization=self.org)
        mapping.column_raw.add(float_raw)
        mapping.column_mapped.add(float_mapped)

        # Integer
        str_unit = Unit.objects.create(
            unit_name="mapped_col unit",
            unit_type=Unit.STRING,
        )
        str_raw = Column.objects.create(
            column_name="string_raw_col",
            organization=self.org,
        )
        self.string_col = "string_mapped_col"
        str_mapped = Column.objects.create(
            table_name="PropertyState",
            column_name=self.string_col,
            unit=str_unit,
            organization=self.org,
            is_extra_data=True,
        )
        mapping = ColumnMapping.objects.create(super_organization=self.org)
        mapping.column_raw.add(str_raw)
        mapping.column_mapped.add(str_mapped)

    def test_clean_value(self):
        cleaner = tasks._build_cleaner(self.org)

        # data is cleaned correctly for fields on PropertyState
        # model
        bs_field = "gross_floor_area"
        self.assertEqual(cleaner.clean_value("1,456", bs_field), 1456)

        # data are cleaned correctly for mapped fields that have float unit
        self.assertEqual(cleaner.clean_value("2,456", self.float_col), 2456)

        # String test
        self.assertEqual(cleaner.clean_value("123,456 Nothingness", self.string_col), "123,456 Nothingness")

        self.assertEqual(cleaner.clean_value("3,456", self.float_col), 3456)

        # other fields are just strings
        self.assertEqual(cleaner.clean_value("123,456", "random"), "123,456")

    def test_clean_value_whitespace_only_is_none(self):
        """Blank and whitespace-only values are cleaned to None for every column type, including extra data (#5076)"""
        cleaner = tasks._build_cleaner(self.org)

        # One column for each branch of clean_value
        self.assertIn(self.string_col, cleaner.string_columns)
        self.assertIn(self.float_col, cleaner.float_columns)
        self.assertIn("address_line_1", cleaner.string_columns)
        self.assertIn("year_built", cleaner.int_columns)
        self.assertIn("year_ending", cleaner.date_columns)
        self.assertIn("recent_sale_date", cleaner.date_time_columns)
        self.assertIn("property_footprint", cleaner.geometry_columns)
        self.assertIn("gross_floor_area", cleaner.float_columns)
        columns = [
            (self.string_col, True),
            (self.float_col, True),
            ("random", True),  # an extra data column without a type
            ("address_line_1", False),
            ("year_built", False),
            ("year_ending", False),
            ("recent_sale_date", False),
            ("property_footprint", False),
            ("gross_floor_area", False),
        ]
        for column_name, is_extra_data in columns:
            for value in ("", " ", "   ", "\t", "\n", " \r\n "):
                with self.subTest(column_name=column_name, value=value):
                    self.assertIsNone(cleaner.clean_value(value, column_name, is_extra_data))

        # Values with text are not stripped
        self.assertEqual(cleaner.clean_value(" a ", self.string_col), " a ")
        self.assertEqual(cleaner.clean_value(" a ", "random"), " a ")

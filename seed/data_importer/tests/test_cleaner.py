# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from django.test import TestCase

from seed.data_importer import tasks
from seed.landing.models import SEEDUser as User
from seed.models import (
    Column,
    ColumnMapping,
    Unit,
)
from seed.utils.organizations import create_organization

logger = logging.getLogger(__name__)


class TestCleaner(TestCase):
    """Tests that our logic for constructing cleaners works."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            email='test_user@demo.com',
            username='test_user@demo.com',
            password='secret',
        )
        self.org, _, _ = create_organization(self.user, "test-organization-a")

        # Float
        float_unit = Unit.objects.create(
            unit_name='mapped_col unit',
            unit_type=Unit.FLOAT,
        )
        float_raw = Column.objects.create(
            column_name='float_raw_col',
            organization=self.org,
        )
        self.float_col = 'float_mapped_col'
        float_mapped = Column.objects.create(
            table_name='PropertyState',
            column_name=self.float_col,
            unit=float_unit,
            organization=self.org,
            is_extra_data=True,
        )
        mapping = ColumnMapping.objects.create(
            super_organization=self.org
        )
        mapping.column_raw.add(float_raw)
        mapping.column_mapped.add(float_mapped)

        # Integer
        str_unit = Unit.objects.create(
            unit_name='mapped_col unit',
            unit_type=Unit.STRING,
        )
        str_raw = Column.objects.create(
            column_name='string_raw_col',
            organization=self.org,
        )
        self.string_col = 'string_mapped_col'
        str_mapped = Column.objects.create(
            table_name='PropertyState',
            column_name=self.string_col,
            unit=str_unit,
            organization=self.org,
            is_extra_data=True,
        )
        mapping = ColumnMapping.objects.create(
            super_organization=self.org
        )
        mapping.column_raw.add(str_raw)
        mapping.column_mapped.add(str_mapped)

    def test_clean_value(self):
        cleaner = tasks._build_cleaner(self.org)

        # data is cleaned correctly for fields on PropertyState
        # model
        bs_field = 'gross_floor_area'
        self.assertEqual(
            cleaner.clean_value('1,456', bs_field),
            1456
        )

        # data are cleaned correctly for mapped fields that have float unit
        self.assertEqual(
            cleaner.clean_value('2,456', self.float_col),
            2456
        )

        # String test
        self.assertEqual(
            cleaner.clean_value('123,456 Nothingness', self.string_col),
            '123,456 Nothingness'
        )

        self.assertEqual(
            cleaner.clean_value('3,456', self.float_col),
            3456
        )

        # other fields are just strings
        self.assertEqual(
            cleaner.clean_value('123,456', 'random'),
            '123,456'
        )

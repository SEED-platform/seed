# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from django.test import TestCase

from seed.data_importer import tasks
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    FLOAT,
    Column,
    ColumnMapping,
    Unit,
)

logger = logging.getLogger(__name__)


class TestCleaner(TestCase):
    """Tests that our logic for constructing cleaners works."""

    def setUp(self):
        self.org = Organization.objects.create()

        unit = Unit.objects.create(
            unit_name='mapped_col unit',
            unit_type=FLOAT,
        )

        raw = Column.objects.create(
            column_name='raw_col',
            organization=self.org,
        )

        self.mapped_col = 'mapped_col'
        mapped = Column.objects.create(
            column_name=self.mapped_col,
            unit=unit,
            organization=self.org,
        )

        mapping = ColumnMapping.objects.create(
            super_organization=self.org
        )
        mapping.column_raw.add(raw)
        mapping.column_mapped.add(mapped)

    def test_clean_value(self):
        cleaner = tasks._build_cleaner(self.org)

        # data is cleaned correctly for fields on PropertyState
        # model
        bs_field = 'gross_floor_area'
        self.assertEqual(
            cleaner.clean_value('123,456', bs_field),
            123456
        )

        # data is cleaned correctly for mapped fields that have unit
        # type information
        self.assertEqual(
            cleaner.clean_value('123,456', self.mapped_col),
            123456
        )

        # other fields are just strings
        self.assertEqual(
            cleaner.clean_value('123,456', 'random'),
            '123,456'
        )

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import datetime
from decimal import Decimal
from unittest import TestCase

from django.utils import timezone

from seed.lib.mcm import cleaners


class TestCleaners(TestCase):

    def setUp(self):
        self.cleaner = cleaners.Cleaner({
            'flat_schema': {
                u'heading1': u'',
                u'heading2': u'',
                u'heading_data1': u'Some unit',
            },
            'types': {
                'heading_data1': 'float',
                'heading2': 'date',
                'heading3': 'datetime',
                'str_1': 'string',
                'int_1': 'integer',
            }
        })

    def test_default_cleaner(self):
        """Make sure we cleanup 'Not Applicables', etc from row data."""
        for item in [u'N/A', u'Not Available', u'not available']:
            self.assertEqual(
                cleaners.default_cleaner(item),
                None
            )

    def test_float_cleaner(self):
        """Test float cleaner."""
        self.assertEqual(cleaners.float_cleaner(u'0.8'), 0.8)
        self.assertEqual(cleaners.float_cleaner(u'wut'), None)
        self.assertEqual(cleaners.float_cleaner(u''), None)
        self.assertEqual(cleaners.float_cleaner(None), None)
        self.assertEqual(cleaners.float_cleaner(u'12,090'), 12090)
        self.assertEqual(cleaners.float_cleaner(u'12,090 ?'), 12090)
        self.assertEqual(cleaners.float_cleaner(0.825), 0.825)
        self.assertEqual(cleaners.float_cleaner(100), 100.0)
        self.assertEqual(cleaners.float_cleaner(0), 0.0)
        self.assertEqual(cleaners.float_cleaner(0.0), 0.0)
        self.assertEqual(cleaners.float_cleaner('0'), 0.0)
        self.assertEqual(cleaners.float_cleaner('-55.0'), -55.0)
        self.assertEqual(cleaners.float_cleaner('-55'), -55.0)
        self.assertEqual(cleaners.float_cleaner(u'-55.0'), -55.0)
        self.assertEqual(cleaners.float_cleaner(Decimal('20.00')), 20.0)
        self.assertTrue(isinstance(cleaners.float_cleaner(100), float))
        self.assertIsInstance(cleaners.float_cleaner(Decimal('20.00')), float)
        with self.assertRaises(TypeError) as error:
            cleaners.float_cleaner(datetime.datetime.now())
        message = error.exception.message
        self.assertEqual(
            message,
            "float_cleaner cannot convert <type 'datetime.datetime'> to float"
        )

    def test_date_cleaner(self):
        """We return the value if it's convertible to a python datetime."""
        self.assertEqual(
            cleaners.date_cleaner(u'2/12/2012'),
            datetime.datetime(2012, 2, 12, 0, 0, tzinfo=timezone.get_current_timezone())
        )
        self.assertEqual(cleaners.date_cleaner(u''), None)
        self.assertEqual(cleaners.date_cleaner(u'some string'), None)
        self.assertEqual(cleaners.date_cleaner(u'00'), None)
        now = datetime.datetime.now()
        self.assertEqual(cleaners.date_cleaner(now), now)

    def test_int_cleaner(self):
        self.assertEqual(cleaners.int_cleaner(u'1'), 1)
        self.assertEqual(cleaners.int_cleaner(u'wut'), None)
        self.assertEqual(cleaners.int_cleaner(u''), None)
        self.assertEqual(cleaners.int_cleaner(None), None)
        self.assertEqual(cleaners.int_cleaner(u'12,090'), 12090)
        self.assertEqual(cleaners.int_cleaner(u'12,090 ?'), 12090)
        self.assertEqual(cleaners.int_cleaner(0.825), 0)
        self.assertEqual(cleaners.int_cleaner(0), 0)
        self.assertEqual(cleaners.int_cleaner('-55'), -55)
        self.assertEqual(cleaners.int_cleaner('55.0'), 55)
        self.assertEqual(cleaners.int_cleaner('1.1'), 1)

    def test_clean_value(self):
        """Test that the ``Cleaner`` object properly routes cleaning."""
        expected = None
        self.assertEqual(
            self.cleaner.clean_value(u'Not Available', u'str_1'),
            expected
        )
        expected = u'Whatever'
        self.assertEqual(
            self.cleaner.clean_value(u'Whatever', u'heading1'),
            expected
        )
        float_expected = 0.7
        self.assertEqual(
            self.cleaner.clean_value(u'0.7', u'heading_data1'),
            float_expected
        )



        self.assertListEqual(sorted(self.cleaner.date_columns), ['heading2', 'heading3'])
        self.assertEqual(self.cleaner.float_columns, ['heading_data1'])
        self.assertEqual(self.cleaner.string_columns, ['str_1'])
        self.assertEqual(self.cleaner.int_columns, ['int_1'])

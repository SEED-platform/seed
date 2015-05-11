"""
:copyright: (c) 2014 Building Energy Inc
"""
import datetime
from unittest import TestCase

from mcm import cleaners


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
                'heading2': 'date'
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
        self.assertTrue(isinstance(cleaners.float_cleaner(100), float))

    def test_date_cleaner(self):
        """We return the value if it's convertable to a python datetime."""
        self.assertEqual(cleaners.date_cleaner(u'2/12/2012'), u'2/12/2012')
        self.assertEqual(cleaners.date_cleaner(u''), None)
        self.assertEqual(cleaners.date_cleaner(u'some string'), None)
        self.assertEqual(cleaners.date_cleaner(u'00'), None)
        now = datetime.datetime.now()
        self.assertEqual(cleaners.date_cleaner(now), now)

    def test_clean_value(self):
        """Test that the ``Cleaner`` object properly routes cleaning."""
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

        self.assertEqual(self.cleaner.date_columns, ['heading2'])
        self.assertEqual(self.cleaner.float_columns, ['heading_data1'])

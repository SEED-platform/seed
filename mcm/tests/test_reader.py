"""
:copyright: (c) 2014 Building Energy Inc
"""
from unittest import TestCase

import unicodecsv

from mcm import reader
from mcm.tests import utils


class TestCSVParser(TestCase):
    def setUp(self):
        self.csv_f = open('test_data/test_espm.csv', 'rb')
        self.parser = reader.CSVParser(self.csv_f)

    def tearDown(self):
        self.csv_f.close()

    def test_get_csv_reader(self):
        """Defaults to DictReader."""
        self.assertTrue(
            isinstance(self.parser.csvreader, unicodecsv.DictReader)
        )

    def test_clean_super(self):
        """Make sure we clean out unicode escaped super scripts."""
        expected = u'Testing 2. And 2.'
        test = u'Testing \xb2. And \ufffd.'
        self.assertEqual(
            self.parser._clean_super(test),
            expected
        )

        # Test that our replace keyword works
        new_expected = expected.replace('2', '3')
        self.assertEqual(
            self.parser._clean_super(test, replace=u'3'),
            new_expected
        )

    def test_clean_super_scripts(self):
        """Call _clean_super on all fieldnames."""
        escape = u'\xb2'
        # We know we have one of these escapes in our columns...

        # self.parser.clean_super_scripts() is run by __init__ now
        self.assertFalse(utils.list_has_substring(
            escape, self.parser.csvreader.unicode_fieldnames
        ))


class TestMCMParserCSV(TestCase):
    def setUp(self):
        self.csv_f = open('test_data/test_espm.csv', 'rb')
        self.parser = reader.MCMParser(self.csv_f)
        self.total_callbacks = 0

    def my_callback(self, rows):
        self.total_callbacks += 1

    def tearDown(self):
        self.csv_f.close()

    def test_split_rows(self):
        """Ensure splitting rows up works as expected."""
        num_rows = self.parser.split_rows(1, self.my_callback)
        # Since there are three lines of test_data, and
        # we specified a chunk size of 1, we should get 3 callbacks.
        self.assertEqual(self.total_callbacks, 3)
        self.assertEqual(num_rows, 3)

    def test_split_rows_w_extra(self):
        """ensure splitting rows works when there's remainder."""
        num_rows = self.parser.split_rows(2, self.my_callback)
        # There are three rows, the first two in the first batch,
        # the last one in its own.
        self.assertEqual(self.total_callbacks, 2)
        self.assertEqual(num_rows, 3)

    def test_split_rows_w_large_batch(self):
        self.parser.split_rows(5000, self.my_callback)
        # There's always at least one batch per file.
        self.assertEqual(self.total_callbacks, 1)

    def test_num_colums(self):
        self.assertEqual(self.parser.num_columns(), 250)


class TestMCMParserXLS(TestCase):
    def setUp(self):
        self.xls_f = open('test_data/test_espm.xls', 'rb')
        self.parser = reader.MCMParser(self.xls_f)
        self.total_callbacks = 0

    def my_callback(self, rows):
        self.total_callbacks += 1

    def tearDown(self):
        self.xls_f.close()

    def test_split_rows(self):
        """Ensure splitting rows up works as expected."""
        num_rows = self.parser.split_rows(1, self.my_callback)
        # Since there are three lines of test_data, and
        # we specified a chunk size of 1, we should get 3 callbacks.
        self.assertEqual(self.total_callbacks, 3)
        self.assertEqual(num_rows, 3)

    def test_split_rows_w_extra(self):
        """ensure splitting rows works when there's remainder."""
        num_rows = self.parser.split_rows(2, self.my_callback)
        # There are three rows, the first two in the first batch,
        # the last one in its own.
        self.assertEqual(self.total_callbacks, 2)
        self.assertEqual(num_rows, 3)

    def test_split_rows_w_large_batch(self):
        self.parser.split_rows(5000, self.my_callback)
        # There's always at least one batch per file.
        self.assertEqual(self.total_callbacks, 1)

    def test_num_colums(self):
        self.assertEqual(self.parser.num_columns(), 250)


class TestMCMParserXLSX(TestCase):
    def setUp(self):
        self.xlsx_f = open('test_data/test_espm.xlsx', 'rb')
        self.parser = reader.MCMParser(self.xlsx_f)
        self.total_callbacks = 0

    def my_callback(self, rows):
        self.total_callbacks += 1

    def tearDown(self):
        self.xlsx_f.close()

    def test_split_rows(self):
        """Ensure splitting rows up works as expected."""
        num_rows = self.parser.split_rows(1, self.my_callback)
        # Since there are three lines of test_data, and
        # we specified a chunk size of 1, we should get 3 callbacks.
        self.assertEqual(self.total_callbacks, 3)
        self.assertEqual(num_rows, 3)

    def test_split_rows_w_extra(self):
        """ensure splitting rows works when there's remainder."""
        num_rows = self.parser.split_rows(2, self.my_callback)
        # There are three rows, the first two in the first batch,
        # the last one in its own.
        self.assertEqual(self.total_callbacks, 2)
        self.assertEqual(num_rows, 3)

    def test_split_rows_w_large_batch(self):
        self.parser.split_rows(5000, self.my_callback)
        # There's always at least one batch per file.
        self.assertEqual(self.total_callbacks, 1)

    def test_num_colums(self):
        self.assertEqual(self.parser.num_columns(), 250)

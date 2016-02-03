# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from unittest import TestCase
import os

import unicodecsv
from seed.lib.mcm import reader
from seed.lib.mcm.tests import utils



class TestCSVParser(TestCase):
    def setUp(self):
        test_file = os.path.dirname(os.path.realpath(__file__)) + '/test_data/test_espm.csv'
        self.csv_f = open(test_file, 'rb')
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
        expected = u'Testing 2. And .'
        test = u'Testing \xb2. And \ufffd.'
        self.assertEqual(
            self.parser._clean_super(test),
            expected
        )

        # Test that our replace keyword works
        expected = u'Testing 3. And - -.'
        test = u'Testing \u00b3. And \u2013 \u2014.'
        self.assertEqual(
            self.parser._clean_super(test),
            expected
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
        test_file = os.path.dirname(os.path.realpath(__file__)) + '/test_data/test_espm.csv'
        self.csv_f = open(test_file, 'rb')
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

    def test_num_columns(self):
        self.assertEqual(self.parser.num_columns(), 250)

    def test_headers(self):
        """tests that we can get the original order of headers"""
        self.assertEqual(
            self.parser.headers()[0],
            'Property Id'
        )
        self.assertEqual(
            self.parser.headers()[-1],
            'Release Date'
        )


class TestMCMParserXLS(TestCase):
    def setUp(self):
        test_file = os.path.dirname(os.path.realpath(__file__)) + '/test_data/test_espm.xls'
        self.xls_f = open(test_file, 'rb')
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

    def test_num_columns(self):
        self.assertEqual(self.parser.num_columns(), 250)

    def test_headers(self):
        self.assertEqual(
            self.parser.headers()[0],
            'Property Id'
        )
        self.assertEqual(
            self.parser.headers()[-1],
            'Release Date'
        )

    def test_blank_row(self):
        self.xls_f.close()
        test_file = os.path.dirname(os.path.realpath(__file__)) + '/test_data/test_espm_blank_rows.xls'
        self.xls_f = open(test_file, 'rb')
        self.parser = reader.MCMParser(self.xls_f)
        self.total_callbacks = 0
        self.assertEqual(
            self.parser.headers()[0],
            'Property Id'
        )
        self.assertEqual(
            self.parser.headers()[-1],
            'Release Date'
        )


class TestMCMParserXLSX(TestCase):
    def setUp(self):
        test_file = os.path.dirname(os.path.realpath(__file__)) + '/test_data/test_espm.xlsx'
        self.xlsx_f = open(test_file, 'rb')
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

    def test_num_columns(self):
        self.assertEqual(self.parser.num_columns(), 250)

    def test_headers(self):
        self.assertEqual(
            self.parser.headers()[0],
            'Property Id'
        )
        self.assertEqual(
            self.parser.headers()[-1],
            'Release Date'
        )

    def test_odd_date_format(self):
        """
        Regression test to handle excel date format issues. More info at:
        https://secure.simplistix.co.uk/svn/xlrd/trunk/xlrd/doc/xlrd.html?p=4966
        under 'Dates in Excel spreadsheets'
        """
        self.xlsx_f.close()
        test_file = os.path.dirname(os.path.realpath(__file__)) + '/test_data/test_espm_date_format.xlsx'
        self.xlsx_f = open(test_file, 'rb')
        self.parser = reader.MCMParser(self.xlsx_f)
        list(self.parser.reader.excelreader)

    def test_get_all_rows(self):
        """Force evaluate all rows to make sure we don't get errors."""
        list(self.parser.reader.excelreader)

# !/usr/bin/env python
# encoding: utf-8

import os

from django.test import TestCase

from seed.lib.mcm.reader import MCMParser


class CSVParserTest(TestCase):
    def setUp(self):
        file_path = os.path.dirname(os.path.abspath(__file__)) + "/test_data/test_csv.csv"
        self.file = open(file_path, "r", encoding="utf-8")
        self.parser = MCMParser(self.file)

    def test_it_has_a_data_property(self):
        expectation = [
            {
                "column 1": "1",
                "column 2": "2",
                "column 3": "3",
                "column 4": "4",
                "column 5": "5",
                "column 6": "6",
            },
            {
                "column 1": "7",
                "column 2": "8",
                "column 3": "9",
                "column 4": "10",
                "column 5": "11",
                "column 6": "12",
            },
        ]

        # have to convert the CSV's DictReader into a list of regular dicts to compare
        data = [dict(row) for row in self.parser.data]
        self.assertEqual(data, expectation)

    def test_it_has_a_headers_property(self):
        expectation = [
            "column 1",
            "column 2",
            "column 3",
            "column 4",
            "column 5",
            "column 6",
        ]

        self.assertEqual(self.parser.headers, expectation)

    def test_it_has_a_num_columns_property(self):
        self.assertEqual(self.parser.num_columns(), 6)

    def test_it_has_a_first_five_rows_property(self):
        expectation = [
            "|#*#|".join([str(i) for i in range(1, 7)]),
            "|#*#|".join([str(i) for i in range(7, 13)]),
        ]

        self.assertEqual(self.parser.first_five_rows, expectation)


class CSVMissingHeadersParserTest(TestCase):
    def setUp(self):
        file_path = os.path.dirname(os.path.abspath(__file__)) + "/test_data/test_missing_headers.csv"
        self.file = open(file_path, "r", encoding="utf-8")
        self.parser = MCMParser(self.file)

    def test_it_has_a_data_property(self):
        expectation = [
            {
                "column 1": "1",
                "column 2": "2",
                "SEED Generated Header 1": "3",
                "column 4": "4",
                "SEED Generated Header 2": "5",
                "column 6": "6",
            },
            {
                "column 1": "7",
                "column 2": "8",
                "SEED Generated Header 1": "9",
                "column 4": "10",
                "SEED Generated Header 2": "11",
                "column 6": "12",
            },
        ]

        # have to convert the CSV's DictReader into a list of regular dicts to compare
        data = [dict(row) for row in self.parser.data]
        self.assertEqual(data, expectation)

    def test_it_has_a_headers_property(self):
        expectation = [
            "column 1",
            "column 2",
            "SEED Generated Header 1",
            "column 4",
            "SEED Generated Header 2",
            "column 6",
        ]

        self.assertEqual(self.parser.headers, expectation)

    def test_it_has_a_num_columns_property(self):
        self.assertEqual(self.parser.num_columns(), 6)

    def test_it_has_a_first_five_rows_property(self):
        expectation = [
            "|#*#|".join([str(i) for i in range(1, 7)]),
            "|#*#|".join([str(i) for i in range(7, 13)]),
        ]

        self.assertEqual(self.parser.first_five_rows, expectation)

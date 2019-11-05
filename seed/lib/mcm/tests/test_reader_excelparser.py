# !/usr/bin/env python
# encoding: utf-8

import os

from django.test import TestCase

from seed.lib.mcm.reader import ExcelParser


class ExcelParserTest(TestCase):
    def setUp(self):
        file_path = os.path.dirname(os.path.abspath(__file__)) + "/test_data/test_espm.xlsx"
        self.file = open(file_path, "r", encoding="utf-8")
        self.parser = ExcelParser(self.file, 'DC_ESPM.csv')

    def test_zip(self):
        for element in range(len(self.parser.sheet._cell_values[self.parser.header_row])):
            if self.parser.sheet._cell_values[self.parser.header_row][element] == 'Postal Code':
                for i in self.parser.sheet.col(element):
                    if not isinstance(i.value, str):
                        return 0
#                        print(str(i.value).zfill(10))

    def test_xls_dict_reader(self):
#        for all in self.parser.XLSDictReader(self.parser.sheet):
#            print("\n")
#            for i in all:
#                if i == 'Postal Code':
#                    print(i.strip())
        self.parser.XLSDictReader(self.parser.sheet)

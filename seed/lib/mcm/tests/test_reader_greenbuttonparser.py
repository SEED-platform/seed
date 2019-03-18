# !/usr/bin/env python
# encoding: utf-8

import os

from django.test import TestCase

from seed.lib.mcm.reader import GreenButtonParser


class GreenButtonParserTest(TestCase):
    def setUp(self):
        file_path = os.path.dirname(os.path.abspath(__file__)) + "/test_data/example-GreenButton-data.xml"
        file = open(file_path, "r", encoding="utf-8")
        self.parser = GreenButtonParser(file)

    def test_it_has_a_data_property(self): # TODO: test for different types and units once an answer is received
        expectation = [
            {
                'start_time': 1299387600,
                'source_id': '409483', # TODO:  verify out of /v1/User/6150855/UsagePoint/409483 , only 409483 is desired
                'duration': 900,
                'Electricity Use  (kWh)': 1.79,
            },
            {
                'start_time': 1299388500,
                'source_id': '409483', # TODO:  verify out of /v1/User/6150855/UsagePoint/409483 , only 409483 is desired
                'duration': 900,
                'Electricity Use  (kWh)': 1.791,
            }
        ]

        self.assertEqual(self.parser.data, expectation)

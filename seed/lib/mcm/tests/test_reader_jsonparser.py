# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import os

from django.test import TestCase

from seed.lib.mcm.reader import GeoJSONParser


class JSONParserTest(TestCase):
    def setUp(self):
        file_path = os.path.dirname(os.path.abspath(__file__)) + "/test_data/example_feature_collection_geojson.json"
        self.file = open(file_path, "r", encoding="utf-8")
        self.parser = GeoJSONParser(self.file)

    def tearDown(self) -> None:
        self.file.close()

    def test_it_has_a_data_property(self):
        expectation = [
            {
                "Address Line 1": "1 Fake Street",
                "property_footprint": (
                    "POLYGON ((-105.17262205481529 39.74200726814212, "
                    "-105.17227604985237 39.74207739085327, "
                    "-105.17228543758394 39.742112452182084, "
                    "-105.17263278365134 39.7420423295066, "
                    "-105.17262205481529 39.74200726814212))"
                ),
                "Building Type": "Office",
                "Created At": "2017-09-01T21:16:27.788Z",
                "Floor Area": 2634.7594734229788,
                "Type": "Building"
            },
            {
                "Address Line 1": "12 Fake Street",
                "property_footprint": (
                    "POLYGON ((-105.17615586519241 39.74217020021416, "
                    "-105.1763167977333 39.74228982098384, "
                    "-105.17616927623747 39.74240944154582, "
                    "-105.17601102590561 39.74228775855852, "
                    "-105.17615586519241 39.74217020021416))"
                ),
                "Building Type": "Office",
                "Created At": "2017-09-01T21:16:27.649Z",
                "Floor Area": 3745.419332770663,
                "Type": "Building"
            }
        ]

        self.assertEqual(self.parser.data, expectation)

    def test_it_has_a_headers_property(self):
        expectation = [
            "Address Line 1",
            "Building Type",
            "Created At",
            "Floor Area",
            "Type",
            "property_footprint"
        ]

        self.assertEqual(self.parser.headers, expectation)

    def test_it_has_a_num_columns_property(self):
        self.assertEqual(self.parser.num_columns(), 6)

    def test_it_has_a_first_five_rows_property(self):
        expectation = [
            "1 Fake Street|#*#|Office|#*#|2017-09-01T21:16:27.788Z|#*#|2634.7594734229788|#*#|Building|#*#|Property Footprint - Not Displayed",
            "12 Fake Street|#*#|Office|#*#|2017-09-01T21:16:27.649Z|#*#|3745.419332770663|#*#|Building|#*#|Property Footprint - Not Displayed"
        ]

        self.assertEqual(self.parser.first_five_rows, expectation)

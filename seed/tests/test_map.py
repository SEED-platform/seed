# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Dan Gunter <dkgunter@lbl.gov>'
"""
"""
Unit tests for map.py
"""

import json
from StringIO import StringIO

from seed.tests import util
from django.test import TestCase
from seed.common import mapper

class TestMapping(TestCase):
    """Test mapping methods."""

    def jsonfile(self):
        return self._jsonfile()

    def _jsonfile(self):
        d = {"Key1": "value1",
         "key2": "value2",
         "has spaces": "value3",
         "has_underscores": "value4",
         "has  multi spaces": "value5",
         "has___multi  underscores": "value6",
         "normal ft2": "value7",
         "caret ft2": "value8",
         "super ft2": "value9"
         }
        for key in d:
            d[key] = [d[key], {mapper.Mapping.META_BEDES: True,
                               mapper.Mapping.META_TYPE: 'string'}]
        return StringIO(json.dumps(d))

    def setUp(self):
        self.json_file = self.jsonfile()

    def test_mapping_init(self):
        self.assertRaises(Exception, mapper.Mapping, None)
        m = mapper.Mapping(self.json_file)
        self.assertIsNotNone(m)

    def test_mapping_regex(self):
        m = mapper.Mapping(self.json_file, regex=True)
        self.assertEqual(m['.*1'].field, "value1")

    def test_mapping_case(self):
        m = mapper.Mapping(self.json_file, ignore_case=True)
        self.assertEqual(m['key1'].field, "value1")
        self.assertEqual(m['KEY1'].field, "value1")
        m = mapper.Mapping(self.jsonfile(), ignore_case=True, regex=True)
        self.assertEqual(m["K..1"].field, "value1")

    def test_mapping_spc(self):
        m = mapper.Mapping(self.json_file)
        self.assertEqual(m['has_spaces'].field, 'value3')
        self.assertEqual(m['has spaces'].field, 'value3')
        self.assertEqual(m['has underscores'].field, 'value4')
        self.assertEqual(m['has_multi spaces'].field, 'value5')
        self.assertEqual(m['has_multi underscores'].field, 'value6')

    def test_units(self):
        m = mapper.Mapping(self.json_file, encoding='latin_1')
        self.assertEqual(m['normal ft2'].field, 'value7')
        self.assertEqual(m['caret ft^2'].field, 'value8')
        self.assertEqual(m['super ft_'].field, 'value9')
        self.assertEqual(m[(u"super ft" + u'\u00B2').encode('latin_1')].field, 'value9')

    def test_mapping_conf(self):
        conf = mapper.MappingConfiguration()
        pm_mapping = conf.pm((1,0))
        self.assertIsInstance(pm_mapping, mapper.Mapping)

    def test_mapping_pm_to_SEED(self):
        expected = {"Address 1": "Address Line 1",
                    "Property ID": "PM Property ID",
                    "Portfolio Manager Property ID": "PM Property ID",
                    "some_other_field_not_in_the_designated_PM_mapping" : None}
        pm = mapper.get_pm_mapping("1.0", expected.keys())
        for src, tgt in expected.items():
            if tgt:
                self.assertEqual(pm[src].field, tgt)
                self.assertEqual(pm[src].is_bedes, False)
            else:
                self.assertFalse(src in pm)

    def test_mapping_pm_to_SEED_include_none(self):
        expected = {"Address 1": "Address Line 1",
                    "Property ID": "PM Property ID",
                    "Portfolio Manager Property ID": "PM Property ID",
                    "some_other_field_not_in_the_designated_PM_mapping" : None}
        pm = mapper.get_pm_mapping("1.0", expected.keys(), True)
        for src, tgt in expected.items():
            if tgt:
                self.assertEqual(pm[src].field, tgt)
                self.assertEqual(pm[src].is_bedes, False)
            else:
                self.assertIsNone(pm[src])

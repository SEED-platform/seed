# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from django.test import TestCase

from seed.lib.mappings.mapping_columns import MappingColumns

logger = logging.getLogger(__name__)


class TestMappingColumns(TestCase):
    def test_unicode_in_destination(self):
        raw_columns = ['foot', 'ankle', 'stomach']
        dest_columns = ['big foot', 'crankle', u'estómago']
        results = MappingColumns(raw_columns, dest_columns)

        expected = {
            'foot': ['_', 'big foot', 90],
            'ankle': ['_', 'crankle', 94],
            'stomach': ['_', u'est\xf3mago', 82]
        }
        self.assertDictEqual(expected, results.final_mappings)

    def test_unicode_in_raw(self):
        raw_columns = ['big foot', 'crankle', u'estómago']
        dest_columns = ['foot', 'ankle', 'stomach', u'estooomago']
        results = MappingColumns(raw_columns, dest_columns)

        expected = {
            'crankle': ['_', 'ankle', 94],
            'big foot': ['_', 'foot', 90],
            u'est\xf3mago': ['_', u'estooomago', 89]
        }
        self.assertDictEqual(expected, results.final_mappings)

    def test_resolve_duplicate(self):
        raw_columns = ['estomago', 'stomach']
        dest_columns = [u'estómago']
        results = MappingColumns(raw_columns, dest_columns)

        # Note that the stomach will resolve as 'PropertyState' by default.
        expected = {
            'estomago': ['_', u'est\xf3mago', 92],
            'stomach': ['PropertyState', 'stomach', 100]
        }
        self.assertDictEqual(expected, results.final_mappings)

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author noel.merket@nrel.gov
"""
import os
import tempfile
from django.test.runner import DiscoverRunner
from django.test import SimpleTestCase as TestCase
from lxml import objectify
from lxml.etree import XMLSyntaxError

from seed.hpxml.hpxml import HPXML


class NoDbTestRunner(DiscoverRunner):
    """ A test runner to test without database creation/deletion """

    def setup_databases(self, **kwargs):
        pass

    def teardown_databases(self, old_config, **kwargs):
        pass


class TestHPXML(TestCase):

    def setUp(self):
        self.xml_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'audit.xml')
        self.hpxml = HPXML()

    def test_constructor(self):
        self.assertTrue(self.hpxml.import_file(self.xml_file))
        self.assertRaises(IOError, self.hpxml.import_file, 'no/path/to/file.xml')
        fd, tempfile_path = tempfile.mkstemp()
        try:
            tree = objectify.parse(self.xml_file)
            root = tree.getroot()
            objectify.SubElement(root, 'BogusElement')
            tree.write(tempfile_path, encoding='utf-8')
            self.assertRaises(XMLSyntaxError, self.hpxml.import_file, tempfile_path)
        finally:
            os.close(fd)
            os.remove(tempfile_path)

    def test_get_building(self):
        self.assertTrue(self.hpxml.import_file(self.xml_file))
        bldg = self.hpxml._get_building()
        self.assertEqual(bldg.ProjectStatus.EventType, 'audit')
        self.hpxml.root.Building[1].ProjectStatus.EventType = 'job completion testing/final inspection'
        bldg = self.hpxml._get_building()
        self.assertEqual(bldg.BuildingID.get('id'), 'bldg1p')
        self.hpxml.root.Building[1].ProjectStatus.EventType = 'proposed workscope'
        bldg = self.hpxml._get_building('bldg1p')
        self.assertEqual(bldg.BuildingID.get('id'), 'bldg1p')

    def test_process(self):
        self.assertTrue(self.hpxml.import_file(self.xml_file))
        res = self.hpxml.process()
        expected = {
            'address_line_1': '123 Main St',
            'address_line_2': '',
            'city': 'Beverly Hills',
            'state': 'CA',
            'postal_code': '90210',
            'year_built': 1961,
            'conditioned_floor_area': 2400.0,
            'owner': 'Jane Customer',
            'owner_email': 'asdf@jkl.com',
            'energy_score': 8,
            'building_certification': 'Home Performance with Energy Star',
        }
        self.assertDictEqual(expected, res)
        self.hpxml.root.Customer.CustomerDetails.Person.Name.clear()
        res = self.hpxml.process()
        self.assertNotIn('owner', res.keys())


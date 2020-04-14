# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from io import BytesIO
from os import path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from lxml import etree

from config.settings.common import BASE_DIR
from seed.building_sync.building_sync import BuildingSync
from seed.models import (
    BuildingFile,
    User
)
from seed.utils.organizations import create_organization


class TestImport(TestCase):
    def test_import_v2_0_ok(self):
        # -- Setup
        filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'buildingsync_v2_0_bricr_workflow.xml')
        bs = BuildingSync()

        # -- Act
        bs.import_file(filename)

        # -- Assert
        self.assertEqual(BuildingSync.BUILDINGSYNC_V2_0, bs.version)

    def test_import_ATT_ok(self):
        # -- Setup
        filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'buildingsync_ATT_export.xml')
        bs = BuildingSync()

        # -- Act
        bs.import_file(filename)

        # -- Assert
        self.assertEqual(BuildingSync.BUILDINGSYNC_V2_0, bs.version)

    def test_import_fails_when_missing_schema(self):
        """import_file should raise an exception if it can't find the expected BuildingSync schema location"""
        # -- Setup
        filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'ex_1_no_schemaLocation.xml')
        bs = BuildingSync()

        # -- Act, Assert
        with self.assertRaises(Exception):
            bs.import_file(filename)


class TestProcess(TestCase):
    def test_parses_v2_0_property_info(self):
        # -- Setup
        filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'buildingsync_v2_0_bricr_workflow.xml')
        bs = BuildingSync()
        bs.import_file(filename)
        self.assertEqual(BuildingSync.BUILDINGSYNC_V2_0, bs.version)

        # -- Act
        result, messages = bs.process()

        # -- Assert
        expected_property_values = {
            'address_line_1': '123 MAIN BLVD',
            'city': 'San Francisco',
            'state': 'CA',
            'postal_code': '94124',
            'longitude': -122.38022804260254,
            'latitude': 37.74391054330132,
            'property_name': 'Building1',
            'property_type': 'Retail',
            'year_built': 2010,
            'floors_above_grade': 1,
            'floors_below_grade': 0,
            'premise_identifier': 'SF000011',
            'custom_id_1': '1',
            'gross_floor_area': 77579.0,
            'net_floor_area': 99887766.0,
            'footprint_floor_area': 215643.97259999998,
        }

        result_subset = {k: v for k, v in result.items() if k in expected_property_values}
        self.assertDictEqual(expected_property_values, result_subset)


class TestExport(TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestExport, cls).setUpClass()

        # make sure the parse is setup s.t. we can diff xml (ie they are in predictable format)
        parser = etree.XMLParser(remove_blank_text=True)
        etree.set_default_parser(parser)

    def setUp(self):
        self.DATA_DIR = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data')

        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)

    def test_export_without_property_state(self):
        """Exporting without a property state should just give us the original xml"""
        # -- Setup
        filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'buildingsync_v2_0_bricr_workflow.xml')
        bs = BuildingSync()
        bs.import_file(filename)

        # -- Act
        result = bs.export(None)
        # get original xml in same structure as our exported result
        with open(filename, 'r') as f:
            expected_tree = etree.parse(f)
            expected_xml = etree.tostring(expected_tree, pretty_print=True)

        actual_tree = etree.parse(BytesIO(result.encode()))
        actual_xml = etree.tostring(actual_tree, pretty_print=True)

        self.assertEqual(expected_xml, actual_xml)

    def test_export_with_property_state(self):
        """Exporting _with_ a property state that differs from the xml on exported fields should update the xml"""
        # This test does the following
        # 1. upload xml as a BuildingFile, then process it to create a property state
        # 2. update the property state so it differs from the xml data on fields that should be exported (ie should update the xml when exported)
        # 3. call export on the xml, passing in the updated property state
        # 4. create a new BuildingFile from the exported xml, and process it to get another property state
        # If the import/export flow works, we would expect our property state constructed from the exported xml to have values
        # that match the changes we made to the original property state

        # -- Setup
        # Go through the building file process flow to create a property state from the xml
        filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'buildingsync_v2_0_bricr_workflow.xml')
        file = open(filename, 'rb')
        simple_uploaded_file = SimpleUploadedFile(file.name, file.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, _, messages = bf.process(self.org.id, self.org.cycles.first())
        self.assertTrue(status, f'Expected process to be successful: {messages}')

        # change some values of the property state so that it differs from the xml
        address_line_1 = 'My New Address'
        postal_code = '30161'
        net_floor_area = 990099  # PropertyState doesn't have this field, it's extra data
        property_state.address_line_1 = address_line_1
        property_state.postal_code = postal_code
        property_state.extra_data['net_floor_area'] = net_floor_area
        property_state.save()

        # -- Act
        bs = BuildingSync()
        bs.import_file(filename)
        exported_xml = bs.export(property_state)

        # -- Assert
        filename = 'exported_bsync_test.xml'
        simple_uploaded_file = SimpleUploadedFile(filename, exported_xml.encode())

        # create a _new_ property state from the exported result
        # this (1) makes it easy to check values without doing xpath stuff here, and (2) tests a full export->import flow
        exported_bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, exported_property_state, _, messages = exported_bf.process(self.org.id, self.org.cycles.first())
        self.assertTrue(status, f'Expected process to be successful: {messages}')

        # compare the property states
        self.assertEqual(address_line_1, exported_property_state.address_line_1)
        self.assertEqual(postal_code, exported_property_state.postal_code)
        self.assertEqual(net_floor_area, exported_property_state.extra_data['net_floor_area'])

        # assert the exported file is valid according to the schema
        schema = BuildingSync.get_schema(BuildingSync.BUILDINGSYNC_V2_0)
        schema.validate(exported_xml)

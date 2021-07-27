# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from os import path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from seed.models import User
from seed.models.building_file import BuildingFile
from seed.models.scenarios import Scenario
from seed.models.meters import Meter, MeterReading
from seed.utils.organizations import create_organization


class TestBuildingFiles(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)

    def test_file_type_lookup(self):
        self.assertEqual(BuildingFile.str_to_file_type(None), None)
        self.assertEqual(BuildingFile.str_to_file_type(''), None)
        self.assertEqual(BuildingFile.str_to_file_type(1), 1)
        self.assertEqual(BuildingFile.str_to_file_type('1'), 1)
        self.assertEqual(BuildingFile.str_to_file_type('BuildingSync'), 1)
        self.assertEqual(BuildingFile.str_to_file_type('BUILDINGSYNC'), 1)
        self.assertEqual(BuildingFile.str_to_file_type('Unknown'), 0)

    def test_buildingsync_constructor(self):
        filename = path.join(path.dirname(__file__), 'data', 'ex_1.xml')
        file = open(filename, 'rb')
        simple_uploaded_file = SimpleUploadedFile(file.name, file.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, property_view, messages = bf.process(self.org.id, self.org.cycles.first())
        self.assertTrue(status)
        self.assertEqual(property_state.address_line_1, '123 Main St')
        self.assertEqual(property_state.property_type, 'Office')
        self.assertEqual(messages, {'errors': [], 'warnings': []})

    def test_buildingsync_constructor_diff_ns(self):
        filename = path.join(path.dirname(__file__), 'data', 'ex_1_different_namespace.xml')
        file = open(filename, 'rb')
        simple_uploaded_file = SimpleUploadedFile(file.name, file.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, property_view, messages = bf.process(self.org.id, self.org.cycles.first())
        self.assertTrue(status)
        self.assertEqual(property_state.address_line_1, '1215 - 18th St')
        self.assertEqual(messages, {'errors': [], 'warnings': []})

    def test_buildingsync_constructor_single_scenario(self):
        # test having only 1 measure and 1 scenario
        filename = path.join(path.dirname(__file__), 'data', 'test_single_scenario.xml')
        file = open(filename, 'rb')
        simple_uploaded_file = SimpleUploadedFile(file.name, file.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, property_view, messages = bf.process(self.org.id, self.org.cycles.first())
        self.assertTrue(status)
        self.assertEqual(property_state.address_line_1, '123 Main St')
        self.assertEqual(messages, {'errors': [], 'warnings': []})

    def test_buildingsync_bricr_import(self):
        filename = path.join(path.dirname(__file__), 'data', 'buildingsync_v2_0_bricr_workflow.xml')
        file = open(filename, 'rb')
        simple_uploaded_file = SimpleUploadedFile(file.name, file.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, property_view, messages = bf.process(self.org.id, self.org.cycles.first())
        self.assertTrue(status, f'Expected process() to succeed; messages: {messages}')
        self.assertEqual(property_state.address_line_1, '123 MAIN BLVD')
        self.assertEqual(messages, {'errors': [], 'warnings': []})

        # look for scenarios, meters, and meterreadings
        scenarios = Scenario.objects.filter(property_state_id=property_state.id)
        self.assertTrue(len(scenarios) > 0)
        meters = Meter.objects.filter(scenario_id=scenarios[0].id)
        self.assertTrue(len(meters) > 0)
        readings = MeterReading.objects.filter(meter_id=meters[0].id)
        self.assertTrue(len(readings) > 0)

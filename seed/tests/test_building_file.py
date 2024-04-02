# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from os import path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from config.settings.common import BASE_DIR
from seed.models import Property, User
from seed.models.building_file import BuildingFile
from seed.models.events import ATEvent
from seed.models.meters import Meter, MeterReading
from seed.models.scenarios import Scenario
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class TestBuildingFiles(TestCase):
    def setUp(self):
        user_details = {'username': 'test_user@demo.com', 'password': 'test_pass', 'email': 'test_user@demo.com'}
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
        self.assertEqual(BuildingFile.str_to_file_type('hpxml'), 3)

    def test_buildingsync_constructor(self):
        filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'ex_1.xml')
        with open(filename, 'rb') as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, _property_view, messages = bf.process(
            self.org.id, self.org.cycles.first(), access_level_instance=self.org.root
        )
        self.assertTrue(status)
        self.assertEqual(property_state.address_line_1, '123 Main St')
        self.assertEqual(property_state.property_type, 'Office')
        self.assertEqual(messages, {'errors': [], 'warnings': []})

    def test_buildingsync_constructor_diff_ns(self):
        filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'ex_1_different_namespace.xml')
        with open(filename, 'rb') as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, _property_view, messages = bf.process(
            self.org.id, self.org.cycles.first(), access_level_instance=self.org.root
        )
        self.assertTrue(status)
        self.assertEqual(property_state.address_line_1, '1215 - 18th St')
        self.assertEqual(messages, {'errors': [], 'warnings': []})

    def test_buildingsync_constructor_single_scenario(self):
        # test having only 1 measure and 1 scenario
        filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'test_single_scenario.xml')
        with open(filename, 'rb') as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, property_view, messages = bf.process(
            self.org.id, self.org.cycles.first(), access_level_instance=self.org.root
        )
        self.assertTrue(status)
        self.assertEqual(property_state.address_line_1, '123 Main St')
        self.assertEqual(messages, {'errors': [], 'warnings': []})

        events = ATEvent.objects.filter(property=property_view.property)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.property_id, property_view.property_id)
        self.assertEqual(event.cycle_id, property_view.cycle_id)
        self.assertEqual(event.building_file_id, bf.id)
        self.assertEqual(len(event.scenarios.all()), 1)

    def test_buildingsync_bricr_import(self):
        filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'buildingsync_v2_0_bricr_workflow.xml')
        file = open(filename, 'rb')
        simple_uploaded_file = SimpleUploadedFile(file.name, file.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, _property_view, messages = bf.process(
            self.org.id, self.org.cycles.first(), access_level_instance=self.org.root
        )
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

    def test_buildingsync_bricr_update_retains_scenarios(self):
        # -- Setup
        filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'buildingsync_v2_0_bricr_workflow.xml')
        with open(filename, 'rb') as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, property_view, messages = bf.process(
            self.org.id, self.org.cycles.first(), access_level_instance=self.org.root
        )
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

        # -- Act
        new_bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        # UPDATE the property using the same file
        status, new_property_state, property_view, messages = new_bf.process(self.org.id, self.org.cycles.first(), property_view)

        # -- Assert
        self.assertTrue(status, f'Expected process() to succeed; messages: {messages}')
        self.assertEqual(new_property_state.address_line_1, '123 MAIN BLVD')
        self.assertEqual(messages, {'errors': [], 'warnings': []})

        # look for scenarios, meters, and meterreadings
        self.assertNotEqual(property_state.id, new_property_state.id, 'Expected BuildingFile to create a new property state')
        scenarios = Scenario.objects.filter(property_state_id=new_property_state.id)
        self.assertTrue(len(scenarios) > 0)
        meters = Meter.objects.filter(scenario_id=scenarios[0].id)
        self.assertTrue(len(meters) > 0)
        readings = MeterReading.objects.filter(meter_id=meters[0].id)
        self.assertTrue(len(readings) > 0)

    def test_hpxml_constructor(self):
        filename = path.join(BASE_DIR, 'seed', 'hpxml', 'tests', 'data', 'audit.xml')
        with open(filename, 'rb') as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

        bf = BuildingFile.objects.create(file=simple_uploaded_file, filename=filename, file_type=BuildingFile.HPXML)

        status, property_state, _property_view, messages = bf.process(
            self.org.id, self.org.cycles.first(), access_level_instance=self.org.root
        )
        self.assertTrue(status)
        self.assertEqual(property_state.owner, 'Jane Customer')
        self.assertEqual(property_state.energy_score, 8)
        self.assertEqual(messages, {'errors': [], 'warnings': []})


class TestBuildingFilesPermission(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.cycle = self.cycle_factory.get_cycle()

        self.root_property = self.property_factory.get_property(access_level_instance=self.root_level_instance)
        self.root_property_state = self.property_state_factory.get_property_state()
        self.root_property_view = self.property_view_factory.get_property_view(prprty=self.root_property, state=self.root_property_state)

        self.child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)
        self.child_property_state = self.property_state_factory.get_property_state()
        self.child_property_view = self.property_view_factory.get_property_view(prprty=self.child_property, state=self.child_property_state)

        self.filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'buildingsync_v2_0_bricr_workflow.xml')
        with open(self.filename, 'rb') as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

        self.root_bf = BuildingFile.objects.create(
            file=simple_uploaded_file, filename=self.filename, file_type=BuildingFile.BUILDINGSYNC, property_state=self.root_property_state
        )

        self.child_bf = BuildingFile.objects.create(
            file=simple_uploaded_file, filename=self.filename, file_type=BuildingFile.BUILDINGSYNC, property_state=self.child_property_state
        )

    def test_list(self):
        url = reverse('api:v3:building_files-list') + f'?organization_id={self.org.id}'

        self.login_as_root_member()
        result = self.client.get(url)
        assert {d['id'] for d in result.json()['data']} == {self.root_bf.id, self.child_bf.id}

        self.login_as_child_member()
        result = self.client.get(url)
        assert {d['id'] for d in result.json()['data']} == {self.child_bf.id}

    def test_get(self):
        url = reverse('api:v3:building_files-detail', args=[self.root_bf.id]) + f'?organization_id={self.org.id}'

        self.login_as_root_member()
        result = self.client.get(url)
        assert result.status_code == 200

        self.login_as_child_member()
        result = self.client.get(url)
        assert result.status_code == 404

    def test_create(self):
        url = reverse('api:v3:building_files-list') + f'?organization_id={self.org.id}&cycle_id={self.cycle.id}'

        self.login_as_root_member()
        with open(self.filename, 'rb') as f:
            response = self.client.post(
                url,
                {
                    'file': f,
                    'file_type': 'BuildingSync',
                },
            )
        property = Property.objects.get(pk=response.json()['data']['property_view']['property'])
        assert property.access_level_instance == self.root_level_instance

        self.login_as_child_member()
        with open(self.filename, 'rb') as f:
            response = self.client.post(
                url,
                {
                    'file': f,
                    'file_type': 'BuildingSync',
                },
            )
        property = Property.objects.get(pk=response.json()['data']['property_view']['property'])
        assert property.access_level_instance == self.child_level_instance

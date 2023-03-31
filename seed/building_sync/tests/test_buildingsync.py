# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from os import path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from seed.models import User
from seed.models.building_file import BuildingFile
from seed.models.meters import Meter, MeterReading
from seed.models.scenarios import Scenario
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
        with open(filename, 'rb') as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, property_view, messages = bf.process(self.org.id, self.org.cycles.first())
        self.assertTrue(status)
        self.assertEqual(property_state.address_line_1, '123 Main St')
        self.assertEqual(property_state.property_type, 'Office')
        self.assertEqual(property_state.extra_data.get("audit_date"), None)
        self.assertEqual(property_state.extra_data.get("audit_date_type"), None)
        self.assertEqual(messages, {'errors': [], 'warnings': []})

    def test_buildingsync_constructor_diff_ns(self):
        filename = path.join(path.dirname(__file__), 'data', 'ex_1_different_namespace.xml')
        with open(filename, 'rb') as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

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
        with open(filename, 'rb') as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

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
        with open(filename, 'rb') as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

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

    def test_buildingsync_audit_template_import(self):
        audit_template_filename = 'example_SF_audit_report_BS_v2.3_081321.xml'
        filename = path.join(path.dirname(__file__), 'data', audit_template_filename)
        with open(filename, 'rb') as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, property_view, messages = bf.process(self.org.id, self.org.cycles.first())
        self.assertTrue(status, f'Expected process() to succeed; messages: {messages}')
        self.assertEqual(property_state.address_line_1, '123 Example Street')
        self.assertEqual(property_state.extra_data.get("audit_date"), "2019-07-01")
        self.assertEqual(property_state.extra_data.get("audit_date_type"), "Level 2: Energy Survey and Analysis")
        self.assertEqual(messages['errors'], [])

        # we expect warnings indicating skipped scenarios and meters
        # Specifically, we expect some of these to get skipped because they are
        # "junk" scenarios/meters that Audit Template puts into the BuildingSync file
        expected_warnings = [
            "Skipping Scenario ScenarioType-69909976065980 because it doesn't include measures or meter data.",
            "Skipping resource use ResourceUseType-69909985411100 due to missing type or units",
            "Skipping Scenario ScenarioType-69909985343680 because it doesn't include measures or meter data.",
            "Skipping Scenario ScenarioType-69909979554640 because it doesn't include measures or meter data.",
            "Skipping Scenario ScenarioType-69909979696200 because it doesn't include measures or meter data.",
            "Skipping meter ResourceUseType-69909980009880 because it had no valid readings.",
            "Skipping Scenario ScenarioType-69909937717840 because it doesn't include measures or meter data.",
            "Skipping meter ResourceUseType-69909964194040 because it had no valid readings.",
            "Skipping Scenario ScenarioType-69909937754040 because it doesn't include measures or meter data.",
            "Skipping meter ResourceUseType-69909940642500 because it had no valid readings.",
            "Skipping Scenario ScenarioType-69909943858060 because it doesn't include measures or meter data.",
            "Skipping meter ResourceUseType-69909941989860 because it had no valid readings.",
            "Skipping meter ResourceUseType-69909942271180 because it had no valid readings.",
            "Skipping meter ResourceUseType-69909942496220 because it had no valid readings.",
            "Skipping meter ResourceUseType-69909942808020 because it had no valid readings.",
            "Skipping meter ResourceUseType-69909942954100 because it had no valid readings.",
            "Skipping Scenario ScenarioType-69909940756840 because it doesn't include measures or meter data.",
            "Skipping meter ResourceUseType-69909944487040 because it had no valid readings.",
            "Skipping meter ResourceUseType-69909944645960 because it had no valid readings.",
            "Skipping Scenario ScenarioType-69909944388980 because it doesn't include measures or meter data.",
            "Skipped meter Site Energy Use ResourceUseType-69909963979840 because it had no valid readings"
        ]
        self.assertEqual(
            messages['warnings'],
            expected_warnings,
        )

        # verify the scenario with electricity readings was imported correctly
        # There are two meters for electricity, even though there's one ResourceUse,
        # because AT puts some meter reading data into AllResourceTotals and links
        # it to a TimeSeriesData with a UserDefinedField. This makes sure we're
        # importing those readings as well.
        electricity_scenario = Scenario.objects.get(name='Audit Template Energy Meter Readings - Electricity')
        electricity_meters = Meter.objects.filter(scenario_id=electricity_scenario.id)
        self.assertEqual(electricity_meters.count(), 2)
        self.assertEqual(electricity_meters[0].meter_readings.count(), 12)
        self.assertEqual(electricity_meters[1].meter_readings.count(), 12)

        # verify the scenario with fuel oil readings was imported correctly
        oil_scenario = Scenario.objects.get(name='Audit Template Energy Deliveries - Fuel Oil #1')
        oil_meters = Meter.objects.filter(scenario_id=oil_scenario.id)
        self.assertEqual(oil_meters.count(), 1)
        self.assertEqual(oil_meters[0].meter_readings.count(), 1)

        # verify we imported the package of measures for lighting and HVAC
        lighting_package_scenario = Scenario.objects.get(name='Lighting retrofit')
        self.assertEqual(lighting_package_scenario.measures.count(), 1)

        hvac_package_scenario = Scenario.objects.get(name='HVAC Upgrade')
        self.assertEqual(hvac_package_scenario.measures.count(), 1)

        # we only expect those scenarios above to have been imported
        all_scenarios = Scenario.objects.filter(property_state_id=property_state.id)
        self.assertEqual(all_scenarios.count(), 4)

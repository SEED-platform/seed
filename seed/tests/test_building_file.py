"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from os import path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from config.settings.common import BASE_DIR
from seed.models import Measure, Property, PropertyMeasure, User
from seed.models.building_file import BuildingFile
from seed.models.events import ATEvent
from seed.models.meters import Meter, MeterReading
from seed.models.scenarios import Scenario
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class TestBuildingFiles(TestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)

    def test_file_type_lookup(self):
        self.assertEqual(BuildingFile.str_to_file_type(None), None)
        self.assertEqual(BuildingFile.str_to_file_type(""), None)
        self.assertEqual(BuildingFile.str_to_file_type(1), 1)
        self.assertEqual(BuildingFile.str_to_file_type("1"), 1)
        self.assertEqual(BuildingFile.str_to_file_type("BuildingSync"), 1)
        self.assertEqual(BuildingFile.str_to_file_type("BUILDINGSYNC"), 1)
        self.assertEqual(BuildingFile.str_to_file_type("Unknown"), 0)
        self.assertEqual(BuildingFile.str_to_file_type("hpxml"), 3)

    def test_buildingsync_constructor(self):
        filename = path.join(BASE_DIR, "seed", "building_sync", "tests", "data", "ex_1.xml")
        with open(filename, "rb") as f:
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
        self.assertEqual(property_state.address_line_1, "123 Main St")
        self.assertEqual(property_state.property_type, "Office")
        self.assertEqual(messages, {"errors": [], "warnings": []})

    def test_buildingsync_constructor_diff_ns(self):
        filename = path.join(BASE_DIR, "seed", "building_sync", "tests", "data", "ex_1_different_namespace.xml")
        with open(filename, "rb") as f:
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
        self.assertEqual(property_state.address_line_1, "1215 - 18th St")
        self.assertEqual(messages, {"errors": [], "warnings": []})

    def test_buildingsync_constructor_single_scenario(self):
        # test having only 1 measure and 1 scenario
        filename = path.join(BASE_DIR, "seed", "building_sync", "tests", "data", "test_single_scenario.xml")
        with open(filename, "rb") as f:
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
        self.assertEqual(property_state.address_line_1, "123 Main St")
        self.assertEqual(messages, {"errors": [], "warnings": []})

        events = ATEvent.objects.filter(property=property_view.property)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.property_id, property_view.property_id)
        self.assertEqual(event.cycle_id, property_view.cycle_id)
        self.assertEqual(event.building_file_id, bf.id)
        self.assertEqual(len(event.scenarios.all()), 1)

    def test_buildingsync_measures_fall_back_to_latest_schema_version(self):
        # Orgs only get 1.0.0 and 2.7.0 measures, so a 2.6.0 file should fall back to the latest available version
        filename = path.join(BASE_DIR, "seed", "building_sync", "tests", "data", "ex_1_v2.7.0.xml")
        with open(filename, "rb") as f:
            content = f.read().replace(b"v2.7.0", b"v2.6.0").replace(b'version="2.7.0"', b'version="2.6.0"')
        self.assertFalse(Measure.objects.filter(organization=self.org, schema_version="2.6.0").exists())

        bf = BuildingFile.objects.create(
            file=SimpleUploadedFile("ex_1_v2.6.0.xml", content),
            filename="ex_1_v2.6.0.xml",
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, _property_view, messages = bf.process(
            self.org.id, self.org.cycles.first(), access_level_instance=self.org.root
        )
        self.assertTrue(status)
        self.assertEqual(messages["errors"], [])
        self.assertIn(
            "Measure service_hot_water_systems:install_heat_pump_shw_system not found for schema version 2.6.0; using schema version 2.7.0",
            messages["warnings"],
        )

        property_measures = PropertyMeasure.objects.filter(property_state=property_state)
        self.assertEqual(property_measures.count(), 1)
        self.assertEqual(property_measures.first().measure.schema_version, "2.7.0")

    def test_buildingsync_measure_annual_cost_savings(self):
        filename = path.join(BASE_DIR, "seed", "building_sync", "tests", "data", "ex_1_v2.7.0.xml")
        with open(filename, "rb") as f:
            content = f.read().replace(
                b"<auc:LongDescription>Install heat pump SHW system</auc:LongDescription>",
                b"<auc:LongDescription>Install heat pump SHW system</auc:LongDescription>"
                b"<auc:MeasureSavingsAnalysis><auc:AnnualSavingsCost>1000</auc:AnnualSavingsCost></auc:MeasureSavingsAnalysis>",
            )

        bf = BuildingFile.objects.create(
            file=SimpleUploadedFile("ex_1_v2.7.0.xml", content),
            filename="ex_1_v2.7.0.xml",
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, _property_view, messages = bf.process(
            self.org.id, self.org.cycles.first(), access_level_instance=self.org.root
        )
        self.assertTrue(status)
        self.assertEqual(messages["errors"], [])
        self.assertEqual(PropertyMeasure.objects.get(property_state=property_state).annual_cost_savings, 1000.0)

    def test_buildingsync_measure_and_scenario_energy_savings(self):
        filename = path.join(BASE_DIR, "seed", "building_sync", "tests", "data", "ex_1_v2.7.0.xml")
        with open(filename, "rb") as f:
            content = f.read().replace(
                b"<auc:LongDescription>Install heat pump SHW system</auc:LongDescription>",
                b"<auc:LongDescription>Install heat pump SHW system</auc:LongDescription>"
                b"<auc:MeasureSavingsAnalysis>"
                b"<auc:AnnualSavingsByFuels>"
                b"<auc:AnnualSavingsByFuel><auc:EnergyResource>Electricity</auc:EnergyResource>"
                b"<auc:AnnualSavingsNativeUnits>10</auc:AnnualSavingsNativeUnits>"
                b"<auc:ResourceUnits>kWh</auc:ResourceUnits>"
                b"</auc:AnnualSavingsByFuel>"
                b"<auc:AnnualSavingsByFuel><auc:EnergyResource>Natural gas</auc:EnergyResource>"
                b"<auc:AnnualSavingsNativeUnits>2</auc:AnnualSavingsNativeUnits>"
                b"<auc:ResourceUnits>therms</auc:ResourceUnits>"
                b"</auc:AnnualSavingsByFuel>"
                b"</auc:AnnualSavingsByFuels>"
                b"<auc:AnnualPeakElectricityReduction>7.5</auc:AnnualPeakElectricityReduction>"
                b"</auc:MeasureSavingsAnalysis>",
            )

        content = content.replace(
            b"</auc:Facility>",
            b"<auc:Reports><auc:Report><auc:Scenarios>"
            b'<auc:Scenario ID="Scenario-1"><auc:ScenarioName>Energy savings</auc:ScenarioName><auc:ScenarioType>'
            b"<auc:PackageOfMeasures><auc:AnnualSavingsByFuels>"
            b"<auc:AnnualSavingsByFuel><auc:EnergyResource>Electricity</auc:EnergyResource>"
            b"<auc:AnnualSavingsNativeUnits>5</auc:AnnualSavingsNativeUnits>"
            b"<auc:ResourceUnits>kWh</auc:ResourceUnits>"
            b"</auc:AnnualSavingsByFuel>"
            b"<auc:AnnualSavingsByFuel><auc:EnergyResource>Natural gas</auc:EnergyResource>"
            b"<auc:AnnualSavingsNativeUnits>1.25</auc:AnnualSavingsNativeUnits>"
            b"<auc:ResourceUnits>therms</auc:ResourceUnits>"
            b"</auc:AnnualSavingsByFuel>"
            b"</auc:AnnualSavingsByFuels>"
            b"<auc:AnnualPeakElectricityReduction>4.5</auc:AnnualPeakElectricityReduction>"
            b"</auc:PackageOfMeasures></auc:ScenarioType></auc:Scenario>"
            b"</auc:Scenarios></auc:Report></auc:Reports></auc:Facility>",
            1,
        )

        bf = BuildingFile.objects.create(
            file=SimpleUploadedFile("ex_1_v2.7.0.xml", content),
            filename="ex_1_v2.7.0.xml",
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, _property_view, messages = bf.process(
            self.org.id, self.org.cycles.first(), access_level_instance=self.org.root
        )
        self.assertTrue(status)
        self.assertEqual(messages["errors"], [])

        measure = PropertyMeasure.objects.get(property_state=property_state)
        self.assertEqual(measure.annual_electricity_savings, 34.1)
        self.assertEqual(measure.annual_natural_gas_savings, 200.0)
        self.assertEqual(measure.annual_peak_electricity_reduction, 7.5)

        scenario = Scenario.objects.get(property_state=property_state, name="Energy savings")
        self.assertEqual(scenario.annual_electricity_savings, 17.05)
        self.assertEqual(scenario.annual_natural_gas_savings, 125.0)
        self.assertEqual(scenario.annual_peak_electricity_reduction, 4.5)

    def test_buildingsync_bricr_import(self):
        filename = path.join(BASE_DIR, "seed", "building_sync", "tests", "data", "buildingsync_v2_0_bricr_workflow.xml")
        with open(filename, "rb") as file:
            simple_uploaded_file = SimpleUploadedFile(file.name, file.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, _property_view, messages = bf.process(
            self.org.id, self.org.cycles.first(), access_level_instance=self.org.root
        )
        self.assertTrue(status, f"Expected process() to succeed; messages: {messages}")
        self.assertEqual(property_state.address_line_1, "123 MAIN BLVD")
        self.assertEqual(messages, {"errors": [], "warnings": []})

        # look for scenarios, meters, and meterreadings
        scenarios = Scenario.objects.filter(property_state_id=property_state.id)
        self.assertTrue(len(scenarios) > 0)
        meters = Meter.objects.filter(scenario_id=scenarios[0].id)
        self.assertTrue(len(meters) > 0)
        readings = MeterReading.objects.filter(meter_id=meters[0].id)
        self.assertTrue(len(readings) > 0)

    def test_buildingsync_bricr_update_retains_scenarios(self):
        # -- Setup
        filename = path.join(BASE_DIR, "seed", "building_sync", "tests", "data", "buildingsync_v2_0_bricr_workflow.xml")
        with open(filename, "rb") as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, property_view, messages = bf.process(
            self.org.id, self.org.cycles.first(), access_level_instance=self.org.root
        )
        self.assertTrue(status, f"Expected process() to succeed; messages: {messages}")
        self.assertEqual(property_state.address_line_1, "123 MAIN BLVD")
        self.assertEqual(messages, {"errors": [], "warnings": []})

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
        self.assertTrue(status, f"Expected process() to succeed; messages: {messages}")
        self.assertEqual(new_property_state.address_line_1, "123 MAIN BLVD")
        self.assertEqual(messages, {"errors": [], "warnings": []})

        # look for scenarios, meters, and meterreadings
        self.assertNotEqual(property_state.id, new_property_state.id, "Expected BuildingFile to create a new property state")
        scenarios = Scenario.objects.filter(property_state_id=new_property_state.id)
        self.assertTrue(len(scenarios) > 0)
        meters = Meter.objects.filter(scenario_id=scenarios[0].id)
        self.assertTrue(len(meters) > 0)
        readings = MeterReading.objects.filter(meter_id=meters[0].id)
        self.assertTrue(len(readings) > 0)

    def test_hpxml_constructor(self):
        filename = path.join(BASE_DIR, "seed", "hpxml", "tests", "data", "audit.xml")
        with open(filename, "rb") as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

        bf = BuildingFile.objects.create(file=simple_uploaded_file, filename=filename, file_type=BuildingFile.HPXML)

        status, property_state, _property_view, messages = bf.process(
            self.org.id, self.org.cycles.first(), access_level_instance=self.org.root
        )
        self.assertTrue(status)
        self.assertEqual(property_state.owner, "Jane Customer")
        self.assertEqual(property_state.energy_score, 8)
        self.assertEqual(messages, {"errors": [], "warnings": []})


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

        self.filename = path.join(BASE_DIR, "seed", "building_sync", "tests", "data", "buildingsync_v2_0_bricr_workflow.xml")
        with open(self.filename, "rb") as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

        self.root_bf = BuildingFile.objects.create(
            file=simple_uploaded_file, filename=self.filename, file_type=BuildingFile.BUILDINGSYNC, property_state=self.root_property_state
        )

        self.child_bf = BuildingFile.objects.create(
            file=simple_uploaded_file, filename=self.filename, file_type=BuildingFile.BUILDINGSYNC, property_state=self.child_property_state
        )

    def test_list(self):
        url = reverse("api:v3:building_files-list") + f"?organization_id={self.org.id}"

        self.login_as_root_member()
        result = self.client.get(url)
        assert {d["id"] for d in result.json()["data"]} == {self.root_bf.id, self.child_bf.id}

        self.login_as_child_member()
        result = self.client.get(url)
        assert {d["id"] for d in result.json()["data"]} == {self.child_bf.id}

    def test_get(self):
        url = reverse("api:v3:building_files-detail", args=[self.root_bf.id]) + f"?organization_id={self.org.id}"

        self.login_as_root_member()
        result = self.client.get(url)
        assert result.status_code == 200

        self.login_as_child_member()
        result = self.client.get(url)
        assert result.status_code == 404

    def test_create(self):
        url = reverse("api:v3:building_files-list") + f"?organization_id={self.org.id}&cycle_id={self.cycle.id}"

        self.login_as_root_member()
        with open(self.filename, "rb") as f:
            response = self.client.post(
                url,
                {
                    "file": f,
                    "file_type": "BuildingSync",
                },
            )
        property = Property.objects.get(pk=response.json()["data"]["property_view"]["property"])
        assert property.access_level_instance == self.root_level_instance

        self.login_as_child_member()
        with open(self.filename, "rb") as f:
            response = self.client.post(
                url,
                {
                    "file": f,
                    "file_type": "BuildingSync",
                },
            )
        property = Property.objects.get(pk=response.json()["data"]["property_view"]["property"])
        assert property.access_level_instance == self.child_level_instance

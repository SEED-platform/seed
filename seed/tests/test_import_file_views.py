# !/usr/bin/env python
# encoding: utf-8

import ast
import os

from datetime import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils.timezone import (
    get_current_timezone,
)

from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    PropertyState,
    PropertyView,
)
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
)
from seed.utils.organizations import create_organization
from seed.tests.util import DataMappingBaseTestCase


class TestMeterViewSet(DataMappingBaseTestCase):
    def setUp(self):
        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **self.user_details
        )
        self.org, _, _ = create_organization(self.user)

        # For some reason, defaults weren't established consistently for each test.
        self.org.display_meter_units = Organization._default_display_meter_units.copy()
        self.org.save()
        self.client.login(**self.user_details)

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id

        # pm_property_ids must match those within example-monthly-meter-usage.xlsx
        self.pm_property_id_1 = '5766973'
        self.pm_property_id_2 = '5766975'

        property_details['pm_property_id'] = self.pm_property_id_1
        state_1 = PropertyState(**property_details)
        state_1.save()
        self.state_1 = PropertyState.objects.get(pk=state_1.id)

        property_details['pm_property_id'] = self.pm_property_id_2
        state_2 = PropertyState(**property_details)
        state_2.save()
        self.state_2 = PropertyState.objects.get(pk=state_2.id)

        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_1 = self.property_factory.get_property()
        self.property_2 = self.property_factory.get_property()

        self.property_view_1 = PropertyView.objects.create(property=self.property_1, cycle=self.cycle, state=self.state_1)
        self.property_view_2 = PropertyView.objects.create(property=self.property_2, cycle=self.cycle, state=self.state_2)

        self.import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)

        # This file has multiple tabs
        filename = "example-pm-monthly-meter-usage.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

    def test_parsed_meters_confirmation_verifies_energy_type_and_units(self):
        url = reverse('api:v3:import_files-pm-meters-preview', kwargs={'pk': self.import_file.id})
        url += f'?organization_id={self.org.pk}'
        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = [
            {
                "parsed_type": "Electric - Grid",
                "parsed_unit": "kBtu (thousand Btu)",
            },
            {
                "parsed_type": "Natural Gas",
                "parsed_unit": "kBtu (thousand Btu)",
            },
        ]

        self.assertCountEqual(result_dict.get("validated_type_units"), expectation)

    def test_parsed_meters_confirmation_verifies_energy_type_and_units_and_ignores_invalid_types_and_units(self):
        filename = "example-pm-monthly-meter-usage-with-unknown-types-and-units.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        import_file_with_invalids = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

        url = reverse('api:v3:import_files-pm-meters-preview', kwargs={'pk': import_file_with_invalids.id})
        url += f'?organization_id={self.org.pk}'
        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = [
            {
                "parsed_type": "Electric - Grid",
                "parsed_unit": "kBtu (thousand Btu)",
            },
            {
                "parsed_type": "Natural Gas",
                "parsed_unit": "kBtu (thousand Btu)",
            },
        ]

        self.assertCountEqual(result_dict.get("validated_type_units"), expectation)

    def test_parsed_meters_confirmation_returns_pm_property_ids_and_corresponding_incoming_counts(self):
        url = reverse('api:v3:import_files-pm-meters-preview', kwargs={'pk': self.import_file.id})
        url += f'?organization_id={self.org.pk}'
        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = [
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-0",
                "type": 'Electric - Grid',
                "incoming": 2,
            }, {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-1",
                "type": 'Natural Gas',
                "incoming": 2,
            }, {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-0",
                "type": 'Electric - Grid',
                "incoming": 2,
            }, {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-1",
                "type": 'Natural Gas',
                "incoming": 2,
            },
        ]

        self.assertCountEqual(result_dict.get("proposed_imports"), expectation)

    def test_parsed_meters_confirmation_also_verifies_cost_type_and_units_and_counts(self):
        filename = "example-pm-monthly-meter-usage-2-cost-meters.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        cost_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

        url = reverse('api:v3:import_files-pm-meters-preview', kwargs={'pk': cost_import_file.id})
        url += f'?organization_id={self.org.pk}'
        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        validated_type_units = [
            {
                "parsed_type": "Electric - Grid",
                "parsed_unit": "kBtu (thousand Btu)",
            },
            {
                "parsed_type": "Natural Gas",
                "parsed_unit": "kBtu (thousand Btu)",
            },
            {
                "parsed_type": "Cost",
                "parsed_unit": "US Dollars",
            },
        ]

        self.assertCountEqual(result_dict.get("validated_type_units"), validated_type_units)

        proposed_imports = [
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-0",
                "type": 'Electric - Grid',
                "incoming": 2,
            }, {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-1",
                "type": 'Natural Gas',
                "incoming": 2,
            }, {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-0",
                "type": 'Cost',
                "incoming": 2,
            }, {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-1",
                "type": 'Cost',
                "incoming": 2,
            }, {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-0",
                "type": 'Electric - Grid',
                "incoming": 2,
            }, {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-1",
                "type": 'Natural Gas',
                "incoming": 2,
            },
        ]

        self.assertCountEqual(result_dict.get("proposed_imports"), proposed_imports)

        # Verify this works for Org with CAN thermal conversions
        self.org.thermal_conversion_assumption = Organization.CAN
        self.org.save()

        can_result = self.client.get(url)
        can_result_dict = ast.literal_eval(can_result.content.decode("utf-8"))

        validated_type_units[2] = {
            "parsed_type": "Cost",
            "parsed_unit": "CAN Dollars",
        }

        self.assertCountEqual(can_result_dict.get("validated_type_units"), validated_type_units)

    def test_green_button_parsed_meters_confirmation_returns_a_green_button_id_incoming_counts_and_parsed_type_units_and_saves_property_id_to_file_cache(self):
        filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        xml_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="GreenButton",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

        url = reverse('api:v3:import_files-greenbutton-meters-preview', kwargs={'pk': xml_import_file.id})
        url += f'?organization_id={self.org.pk}&view_id={self.property_view_1.id}'
        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        proposed_imports = [
            {
                "source_id": '409483',
                "property_id": self.property_1.id,
                "type": 'Electric - Grid',
                "incoming": 2,
            },
        ]

        validated_type_units = [
            {
                "parsed_type": "Electric - Grid",
                "parsed_unit": "kWh (thousand Watt-hours)",
            },
        ]

        self.assertEqual(result_dict['proposed_imports'], proposed_imports)
        self.assertEqual(result_dict['validated_type_units'], validated_type_units)

        refreshed_import_file = ImportFile.objects.get(pk=xml_import_file.id)
        self.assertEqual(refreshed_import_file.matching_results_data, {'property_id': self.property_view_1.property_id})

    def test_parsed_meters_confirmation_returns_unlinkable_pm_property_ids(self):
        PropertyState.objects.all().delete()

        url = reverse('api:v3:import_files-pm-meters-preview', kwargs={'pk': self.import_file.id})
        url += f'?organization_id={self.org.pk}'
        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = [
            {
                "portfolio_manager_id": "5766973",
            },
            {
                "portfolio_manager_id": "5766975",
            },
        ]

        self.assertCountEqual(result_dict.get("unlinkable_pm_ids"), expectation)

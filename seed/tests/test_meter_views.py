# !/usr/bin/env python
# encoding: utf-8

import ast
import os
import json

from config.settings.common import TIME_ZONE

from datetime import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils.timezone import (
    get_current_timezone,
    make_aware,
)

from pytz import timezone

from seed.data_importer.models import ImportFile, ImportRecord
from seed.data_importer.tasks import save_raw_data
from seed.data_importer.utils import kbtu_thermal_conversion_factors
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    Meter,
    MeterReading,
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
        url = reverse('api:v2:meters-parsed-meters-confirmation')

        post_params = json.dumps({
            'file_id': self.import_file.id,
            'organization_id': self.org.pk,
        })
        result = self.client.post(url, post_params, content_type="application/json")
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

        url = reverse('api:v2:meters-parsed-meters-confirmation')

        post_params = json.dumps({
            'file_id': import_file_with_invalids.id,
            'organization_id': self.org.pk,
        })
        result = self.client.post(url, post_params, content_type="application/json")
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
        url = reverse('api:v2:meters-parsed-meters-confirmation')

        post_params = json.dumps({
            'file_id': self.import_file.id,
            'organization_id': self.org.pk,
        })
        result = self.client.post(url, post_params, content_type="application/json")
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

        url = reverse('api:v2:meters-parsed-meters-confirmation')

        post_params = json.dumps({
            'file_id': cost_import_file.id,
            'organization_id': self.org.pk,
        })
        result = self.client.post(url, post_params, content_type="application/json")
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

        can_result = self.client.post(url, post_params, content_type="application/json")
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

        url = reverse('api:v2:meters-greenbutton-parsed-meters-confirmation')

        post_params = json.dumps({
            'file_id': xml_import_file.id,
            'organization_id': self.org.pk,
            'view_id': self.property_view_1.id,
        })
        result = self.client.post(url, post_params, content_type="application/json")
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

        url = reverse('api:v2:meters-parsed-meters-confirmation')

        post_params = json.dumps({
            'file_id': self.import_file.id,
            'organization_id': self.org.pk,
        })
        result = self.client.post(url, post_params, content_type="application/json")
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

    def test_property_meters_endpoint_returns_a_list_of_meters_of_a_view(self):
        # add meters and readings to property associated to property_view_1
        save_raw_data(self.import_file.id)

        # create GB gas meter
        meter_details = {
            'source': Meter.GREENBUTTON,
            'source_id': '/v1/User/000/UsagePoint/123fakeID/MeterReading/000',
            'type': Meter.NATURAL_GAS,
            'property_id': self.property_view_1.property.id,
        }
        gb_gas_meter = Meter.objects.create(**meter_details)

        url = reverse('api:v2:meters-property-meters')

        post_params = json.dumps({
            'property_view_id': self.property_view_1.id,
        })

        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = json.loads(result.content)

        electric_meter = Meter.objects.get(property_id=self.property_view_1.property_id, type=Meter.ELECTRICITY_GRID)
        gas_meter = Meter.objects.get(property_id=self.property_view_1.property_id, type=Meter.NATURAL_GAS, source=Meter.PORTFOLIO_MANAGER)
        expectation = [
            {
                'id': electric_meter.id,
                'type': 'Electric - Grid',
                'source': 'PM',
                'source_id': '5766973-0',
                'scenario_id': None,
                'scenario_name': None
            }, {
                'id': gas_meter.id,
                'type': 'Natural Gas',
                'source': 'PM',
                'source_id': '5766973-1',
                'scenario_id': None,
                'scenario_name': None
            }, {
                'id': gb_gas_meter.id,
                'type': 'Natural Gas',
                'source': 'GB',
                'source_id': '123fakeID',
                'scenario_id': None,
                'scenario_name': None
            },
        ]

        self.assertCountEqual(result_dict, expectation)

    def test_property_meter_usage_returns_meter_readings_and_column_defs_given_property_view_and_nondefault_meter_display_org_settings(self):
        # Update settings for display meter units to change it from the default values.
        self.org.display_meter_units['Electric - Grid'] = 'kWh (thousand Watt-hours)'
        self.org.display_meter_units['Natural Gas'] = 'kcf (thousand cubic feet)'
        self.org.save()

        # add meters and readings to property associated to property_view_1
        save_raw_data(self.import_file.id)

        meter_details = {
            'source': Meter.GREENBUTTON,
            'source_id': '/v1/User/000/UsagePoint/123fakeID/MeterReading/000',
            'type': Meter.NATURAL_GAS,
            'property_id': self.property_view_1.property.id,
        }
        gb_gas_meter = Meter.objects.create(**meter_details)

        tz_obj = timezone(TIME_ZONE)
        gb_gas_reading_details = {
            'start_time': make_aware(datetime(2016, 1, 1, 0, 0, 0), timezone=tz_obj),
            'end_time': make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=tz_obj),
            'reading': 1000,
            'source_unit': 'kBtu (thousand Btu)',
            'conversion_factor': 1,
            'meter_id': gb_gas_meter.id,
        }
        MeterReading.objects.create(**gb_gas_reading_details)

        url = reverse('api:v2:meters-property-meter-usage')

        post_params = json.dumps({
            'property_view_id': self.property_view_1.id,
            'interval': 'Exact',
            'excluded_meter_ids': [],
        })
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            'readings': [
                {
                    'start_time': '2016-01-01 00:00:00',
                    'end_time': '2016-02-01 00:00:00',
                    'Electric - Grid - PM - 5766973-0': (597478.9 / 3.41),
                    'Natural Gas - PM - 5766973-1': 576000.2 / 1026,
                    'Natural Gas - GB - 123fakeID': 1000 / 1026,
                },
                {
                    'start_time': '2016-02-01 00:00:00',
                    'end_time': '2016-03-01 00:00:00',
                    'Electric - Grid - PM - 5766973-0': (548603.7 / 3.41),
                    'Natural Gas - PM - 5766973-1': 488000.1 / 1026,
                },
            ],
            'column_defs': [
                {
                    'field': 'start_time',
                    '_filter_type': 'datetime',
                },
                {
                    'field': 'end_time',
                    '_filter_type': 'datetime',
                },
                {
                    'field': 'Electric - Grid - PM - 5766973-0',
                    'displayName': 'Electric - Grid - PM - 5766973-0 (kWh (thousand Watt-hours))',
                    '_filter_type': 'reading',
                },
                {
                    'field': 'Natural Gas - PM - 5766973-1',
                    'displayName': 'Natural Gas - PM - 5766973-1 (kcf (thousand cubic feet))',
                    '_filter_type': 'reading',
                },
                {
                    'field': 'Natural Gas - GB - 123fakeID',
                    'displayName': 'Natural Gas - GB - 123fakeID (kcf (thousand cubic feet))',
                    '_filter_type': 'reading',
                },
            ]
        }

        self.assertCountEqual(result_dict['readings'], expectation['readings'])
        self.assertCountEqual(result_dict['column_defs'], expectation['column_defs'])

    def test_property_meter_usage_returns_meter_readings_and_column_defs_when_cost_meter_included(self):
        filename = "example-pm-monthly-meter-usage-2-cost-meters.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        cost_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

        # add meters and readings to property associated to property_view_1
        save_raw_data(cost_import_file.id)

        url = reverse('api:v2:meters-property-meter-usage')

        post_params = json.dumps({
            'property_view_id': self.property_view_1.id,
            'interval': 'Exact',
            'excluded_meter_ids': [],
        })
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            'readings': [
                {
                    'start_time': '2016-01-01 00:00:00',
                    'end_time': '2016-02-01 00:00:00',
                    'Electric - Grid - PM - 5766973-0': 597478.9 / 3.41,
                    'Cost - PM - 5766973-0': 100,
                    'Natural Gas - PM - 5766973-1': 576000.2,
                    'Cost - PM - 5766973-1': 300,
                },
                {
                    'start_time': '2016-02-01 00:00:00',
                    'end_time': '2016-03-01 00:00:00',
                    'Electric - Grid - PM - 5766973-0': 548603.7 / 3.41,
                    'Cost - PM - 5766973-0': 200,
                    'Natural Gas - PM - 5766973-1': 488000.1,
                    'Cost - PM - 5766973-1': 400,
                },
            ],
            'column_defs': [
                {
                    'field': 'start_time',
                    '_filter_type': 'datetime',
                },
                {
                    'field': 'end_time',
                    '_filter_type': 'datetime',
                },
                {
                    'field': 'Electric - Grid - PM - 5766973-0',
                    'displayName': 'Electric - Grid - PM - 5766973-0 (kWh (thousand Watt-hours))',
                    '_filter_type': 'reading',
                },
                {
                    'field': 'Natural Gas - PM - 5766973-1',
                    'displayName': 'Natural Gas - PM - 5766973-1 (kBtu (thousand Btu))',
                    '_filter_type': 'reading',
                },
                {
                    'field': 'Cost - PM - 5766973-0',
                    'displayName': 'Cost - PM - 5766973-0 (US Dollars)',
                    '_filter_type': 'reading',
                },
                {
                    'field': 'Cost - PM - 5766973-1',
                    'displayName': 'Cost - PM - 5766973-1 (US Dollars)',
                    '_filter_type': 'reading',
                },
            ]
        }

        self.assertCountEqual(result_dict['readings'], expectation['readings'])
        self.assertCountEqual(result_dict['column_defs'], expectation['column_defs'])

    def test_property_meter_usage_returns_meter_readings_according_to_thermal_conversion_preferences_of_an_org_if_applicable_for_display_settings(self):
        # update the org settings thermal preference and display preference
        self.org.thermal_conversion_assumption = Organization.CAN
        self.org.display_meter_units["Diesel"] = "Liters"
        self.org.display_meter_units["Coke"] = "Lbs. (pounds)"
        self.org.save()

        # add meters and readings to property associated to property_view_1
        meter_details = {
            'source': Meter.PORTFOLIO_MANAGER,
            'source_id': '123fakeID',
            'type': Meter.DIESEL,
            'property_id': self.property_view_1.property.id,
        }
        diesel_meter = Meter.objects.create(**meter_details)

        tz_obj = timezone(TIME_ZONE)
        diesel_reading_details = {
            'start_time': make_aware(datetime(2016, 1, 1, 0, 0, 0), timezone=tz_obj),
            'end_time': make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=tz_obj),
            'reading': 10,
            'source_unit': 'kBtu (thousand Btu)',
            'conversion_factor': 1,
            'meter_id': diesel_meter.id,
        }
        MeterReading.objects.create(**diesel_reading_details)

        meter_details['type'] = Meter.COKE
        meter_details['source_id'] = '456fakeID'
        coke_meter = Meter.objects.create(**meter_details)

        coke_reading_details = {
            'start_time': make_aware(datetime(2016, 1, 1, 0, 0, 0), timezone=tz_obj),
            'end_time': make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=tz_obj),
            'reading': 100,
            'source_unit': 'kBtu (thousand Btu)',
            'conversion_factor': 1,
            'meter_id': coke_meter.id,
        }
        MeterReading.objects.create(**coke_reading_details)

        post_params = json.dumps({
            'property_view_id': self.property_view_1.id,
            'interval': 'Exact',
            'excluded_meter_ids': [],
        })

        url = reverse('api:v2:meters-property-meter-usage')
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        display_readings = [
            {
                'start_time': '2016-01-01 00:00:00',
                'end_time': '2016-02-01 00:00:00',
                'Diesel - PM - 123fakeID': 10 / 36.30,
                'Coke - PM - 456fakeID': 100 / 12.39,
            },
        ]

        self.assertCountEqual(result_dict['readings'], display_readings)

    def test_property_meter_usage_can_return_monthly_meter_readings_and_column_defs_with_nondefault_display_setting(self):
        # Update settings for display meter units to change it from the default values.
        self.org.display_meter_units['Electric - Grid'] = 'kWh (thousand Watt-hours)'
        self.org.save()

        # add initial meters and readings
        save_raw_data(self.import_file.id)

        # add additional entries for each initial meter
        tz_obj = timezone(TIME_ZONE)
        for meter in Meter.objects.all():
            # March 2016 reading
            reading_details = {
                'meter_id': meter.id,
                'start_time': make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=tz_obj),
                'end_time': make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=tz_obj),
                'reading': 100,
                'source_unit': 'kBtu (thousand Btu)',
                'conversion_factor': 1
            }
            MeterReading.objects.create(**reading_details)

            # May 2016 reading
            reading_details['start_time'] = make_aware(datetime(2016, 5, 1, 0, 0, 0), timezone=tz_obj)
            reading_details['end_time'] = make_aware(datetime(2016, 6, 1, 0, 0, 0), timezone=tz_obj)
            reading_details['reading'] = 200
            MeterReading.objects.create(**reading_details)

        url = reverse('api:v2:meters-property-meter-usage')

        post_params = json.dumps({
            'property_view_id': self.property_view_1.id,
            'interval': 'Month',
            'excluded_meter_ids': [],
        })
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            'readings': [
                {
                    'month': 'January 2016',
                    'Electric - Grid - PM - 5766973-0': 597478.9 / 3.41,
                    'Natural Gas - PM - 5766973-1': 576000.2,
                },
                {
                    'month': 'February 2016',
                    'Electric - Grid - PM - 5766973-0': 548603.7 / 3.41,
                    'Natural Gas - PM - 5766973-1': 488000.1,
                },
                {
                    'month': 'March 2016',
                    'Electric - Grid - PM - 5766973-0': 100 / 3.41,
                    'Natural Gas - PM - 5766973-1': 100,
                },
                {
                    'month': 'May 2016',
                    'Electric - Grid - PM - 5766973-0': 200 / 3.41,
                    'Natural Gas - PM - 5766973-1': 200,
                },
            ],
            'column_defs': [
                {
                    'field': 'month',
                    '_filter_type': 'datetime',
                },
                {
                    'field': 'Electric - Grid - PM - 5766973-0',
                    'displayName': 'Electric - Grid - PM - 5766973-0 (kWh (thousand Watt-hours))',
                    '_filter_type': 'reading',
                },
                {
                    'field': 'Natural Gas - PM - 5766973-1',
                    'displayName': 'Natural Gas - PM - 5766973-1 (kBtu (thousand Btu))',
                    '_filter_type': 'reading',
                },
            ]
        }

        self.assertCountEqual(result_dict['readings'], expectation['readings'])
        self.assertCountEqual(result_dict['column_defs'], expectation['column_defs'])

    def test_property_meter_usage_can_return_monthly_meter_readings_and_column_defs_for_submonthly_data_with_DST_transitions_and_specific_meters(self):
        # add initial meters and readings
        save_raw_data(self.import_file.id)

        property_1_electric_meter = Meter.objects.get(source_id='5766973-0')
        # add additional sub-montly entries for each initial meter
        tz_obj = timezone(TIME_ZONE)
        for meter in Meter.objects.all():
            # November 2019 reading between DST transition
            reading_details = {
                'meter_id': meter.id,
                'start_time': make_aware(datetime(2019, 11, 3, 1, 59, 59), timezone=tz_obj, is_dst=True),
                'end_time': make_aware(datetime(2019, 11, 3, 1, 59, 59), timezone=tz_obj, is_dst=False),
                'reading': 100,
                'source_unit': 'kBtu (thousand Btu)',
                'conversion_factor': 1
            }
            MeterReading.objects.create(**reading_details)

            # November 2019 reading after DST transition
            reading_details['start_time'] = make_aware(datetime(2019, 11, 3, 2, 0, 0), timezone=tz_obj)
            reading_details['end_time'] = make_aware(datetime(2019, 11, 3, 3, 0, 0), timezone=tz_obj)
            reading_details['reading'] = 200
            MeterReading.objects.create(**reading_details)

            # Create a reading for only one of the meters that will be filtered out completely
            if meter.source_id == property_1_electric_meter.id:
                reading_details['start_time'] = make_aware(datetime(2020, 11, 3, 2, 0, 0), timezone=tz_obj)
                reading_details['end_time'] = make_aware(datetime(2020, 11, 3, 3, 0, 0), timezone=tz_obj)
                reading_details['reading'] = 10000000
                MeterReading.objects.create(**reading_details)

        url = reverse('api:v2:meters-property-meter-usage')

        post_params = json.dumps({
            'property_view_id': self.property_view_1.id,
            'interval': 'Month',
            'excluded_meter_ids': [property_1_electric_meter.id],
        })
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            'readings': [
                {
                    'month': 'January 2016',
                    'Natural Gas - PM - 5766973-1': 576000.2,
                },
                {
                    'month': 'February 2016',
                    'Natural Gas - PM - 5766973-1': 488000.1,
                },
                {
                    'month': 'November 2019',
                    'Natural Gas - PM - 5766973-1': 300,
                },
            ],
            'column_defs': [
                {
                    'field': 'month',
                    '_filter_type': 'datetime',
                },
                {
                    'field': 'Natural Gas - PM - 5766973-1',
                    'displayName': 'Natural Gas - PM - 5766973-1 (kBtu (thousand Btu))',
                    '_filter_type': 'reading',
                },
            ]
        }

        self.assertCountEqual(result_dict['readings'], expectation['readings'])
        self.assertCountEqual(result_dict['column_defs'], expectation['column_defs'])

    def test_property_meter_usage_can_return_monthly_meter_readings_and_column_defs_of_overlapping_submonthly_data_aggregating_monthly_data_to_maximize_total(self):
        # add initial meters and readings
        save_raw_data(self.import_file.id)

        # add additional entries for the Electricity meter
        tz_obj = timezone(TIME_ZONE)
        meter = Meter.objects.get(property_id=self.property_view_1.property.id, type=Meter.type_lookup['Electric - Grid'])
        # 2016 January reading that should override the existing reading
        reading_details = {
            'meter_id': meter.id,
            'start_time': make_aware(datetime(2016, 1, 1, 0, 0, 0), timezone=tz_obj),
            'end_time': make_aware(datetime(2016, 1, 20, 23, 59, 59), timezone=tz_obj),
            'reading': 100000000000000,
            'source_unit': 'kBtu (thousand Btu)',
            'conversion_factor': 1
        }
        MeterReading.objects.create(**reading_details)

        # 2016 January reading that should be ignored
        reading_details['start_time'] = make_aware(datetime(2016, 1, 1, 0, 0, 0), timezone=tz_obj)
        reading_details['end_time'] = make_aware(datetime(2016, 3, 31, 23, 59, 59), timezone=tz_obj)
        reading_details['reading'] = 0.1
        MeterReading.objects.create(**reading_details)

        # Create March 2016 entries having disregarded readings when finding monthly total
        # 1 week - not included in total
        reading_details['start_time'] = make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=tz_obj)
        reading_details['end_time'] = make_aware(datetime(2016, 3, 6, 23, 59, 59), timezone=tz_obj)
        reading_details['reading'] = 1
        MeterReading.objects.create(**reading_details)

        # 1 week - not included in total
        reading_details['start_time'] = make_aware(datetime(2016, 3, 7, 0, 0, 0), timezone=tz_obj)
        reading_details['end_time'] = make_aware(datetime(2016, 3, 13, 23, 59, 59), timezone=tz_obj)
        reading_details['reading'] = 10
        MeterReading.objects.create(**reading_details)

        # 10 days - included in total
        reading_details['start_time'] = make_aware(datetime(2016, 3, 2, 0, 0, 0), timezone=tz_obj)
        reading_details['end_time'] = make_aware(datetime(2016, 3, 11, 23, 59, 59), timezone=tz_obj)
        reading_details['reading'] = 100
        MeterReading.objects.create(**reading_details)

        # 10 days - included in total
        reading_details['start_time'] = make_aware(datetime(2016, 3, 12, 0, 0, 0), timezone=tz_obj)
        reading_details['end_time'] = make_aware(datetime(2016, 3, 21, 23, 59, 59), timezone=tz_obj)
        reading_details['reading'] = 1000
        MeterReading.objects.create(**reading_details)

        # Create April 2016 entries having disregarded readings when finding monthly total
        # 5 days - not included in total
        reading_details['start_time'] = make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=tz_obj)
        reading_details['end_time'] = make_aware(datetime(2016, 4, 4, 23, 59, 59), timezone=tz_obj)
        reading_details['reading'] = 2
        MeterReading.objects.create(**reading_details)

        # 10 days - not included in total
        reading_details['start_time'] = make_aware(datetime(2016, 4, 6, 0, 0, 0), timezone=tz_obj)
        reading_details['end_time'] = make_aware(datetime(2016, 4, 15, 23, 59, 59), timezone=tz_obj)
        reading_details['reading'] = 20
        MeterReading.objects.create(**reading_details)

        # 20 days - included in total
        reading_details['start_time'] = make_aware(datetime(2016, 4, 2, 0, 0, 0), timezone=tz_obj)
        reading_details['end_time'] = make_aware(datetime(2016, 4, 21, 23, 59, 59), timezone=tz_obj)
        reading_details['reading'] = 200
        MeterReading.objects.create(**reading_details)

        url = reverse('api:v2:meters-property-meter-usage')

        post_params = json.dumps({
            'property_view_id': self.property_view_1.id,
            'interval': 'Month',
            'excluded_meter_ids': [],
        })
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            'readings': [
                {
                    'month': 'January 2016',
                    'Electric - Grid - PM - 5766973-0': 100000000000000 / 3.41,
                    'Natural Gas - PM - 5766973-1': 576000.2,
                },
                {
                    'month': 'February 2016',
                    'Electric - Grid - PM - 5766973-0': 548603.7 / 3.41,
                    'Natural Gas - PM - 5766973-1': 488000.1,
                },
                {
                    'month': 'March 2016',
                    'Electric - Grid - PM - 5766973-0': 1100 / 3.41,
                },
                {
                    'month': 'April 2016',
                    'Electric - Grid - PM - 5766973-0': 200 / 3.41,
                },
            ],
            'column_defs': [
                {
                    'field': 'month',
                    '_filter_type': 'datetime',
                },
                {
                    'field': 'Electric - Grid - PM - 5766973-0',
                    'displayName': 'Electric - Grid - PM - 5766973-0 (kWh (thousand Watt-hours))',
                    '_filter_type': 'reading',
                },
                {
                    'field': 'Natural Gas - PM - 5766973-1',
                    'displayName': 'Natural Gas - PM - 5766973-1 (kBtu (thousand Btu))',
                    '_filter_type': 'reading',
                },
            ]
        }

        self.assertCountEqual(result_dict['readings'], expectation['readings'])
        self.assertCountEqual(result_dict['column_defs'], expectation['column_defs'])

    def test_property_meter_usage_can_return_annual_meter_readings_and_column_defs_while_handling_a_nondefault_display_setting(self):
        # Update settings for display meter units to change it from the default values.
        self.org.display_meter_units['Electric - Grid'] = 'kWh (thousand Watt-hours)'
        self.org.save()

        # add initial meters and readings
        save_raw_data(self.import_file.id)

        # add additional 2018 entries for each initial meter
        tz_obj = timezone(TIME_ZONE)
        for meter in Meter.objects.all():
            # March 2018 reading
            reading_details = {
                'meter_id': meter.id,
                'start_time': make_aware(datetime(2018, 3, 1, 0, 0, 0), timezone=tz_obj),
                'end_time': make_aware(datetime(2018, 4, 1, 0, 0, 0), timezone=tz_obj),
                'reading': 100,
                'source_unit': 'kBtu (thousand Btu)',
                'conversion_factor': 1
            }
            MeterReading.objects.create(**reading_details)

            # May 2018 reading
            reading_details['start_time'] = make_aware(datetime(2018, 5, 1, 0, 0, 0), timezone=tz_obj)
            reading_details['end_time'] = make_aware(datetime(2018, 6, 1, 0, 0, 0), timezone=tz_obj)
            reading_details['reading'] = 200
            MeterReading.objects.create(**reading_details)

        url = reverse('api:v2:meters-property-meter-usage')

        post_params = json.dumps({
            'property_view_id': self.property_view_1.id,
            'interval': 'Year',
            'excluded_meter_ids': [],
        })
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            'readings': [
                {
                    'year': 2016,
                    'Electric - Grid - PM - 5766973-0': (597478.9 + 548603.7) / 3.41,
                    'Natural Gas - PM - 5766973-1': 576000.2 + 488000.1,
                },
                {
                    'year': 2018,
                    'Electric - Grid - PM - 5766973-0': (100 + 200) / 3.41,
                    'Natural Gas - PM - 5766973-1': 100 + 200,
                },
            ],
            'column_defs': [
                {
                    'field': 'year',
                    '_filter_type': 'datetime',
                },
                {
                    'field': 'Electric - Grid - PM - 5766973-0',
                    'displayName': 'Electric - Grid - PM - 5766973-0 (kWh (thousand Watt-hours))',
                    '_filter_type': 'reading',
                },
                {
                    'field': 'Natural Gas - PM - 5766973-1',
                    'displayName': 'Natural Gas - PM - 5766973-1 (kBtu (thousand Btu))',
                    '_filter_type': 'reading',
                },
            ]
        }

        self.assertCountEqual(result_dict['readings'], expectation['readings'])
        self.assertCountEqual(result_dict['column_defs'], expectation['column_defs'])


class TestMeterValidTypesUnits(DataMappingBaseTestCase):
    def setUp(self):
        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **self.user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.client.login(**self.user_details)

    def test_view_that_returns_valid_types_and_units_for_meters(self):
        url = reverse('api:v2:meters-valid-types-units')

        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            type: list(units.keys())
            for type, units
            in kbtu_thermal_conversion_factors("US").items()
        }

        self.assertEqual(result_dict, expectation)

# !/usr/bin/env python
# encoding: utf-8


from config.settings.common import TIME_ZONE

from datetime import datetime

from django.test import TestCase
from django.utils.timezone import (
    get_current_timezone,
    make_aware,  # make_aware is used because inconsistencies exist in creating datetime with tzinfo
)

from pytz import timezone

from seed.data_importer.meters_parser import MetersParser
from seed.landing.models import SEEDUser as User
from seed.models import (
    Meter,
    PropertyState,
    PropertyView,
)
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
)
from seed.utils.organizations import create_organization


class MeterUtilTests(TestCase):
    def setUp(self):
        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **self.user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

        property_details = self.property_state_factory.get_details()
        self.pm_property_id = '12345'
        property_details['pm_property_id'] = self.pm_property_id
        property_details['organization_id'] = self.org.id

        state = PropertyState(**property_details)
        state.save()
        self.state = PropertyState.objects.get(pk=state.id)

        self.cycle_factory = FakeCycleFactory(
            organization=self.org, user=self.user
        )
        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=get_current_timezone())
        )

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property = self.property_factory.get_property()

        self.property_view = PropertyView.objects.create(
            property=self.property, cycle=self.cycle, state=self.state
        )

        self.tz_obj = timezone(TIME_ZONE)

    def test_parse_meter_details_splits_monthly_info_into_meter_data_and_readings_even_with_DST_changing(self):
        raw_meters = [
            {
                'Property Id': self.pm_property_id,
                'Property Name': 'EPA Sample Library',
                'Parent Property Id': 'Not Applicable: Standalone Property',
                'Parent Property Name': 'Not Applicable: Standalone Property',
                'Month': 'Mar-16',
                'Electricity Use  (kBtu)': 597478.9,
                'Natural Gas Use  (kBtu)': 576000.2
            }
        ]

        expected = [
            {
                'property_id': self.property.id,
                'source': Meter.PORTFOLIO_MANAGER,
                'source_id': self.pm_property_id,
                'type': Meter.ELECTRICITY,
                'readings': [
                    {
                        'start_time': make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2016, 3, 31, 23, 59, 59), timezone=self.tz_obj),
                        'reading': 597478.9,
                        'source_unit': 'kBtu',
                        'conversion_factor': 1
                    }
                ]
            },
            {
                'property_id': self.property.id,
                'source': Meter.PORTFOLIO_MANAGER,
                'source_id': self.pm_property_id,
                'type': Meter.NATURAL_GAS,
                'readings': [
                    {
                        'start_time': make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2016, 3, 31, 23, 59, 59), timezone=self.tz_obj),
                        'reading': 576000.2,
                        'source_unit': 'kBtu',
                        'conversion_factor': 1
                    }
                ]
            }
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        self.assertEqual(meters_parser.meter_and_reading_objs, expected)

    def test_parse_meter_details_works_with_multiple_meters_impacted_by_a_leap_year(self):
        raw_meters = [
            {
                'Property Id': self.pm_property_id,
                'Month': 'Feb-16',
                'Electricity Use  (kBtu)': 111,
                'Natural Gas Use  (kBtu)': 333
            }, {
                'Property Id': self.pm_property_id,
                'Month': 'Feb-17',
                'Electricity Use  (kBtu)': 222,
                'Natural Gas Use  (kBtu)': 444
            }

        ]

        expected = [
            {
                'property_id': self.property.id,
                'source': Meter.PORTFOLIO_MANAGER,
                'source_id': self.pm_property_id,
                'type': Meter.ELECTRICITY,
                'readings': [
                    {
                        'start_time': make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2016, 2, 29, 23, 59, 59), timezone=self.tz_obj),
                        'reading': 111,
                        'source_unit': 'kBtu',
                        'conversion_factor': 1
                    },
                    {
                        'start_time': make_aware(datetime(2017, 2, 1, 0, 0, 0), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2017, 2, 28, 23, 59, 59), timezone=self.tz_obj),
                        'reading': 222,
                        'source_unit': 'kBtu',
                        'conversion_factor': 1
                    }
                ]
            },
            {
                'property_id': self.property.id,
                'source': Meter.PORTFOLIO_MANAGER,
                'source_id': self.pm_property_id,
                'type': Meter.NATURAL_GAS,
                'readings': [
                    {
                        'start_time': make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2016, 2, 29, 23, 59, 59), timezone=self.tz_obj),
                        'reading': 333,
                        'source_unit': 'kBtu',
                        'conversion_factor': 1
                    },
                    {
                        'start_time': make_aware(datetime(2017, 2, 1, 0, 0, 0), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2017, 2, 28, 23, 59, 59), timezone=self.tz_obj),
                        'reading': 444,
                        'source_unit': 'kBtu',
                        'conversion_factor': 1
                    }
                ]
            }
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        self.assertEqual(meters_parser.meter_and_reading_objs, expected)

    def test_parse_meter_details_converts_energy_units_if_necessary(self):
        raw_meters = [
            {
                'Property Id': self.pm_property_id,
                'Property Name': 'EPA Sample Library',
                'Parent Property Id': 'Not Applicable: Standalone Property',
                'Parent Property Name': 'Not Applicable: Standalone Property',
                'Month': 'Mar-16',
                'Electricity Use  (kWh)': 1000,
                'Fuel Oil (No. 1) Use  (GJ)': 1000
            }
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        result = meters_parser.meter_and_reading_objs

        if result[0]["type"] == Meter.FUEL_OIL_NO_1:
            fuel_oil_details = result[0]
            electricity_details = result[1]
        else:
            fuel_oil_details = result[1]
            electricity_details = result[0]

        self.assertEqual(fuel_oil_details["readings"][0]["reading"], 947817)
        self.assertEqual(fuel_oil_details["readings"][0]["source_unit"], "GJ")
        self.assertEqual(fuel_oil_details["readings"][0]["conversion_factor"], 947.817)
        self.assertEqual(electricity_details["readings"][0]["reading"], 3412)
        self.assertEqual(electricity_details["readings"][0]["source_unit"], "kWh")
        self.assertEqual(electricity_details["readings"][0]["conversion_factor"], 3.412)

    def test_unlinked_properties_are_identified(self):
        raw_meters = [
            {
                'Property Id': "11111111",
                'Property Name': 'EPA Sample Library',
                'Parent Property Id': 'Not Applicable: Standalone Property',
                'Parent Property Name': 'Not Applicable: Standalone Property',
                'Month': 'Mar-16',
                'Electricity Use  (kWh)': 1000,
                'Fuel Oil (No. 1) Use  (GJ)': 1000
            },
            {
                'Property Id': "22222222",
                'Property Name': 'EPA Sample Library',
                'Parent Property Id': 'Not Applicable: Standalone Property',
                'Parent Property Name': 'Not Applicable: Standalone Property',
                'Month': 'Mar-16',
                'Electricity Use  (kBtu)': 597478.9,
                'Natural Gas Use  (kBtu)': 576000.2
            },
            {
                'Property Id': "22222222",
                'Property Name': 'EPA Sample Library',
                'Parent Property Id': 'Not Applicable: Standalone Property',
                'Parent Property Name': 'Not Applicable: Standalone Property',
                'Month': 'Feb-16',
                'Electricity Use  (kBtu)': 597478.9,
                'Natural Gas Use  (kBtu)': 576000.2
            },
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        expected = [
            {'portfolio_manager_id': "11111111"},
            {'portfolio_manager_id': "22222222"},
        ]

        self.assertCountEqual(expected, meters_parser.unlinkable_pm_ids)

        self.assertEqual([], meters_parser.meter_and_reading_objs)

    def test_meters_parser_can_handle_raw_meters_with_start_time_and_duration_involving_DST_change_and_a_leap_year(self):
        raw_meters = [
            {
                'start_time': 1552211999,  # Mar. 10, 2019 01:59:59 (pre-DST change)
                'source_id': 'ABCDEF',
                'duration': 900,
                'Electricity Use  (kBtu)': 100,
                'Natural Gas Use  (GJ)': 100
            },
            {
                'start_time': 1456732799,  # Feb. 28, 2016 23:59:59 (leap year)
                'duration': 900,
                'source_id': 'ABCDEF',
                'Electricity Use  (kBtu)': 1000,
                'Natural Gas Use  (GJ)': 1000
            }
        ]

        expected = [
            {
                'property_id': self.property.id,
                'source': Meter.GREENBUTTON,
                'source_id': 'ABCDEF',
                'type': Meter.ELECTRICITY,
                'readings': [
                    {
                        'start_time': make_aware(datetime(2019, 3, 10, 1, 59, 59), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2019, 3, 10, 3, 14, 59), timezone=self.tz_obj),
                        'reading': 100,
                        'source_unit': 'kBtu',
                        'conversion_factor': 1
                    },
                    {
                        'start_time': make_aware(datetime(2016, 2, 28, 23, 59, 59), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2016, 2, 29, 0, 14, 59), timezone=self.tz_obj),
                        'reading': 1000,
                        'source_unit': 'kBtu',
                        'conversion_factor': 1
                    },
                ]
            },
            {
                'property_id': self.property.id,
                'source': Meter.GREENBUTTON,
                'source_id': 'ABCDEF',
                'type': Meter.NATURAL_GAS,
                'readings': [
                    {
                        'start_time': make_aware(datetime(2019, 3, 10, 1, 59, 59), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2019, 3, 10, 3, 14, 59), timezone=self.tz_obj),
                        'reading': 94781.7,
                        'source_unit': 'GJ',
                        'conversion_factor': 947.817
                    },
                    {
                        'start_time': make_aware(datetime(2016, 2, 28, 23, 59, 59), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2016, 2, 29, 0, 14, 59), timezone=self.tz_obj),
                        'reading': 947817.0,
                        'source_unit': 'GJ',
                        'conversion_factor': 947.817
                    },
                ]
            }
        ]

        meters_parser = MetersParser(self.org.id, raw_meters, source_type="GreenButton", property_id=self.property.id)

        self.assertEqual(meters_parser.meter_and_reading_objs, expected)

"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import locale
from datetime import datetime
from pathlib import Path

from django.test import TestCase
from django.utils.timezone import (
    get_current_timezone,
    make_aware,  # make_aware is used because inconsistencies exist in creating datetime with tzinfo
)
from pytz import timezone

from config.settings.common import TIME_ZONE
from seed.data_importer.meters_parser import MetersParser
from seed.data_importer.utils import kbtu_thermal_conversion_factors
from seed.landing.models import SEEDUser as User
from seed.lib.mcm import reader
from seed.lib.superperms.orgs.models import Organization
from seed.models import Meter, PropertyState, PropertyView
from seed.test_helpers.fake import FakeCycleFactory, FakePropertyFactory, FakePropertyStateFactory
from seed.utils.organizations import create_organization


class ThermalConversionTests(TestCase):
    def test_usa_and_canada_have_the_same_type_unit_combinations(self):
        """
        This was true when Meters features were first developed. Many aspects of
        these features depend on this assumption, so this test was written.
        """

        def valid_type_and_unit_combinations(country):
            return {type: list(unit_factors) for type, unit_factors in kbtu_thermal_conversion_factors(country).items()}

        us_type_units = valid_type_and_unit_combinations("US")
        can_type_units = valid_type_and_unit_combinations("CAN")

        self.assertEqual(us_type_units, can_type_units)


class MeterUtilTests(TestCase):
    def setUp(self):
        self.user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        self.user = User.objects.create_superuser(email="test_user@demo.com", **self.user_details)
        self.org, _, _ = create_organization(self.user)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

        property_details = self.property_state_factory.get_details()
        self.pm_property_id = "12345"
        property_details["pm_property_id"] = self.pm_property_id
        property_details["organization_id"] = self.org.id

        state = PropertyState(**property_details)
        state.save()
        self.state = PropertyState.objects.get(pk=state.id)

        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property = self.property_factory.get_property()

        self.property_view = PropertyView.objects.create(property=self.property, cycle=self.cycle, state=self.state)

        self.tz_obj = timezone(TIME_ZONE)

    def test_parse_meter_preprocess_raw_pm_data_request(self):
        with open(
            Path(__file__).resolve().parent / "data" / "example-pm-data-request-with-meters.xlsx",
            encoding=locale.getpreferredencoding(False),
        ) as meters_file:
            parser = reader.MCMParser(meters_file, sheet_name="Monthly Usage")

        raw_meter_data = MetersParser.preprocess_raw_pm_data_request(parser.data)
        self.assertEqual(
            raw_meter_data,
            [
                {
                    "Start Date": "2016-01-01 00:00:00",
                    "End Date": "2016-02-01 00:00:00",
                    "Portfolio Manager ID": "4544232",
                    "Portfolio Manager Meter ID": "Unknown",
                    "Meter Type": "Electric - Grid",
                    "Usage/Quantity": "85887.1",
                    "Usage Units": "kBtu (thousand Btu)",
                },
                {
                    "Start Date": "2016-02-01 00:00:00",
                    "End Date": "2016-03-01 00:00:00",
                    "Portfolio Manager ID": "4544232",
                    "Portfolio Manager Meter ID": "Unknown",
                    "Meter Type": "Electric - Grid",
                    "Usage/Quantity": "175697.3",
                    "Usage Units": "kBtu (thousand Btu)",
                },
            ],
        )

    def test_parse_meter_preprocess_raw_pm_data_request_new(self):
        with open(
            Path(__file__).resolve().parent / "data" / "example-pm-data-request-with-meters-new-format.xlsx",
            encoding=locale.getpreferredencoding(False),
        ) as meters_file:
            parser = reader.MCMParser(meters_file, sheet_name="Monthly Usage")

        raw_meter_data = MetersParser.preprocess_raw_pm_data_request(parser.data)
        self.assertEqual(
            raw_meter_data,
            [
                {
                    "Start Date": "2016-01-01 00:00:00",
                    "End Date": "2016-02-01 00:00:00",
                    "Portfolio Manager ID": "4544232",
                    "Portfolio Manager Meter ID": "Unknown",
                    "Meter Type": "Electric - Grid",
                    "Usage/Quantity": "85887.1",
                    "Usage Units": "kBtu (thousand Btu)",
                },
                {
                    "Start Date": "2016-02-01 00:00:00",
                    "End Date": "2016-03-01 00:00:00",
                    "Portfolio Manager ID": "4544232",
                    "Portfolio Manager Meter ID": "Unknown",
                    "Meter Type": "Electric - Grid",
                    "Usage/Quantity": "175697.3",
                    "Usage Units": "kBtu (thousand Btu)",
                },
            ],
        )

    def test_parse_meter_details_splits_monthly_info_into_meter_data_and_readings_even_with_dst_changing(self):
        raw_meters = [
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2016-03-01 00:00:00",
                "End Date": "2016-04-01 00:00:00",
                "Meter Type": "Electric - Grid",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 100,
            },
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2016-03-01 00:00:00",
                "End Date": "2016-04-01 00:00:00",
                "Meter Type": "Natural Gas",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 200,
            },
        ]

        expected = [
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID",
                "type": Meter.ELECTRICITY_GRID,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 100,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    }
                ],
            },
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID",
                "type": Meter.NATURAL_GAS,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 200,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    }
                ],
            },
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        self.assertEqual(meters_parser.meter_and_reading_objs, expected)

    def test_parse_meter_details_creates_entries_for_multiple_records_with_same_pm_property_id(self):
        property_details = self.property_state_factory.get_details()
        property_details["pm_property_id"] = self.pm_property_id
        property_details["custom_id_1"] = "Force unmatched"
        property_details["organization_id"] = self.org.id

        state = PropertyState(**property_details)
        state.save()
        state_2 = PropertyState.objects.get(pk=state.id)

        property_2 = self.property_factory.get_property()

        PropertyView.objects.create(property=property_2, cycle=self.cycle, state=state_2)

        raw_meters = [
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2016-03-01 00:00:00",
                "End Date": "2016-04-01 00:00:00",
                "Meter Type": "Electric - Grid",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 100,
            },
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2016-03-01 00:00:00",
                "End Date": "2016-04-01 00:00:00",
                "Meter Type": "Natural Gas",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 200,
            },
        ]

        expected = [
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID",
                "type": Meter.ELECTRICITY_GRID,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 100,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    }
                ],
            },
            {
                "property_id": property_2.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID",
                "type": Meter.ELECTRICITY_GRID,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 100,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    }
                ],
            },
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID",
                "type": Meter.NATURAL_GAS,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 200,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    }
                ],
            },
            {
                "property_id": property_2.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID",
                "type": Meter.NATURAL_GAS,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 200,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    }
                ],
            },
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        meters_parser.meter_and_reading_objs.sort(key=lambda x: (x["readings"][0]["reading"], x["property_id"]))
        self.assertEqual(meters_parser.meter_and_reading_objs, expected)

    def test_parse_meter_details_splits_monthly_info_including_cost_into_meter_data_and_readings(self):
        raw_meters = [
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID-el",
                "Start Date": "2016-03-01 00:00:00",
                "End Date": "2016-04-01 00:00:00",
                "Usage Units": "kBtu (thousand Btu)",
                "Meter Type": "Electric - Grid",
                "Usage/Quantity": 100,
                "Cost ($)": 100,
            },
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID-gas",
                "Start Date": "2016-03-01 00:00:00",
                "End Date": "2016-04-01 00:00:00",
                "Meter Type": "Natural Gas",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 200,
                "Cost ($)": 50,
            },
        ]

        expected = [
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID-el",
                "type": Meter.ELECTRICITY_GRID,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 100,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    }
                ],
            },
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID-el",
                "type": Meter.COST,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 100,
                        "source_unit": "US Dollars",
                        "conversion_factor": 1,
                    }
                ],
            },
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID-gas",
                "type": Meter.NATURAL_GAS,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 200,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    }
                ],
            },
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID-gas",
                "type": Meter.COST,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 50,
                        "source_unit": "US Dollars",
                        "conversion_factor": 1,
                    }
                ],
            },
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        self.assertEqual(meters_parser.meter_and_reading_objs, expected)

    def test_parser_uses_canadian_thermal_conversion_assumptions_if_org_specifies_it(self):
        self.org.thermal_conversion_assumption = Organization.CAN
        self.org.save()

        raw_meters = [
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID-gas",
                "Start Date": "2016-03-01 00:00:00",
                "End Date": "2016-04-01 00:00:00",
                "Meter Type": "Natural Gas",
                "Usage Units": "cm (cubic meters)",
                "Usage/Quantity": 1000,
                "Cost ($)": 100,
            }
        ]

        expected = [
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID-gas",
                "type": Meter.NATURAL_GAS,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 36420.0,
                        "source_unit": "cm (cubic meters)",
                        "conversion_factor": 36.42,
                    }
                ],
            },
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID-gas",
                "type": Meter.COST,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 100,
                        "source_unit": "CAN Dollars",
                        "conversion_factor": 1,
                    }
                ],
            },
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        self.assertEqual(meters_parser.meter_and_reading_objs, expected)

    def test_parse_meter_details_works_with_multiple_meters_impacted_by_a_leap_year(self):
        raw_meters = [
            {"Property Id": self.pm_property_id, "Month": "Feb-16", "Electricity Use  (kBtu)": 111, "Natural Gas Use  (kBtu)": 333},
            {"Property Id": self.pm_property_id, "Month": "Feb-17", "Electricity Use  (kBtu)": 222, "Natural Gas Use  (kBtu)": 444},
        ]
        raw_meters = [
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2016-02-01 00:00:00",
                "End Date": "2016-03-01 00:00:00",
                "Meter Type": "Electric - Grid",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 111,
            },
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2016-02-01 00:00:00",
                "End Date": "2016-03-01 00:00:00",
                "Meter Type": "Natural Gas",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 333,
            },
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2017-02-01 00:00:00",
                "End Date": "2017-03-01 00:00:00",
                "Meter Type": "Electric - Grid",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 222,
            },
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2017-02-01 00:00:00",
                "End Date": "2017-03-01 00:00:00",
                "Meter Type": "Natural Gas",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 444,
            },
        ]

        expected = [
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID",
                "type": Meter.ELECTRICITY_GRID,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 111,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    },
                    {
                        "start_time": make_aware(datetime(2017, 2, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2017, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 222,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    },
                ],
            },
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID",
                "type": Meter.NATURAL_GAS,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 333,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    },
                    {
                        "start_time": make_aware(datetime(2017, 2, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2017, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 444,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    },
                ],
            },
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        self.assertEqual(meters_parser.meter_and_reading_objs, expected)

    def test_parse_meter_details_converts_energy_units_if_necessary(self):
        raw_meters = [
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2016-03-01 00:00:00",
                "End Date": "2016-04-01 00:00:00",
                "Meter Type": "Natural Gas",
                "Usage Units": "ccf (hundred cubic feet)",
                "Usage/Quantity": 1000,
            },
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2016-03-01 00:00:00",
                "End Date": "2016-04-01 00:00:00",
                "Meter Type": "Fuel Oil (No. 1)",
                "Usage Units": "GJ",
                "Usage/Quantity": 1000,
            },
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        result = meters_parser.meter_and_reading_objs

        if result[0]["type"] == Meter.FUEL_OIL_NO_1:
            fuel_oil_details = result[0]
            gas_details = result[1]
        else:
            fuel_oil_details = result[1]
            gas_details = result[0]

        self.assertEqual(fuel_oil_details["readings"][0]["reading"], 947820)
        self.assertEqual(fuel_oil_details["readings"][0]["source_unit"], "GJ")
        self.assertEqual(fuel_oil_details["readings"][0]["conversion_factor"], 947.82)
        self.assertEqual(gas_details["readings"][0]["reading"], 102600)
        self.assertEqual(gas_details["readings"][0]["source_unit"], "ccf (hundred cubic feet)")
        self.assertEqual(gas_details["readings"][0]["conversion_factor"], 102.6)

    def test_unlinked_properties_are_identified(self):
        raw_meters = [
            {
                "Portfolio Manager ID": "11111111",
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2016-03-01 00:00:00",
                "End Date": "2016-04-01 00:00:00",
                "Meter Type": "Electric - Grid",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 100,
            },
            {
                "Portfolio Manager ID": "22222222",
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2016-03-01 00:00:00",
                "End Date": "2016-04-01 00:00:00",
                "Meter Type": "Electric - Grid",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 100,
            },
            {
                "Portfolio Manager ID": "22222222",
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2016-04-01 00:00:00",
                "End Date": "2016-05-01 00:00:00",
                "Meter Type": "Electric - Grid",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 100,
            },
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        expected = [
            {"portfolio_manager_id": "11111111"},
            {"portfolio_manager_id": "22222222"},
        ]

        self.assertCountEqual(expected, meters_parser.unlinkable_pm_ids)

        self.assertEqual([], meters_parser.meter_and_reading_objs)

    def test_meters_parser_can_handle_raw_meters_with_start_time_and_duration_involving_dst_change_and_a_leap_year(self):
        raw_meters = [
            {
                "start_time": 1552211999,  # Mar. 10, 2019 01:59:59 (pre-DST change)
                "source_id": "ABCDEF",
                "duration": 900,
                "Meter Type": "Natural Gas",
                "Usage Units": "GJ",
                "Usage/Quantity": 100,
            },
            {
                "start_time": 1456732799,  # Feb. 28, 2016 23:59:59 (leap year)
                "source_id": "ABCDEF",
                "duration": 900,
                "Meter Type": "Natural Gas",
                "Usage Units": "GJ",
                "Usage/Quantity": 1000,
            },
        ]

        expected = [
            {
                "property_id": self.property.id,
                "source": Meter.GREENBUTTON,
                "source_id": "ABCDEF",
                "type": Meter.NATURAL_GAS,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2019, 3, 10, 1, 59, 59), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2019, 3, 10, 3, 14, 59), timezone=self.tz_obj),
                        "reading": 94782.0,
                        "source_unit": "GJ",
                        "conversion_factor": 947.82,
                    },
                    {
                        "start_time": make_aware(datetime(2016, 2, 28, 23, 59, 59), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 2, 29, 0, 14, 59), timezone=self.tz_obj),
                        "reading": 947820.0,
                        "source_unit": "GJ",
                        "conversion_factor": 947.82,
                    },
                ],
            }
        ]

        meters_parser = MetersParser(self.org.id, raw_meters, source_type=Meter.GREENBUTTON, property_id=self.property.id)

        self.assertEqual(meters_parser.meter_and_reading_objs, expected)

    def test_meters_parser_can_handle_delivered_pm_meters(self):
        raw_meters = [
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "Not Available",
                "End Date": "Not Available",
                "Delivery Date": "2016-03-05 00:00:00",
                "Meter Type": "Electric - Grid",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 100,
            },
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "Not Available",
                "End Date": "Not Available",
                "Delivery Date": "2016-03-01 00:00:00",
                "Meter Type": "Natural Gas",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 200,
            },
        ]

        expected = [
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID",
                "type": Meter.ELECTRICITY_GRID,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 100,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    }
                ],
            },
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID",
                "type": Meter.NATURAL_GAS,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=self.tz_obj),
                        "reading": 200,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    }
                ],
            },
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        self.assertEqual(meters_parser.meter_and_reading_objs, expected)

    def test_meters_parser_can_handle_ambiguous_timestamps(self):
        raw_meters = [
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2022-11-06 01:00:00",
                "End Date": "2022-11-06 01:15:00",
                "Meter Type": "Electric - Grid",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 100,
            }
        ]

        expected = [
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID",
                "type": Meter.ELECTRICITY_GRID,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2022, 11, 6, 1, 0, 0), timezone=self.tz_obj, is_dst=False),
                        "end_time": make_aware(datetime(2022, 11, 6, 1, 15, 0), timezone=self.tz_obj, is_dst=False),
                        "reading": 100,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    }
                ],
            }
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        self.assertEqual(meters_parser.meter_and_reading_objs, expected)

    def test_meters_parser_can_handle_nonexistent_timestamps(self):
        raw_meters = [
            {
                "Portfolio Manager ID": self.pm_property_id,
                "Portfolio Manager Meter ID": "123-PMMeterID",
                "Start Date": "2023-03-12 02:00:00",
                "End Date": "2023-03-12 02:15:00",
                "Meter Type": "Electric - Grid",
                "Usage Units": "kBtu (thousand Btu)",
                "Usage/Quantity": 100,
            }
        ]

        expected = [
            {
                "property_id": self.property.id,
                "source": Meter.PORTFOLIO_MANAGER,
                "source_id": "123-PMMeterID",
                "type": Meter.ELECTRICITY_GRID,
                "readings": [
                    {
                        "start_time": make_aware(datetime(2023, 3, 12, 2, 0, 0), timezone=self.tz_obj, is_dst=True),
                        "end_time": make_aware(datetime(2023, 3, 12, 2, 15, 0), timezone=self.tz_obj, is_dst=True),
                        "reading": 100,
                        "source_unit": "kBtu (thousand Btu)",
                        "conversion_factor": 1,
                    }
                ],
            }
        ]

        meters_parser = MetersParser(self.org.id, raw_meters)

        self.assertEqual(meters_parser.meter_and_reading_objs, expected)

    def test_meters_parser_can_handle_meter_water_units(self):
        raw_meters = []
        raw_meter = {
            "Portfolio Manager ID": self.pm_property_id,
            "Portfolio Manager Meter ID": "1-PMMeterID",
            "Start Date": "2016-02-01 00:00:00",
            "End Date": "2016-03-01 00:00:00",
            "Meter Type": "Potable Indoor",
            "Usage Units": "",
            "Usage/Quantity": 1,
        }

        usage_units = [
            "ccf (hundred cubic feet)",
            "cf (cubic feet)",
            "cGal (hundred gallons) (US)",
            "cGal (hundred gallons) (UK)",
            "cm (cubic meters)",
            "Gallons (US)",
            "Gallons (UK)",
            "kcf (thousand cubic feet)",
            "kcm (thousand cubit meters)",
            "kGal (thousand gallons) (US)",
            "kGal (thousand gallons) (UK)",
            "Liters",
            "Mcf (million cubic feed)",
            "MGal (million gallons) (UK)",
            "MGal (million gallons) (US)",
            # invalid units
            "invalid",
            "ccf",
            "Gallons",
        ]

        for usage_unit in usage_units:
            meter = raw_meter.copy()
            meter["Usage Units"] = usage_unit
            raw_meters.append(meter)

        meters_parser = MetersParser(self.org.id, raw_meters)

        expected_readings = [0.748, 0.00748, 0.1, 0.12, 0.26417, 0.001, 0.0012, 7.480, 264.172, 1, 1.2, 0.000264172, 7480.52, 1000, 1200]
        actual_readings = [reading["reading"] for reading in meters_parser.meter_and_reading_objs[0]["readings"]]

        self.assertEqual(len(actual_readings), 15)

        zipped_readings = zip(actual_readings, expected_readings)
        # round to account for binary nature of floating point
        for readings in zipped_readings:
            self.assertEqual(round(readings[0], 5), round(readings[1], 5))

    def test_meters_parser_ignores_unexpected_meter_water_types(self):
        raw_meters = []
        raw_meter = {
            "Portfolio Manager ID": self.pm_property_id,
            "Portfolio Manager Meter ID": "1-PMMeterID",
            "Start Date": "2016-02-01 00:00:00",
            "End Date": "2016-03-01 00:00:00",
            "Meter Type": "",
            "Usage Units": "kGal (thousand gallons) (US)",
            "Usage/Quantity": 1,
        }

        meter_types = [
            "Potable Indoor",
            "Potable: Mixed Indoor/Outdoor",
            "Potable Outdoor",
            # invalid types
            "Potable Invalid",
            "Other Indoor",
            "Well Water: Indoor",
        ]

        for type in meter_types:
            meter = raw_meter.copy()
            meter["Meter Type"] = type
            raw_meters.append(meter)

        meters_parser = MetersParser(self.org.id, raw_meters)
        actual_readings = meters_parser.meter_and_reading_objs

        self.assertEqual(len(actual_readings), 3)

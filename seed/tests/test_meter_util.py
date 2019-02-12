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
from seed.utils.meter import parse_meter_details
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
                'source': Meter.PROPERTY_MANAGER,
                'source_id': self.pm_property_id,
                'type': Meter.ELECTRICITY,
                'units': Meter.KBTU,
                'readings': [
                    {
                        'start_time': make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2016, 3, 31, 23, 59, 59), timezone=self.tz_obj),
                        'reading': 597478.9
                    }
                ]
            },
            {
                'property_id': self.property.id,
                'source': Meter.PROPERTY_MANAGER,
                'source_id': self.pm_property_id,
                'type': Meter.NATURAL_GAS,
                'units': Meter.KBTU,
                'readings': [
                    {
                        'start_time': make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2016, 3, 31, 23, 59, 59), timezone=self.tz_obj),
                        'reading': 576000.2
                    }
                ]
            }
        ]

        self.assertEqual(parse_meter_details(raw_meters, monthly=True), expected)

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
                'source': Meter.PROPERTY_MANAGER,
                'source_id': self.pm_property_id,
                'type': Meter.ELECTRICITY,
                'units': Meter.KBTU,
                'readings': [
                    {
                        'start_time': make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2016, 2, 29, 23, 59, 59), timezone=self.tz_obj),
                        'reading': 111
                    },
                    {
                        'start_time': make_aware(datetime(2017, 2, 1, 0, 0, 0), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2017, 2, 28, 23, 59, 59), timezone=self.tz_obj),
                        'reading': 222
                    }
                ]
            },
            {
                'property_id': self.property.id,
                'source': Meter.PROPERTY_MANAGER,
                'source_id': self.pm_property_id,
                'type': Meter.NATURAL_GAS,
                'units': Meter.KBTU,
                'readings': [
                    {
                        'start_time': make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2016, 2, 29, 23, 59, 59), timezone=self.tz_obj),
                        'reading': 333
                    },
                    {
                        'start_time': make_aware(datetime(2017, 2, 1, 0, 0, 0), timezone=self.tz_obj),
                        'end_time': make_aware(datetime(2017, 2, 28, 23, 59, 59), timezone=self.tz_obj),
                        'reading': 444
                    }
                ]
            }
        ]

        self.assertEqual(parse_meter_details(raw_meters, monthly=True), expected)

import datetime
import json

from django.test import TestCase
from landing.models import SEEDUser as User

from seed.models import (
    ELECTRICITY, KILOWATT_HOURS, BuildingSnapshot, Meter, TimeSeries
)
from seed.views import meters
from seed.tests.util import FakeRequest

from superperms.orgs.models import Organization


class TestMeterViews(TestCase):

    def setUp(self):
        super(TestMeterViews, self).setUp()
        self.org = Organization.objects.create()
        self.fake_user = User.objects.create(email='a@f.com')
        self.fake_user.active = True
        self.fake_user.save()
        self.org.add_member(self.fake_user)

    def test_get_meters_no_building(self):
        """We throw an error when there's no building id passed in."""
        expected = {"status": "error", "message": "No building id specified"}
        fake_request = FakeRequest(
            {'building_id': None},
            user=self.fake_user,
            method='GET',
            body=json.dumps({'organization_id': self.org.pk})
        )
        resp = meters.get_meters(fake_request)

        self.assertDictEqual(json.loads(resp.content), expected)

    def test_get_meters(self):
        """We get a meter that we saved back."""
        bs = BuildingSnapshot.objects.create()
        bs.super_organization = self.org
        bs.save()

        meter = Meter.objects.create(
            name='tester', energy_type=ELECTRICITY, energy_units=KILOWATT_HOURS
        )
        meter.building_snapshot.add(bs)

        expected = {
            'status': 'success',
            'building_id': bs.pk,
            'meters': [
                {
                    'name': meter.name,
                    'building_snapshot': [bs.pk],
                    'energy_units': KILOWATT_HOURS,
                    'energy_type': ELECTRICITY,
                    'pk': meter.pk,
                    'model': 'seed.meter',
                    'id': meter.pk
                }
            ]
        }

        fake_request = FakeRequest(
            {'building_id': bs.pk},
            user=self.fake_user,
            method='GET',
            body=json.dumps({'organization_id': self.org.pk})
        )

        resp = meters.get_meters(fake_request)

        self.assertDictEqual(json.loads(resp.content), expected)

    def test_add_meter_to_building(self):
        """Add a meter to a building."""
        bs = BuildingSnapshot.objects.create()
        bs.super_organization = self.org
        bs.save()

        fake_request = FakeRequest(
            {},
            user=self.fake_user,
            body=json.dumps({
                'organization_id': self.org.pk,
                'building_id': bs.pk,
                'meter_name': 'Fun',
                'energy_type': 'Electricity',
                'energy_units': 'kWh',
            })
        )

        expected = {'status': 'success'}
        resp = meters.add_meter_to_building(fake_request)

        self.assertDictEqual(json.loads(resp.content), expected)

    def test_get_timeseries(self):
        """We get all the times series for a meter."""
        meter = Meter.objects.create(
            name='test', energy_type=ELECTRICITY, energy_units=KILOWATT_HOURS
        )

        now = datetime.datetime.utcnow()
        for i in range(100):
            TimeSeries.objects.create(
                begin_time=now,
                end_time=now,
                cost=23,
                meter=meter
            )

        fake_request = FakeRequest(
            data={'meter_id': meter.pk},
            method='GET',
            user=self.fake_user,
            body=json.dumps({
                'organization_id': self.org.pk,
            })
        )

        resp = json.loads(meters.get_timeseries(fake_request).content)

        smallest_pk = TimeSeries.objects.all()[0].pk
        self.assertEqual(resp['timeseries'][0]['pk'], smallest_pk)
        self.assertEqual(len(resp['timeseries']), 12)

    def test_get_timeseries_w_offset_and_num(self):
        """"make sure we support offsets and number of results."""
        meter = Meter.objects.create(
            name='test', energy_type=ELECTRICITY, energy_units=KILOWATT_HOURS
        )

        now = datetime.datetime.utcnow()
        for i in range(100):
            TimeSeries.objects.create(
                begin_time=now,
                end_time=now,
                cost=23,
                meter=meter
            )

        fake_request = FakeRequest(
            {'meter_id': meter.pk, 'offset': 20, 'num': '5'},
            method='GET',
            user=self.fake_user,
            body=json.dumps({
                'organization_id': self.org.pk,
            })
        )

        resp = json.loads(meters.get_timeseries(fake_request).content)

        first_timeseries_pk = TimeSeries.objects.all()[0].pk
        # Make sure that our offset worked properly
        self.assertEqual(
            resp['timeseries'][0]['pk'], 20 + first_timeseries_pk
        )
        self.assertEqual(len(resp['timeseries']), 5)

    def test_add_timeseries(self):
        """Adding timeseries works."""
        meter = Meter.objects.create(
            name='test', energy_type=ELECTRICITY, energy_units=KILOWATT_HOURS
        )

        fake_request = FakeRequest(
            method='POST',
            user=self.fake_user,
            body=json.dumps({
                'meter_id': meter.pk,
                'organization_id': self.org.pk,
                'timeseries': [
                    {
                        'begin_time': '2014-07-10T18:14:54.726',
                        'end_time': '2014-07-10T18:14:54.726',
                        'cost': 345,
                        'reading': 23.0,
                    },
                    {
                        'begin_time': '2014-07-09T18:14:54.726',
                        'end_time': '2014-07-09T18:14:54.726',
                        'cost': 33,
                        'reading': 11.0,
                    }

                ]
            })
        )

        self.assertEqual(TimeSeries.objects.all().count(), 0)

        resp = json.loads(meters.add_timeseries(fake_request).content)

        self.assertEqual(resp, {'status': 'success'})
        self.assertEqual(TimeSeries.objects.all().count(), 2)

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    PropertyState,
    Meter,
    TimeSeries,
)
from seed.utils.organizations import create_organization


class TestMeterViewSet(TestCase):
    def setUp(self):
        self.org = Organization.objects.create()
        self.user = User.objects.create_superuser(
            email='test_user@demo.com',
            username='test_user@demo.com',
            password='secret',
        )
        self.org, _, _ = create_organization(self.user, "test-organization-a")
        self.org.add_member(self.user)
        self.cycle = self.org.cycles.first()

        self.maxDiff = None

    def test_get_meters_no_building(self):
        """We throw an error when there's no building id passed in."""
        client = APIClient()
        client.login(username=self.user.username, password='secret')

        url = reverse('api:v2:meters-list')

        expected = {
            "status": "error",
            "message": "No property_view_id specified",
            "meters": []
        }

        resp = client.get(url, {'organization_id': self.org.pk})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertDictEqual(json.loads(resp.content), expected)

    def test_get_meters(self):
        """We get a meter that we saved back that was assigned to a property view"""
        ps = PropertyState.objects.create(organization=self.org)
        property_view = ps.promote(self.cycle)

        meter = Meter.objects.create(
            name='tester',
            energy_type=Meter.ELECTRICITY,
            energy_units=Meter.KILOWATT_HOURS,
            property_view=property_view,
        )

        client = APIClient()
        client.login(username=self.user.username, password='secret')

        url = reverse('api:v2:meters-detail', args=(meter.pk,))
        resp = client.get(url)

        expected = {
            "status": "success",
            "meter": {
                "property_view": property_view.pk,
                "scenario": None,
                "name": "tester",
                "timeseries_count": 0,
                "energy_units": 1,
                "energy_type": 2,
                "pk": meter.pk,
                "model": "seed.meter",
                "id": meter.pk,
            }
        }

        self.assertDictEqual(json.loads(resp.content), expected)

    def test_add_meter_to_property(self):
        """Add a meter to a building."""
        ps = PropertyState.objects.create(organization=self.org)
        pv = ps.promote(self.cycle)

        data = {
            "property_view_id": pv.pk,
            "name": "test meter",
            "energy_type": Meter.NATURAL_GAS,
            "energy_units": Meter.KILOWATT_HOURS
        }

        client = APIClient()
        client.login(username=self.user.username, password='secret')
        url = reverse('api:v2:meters-list') + '?organization_id={}'.format(self.org.pk)
        resp = client.post(url, data)

        expected = {
            "status": "success",
            "meter": {
                "property_view": pv.pk,
                "name": "test meter",
                "energy_units": Meter.KILOWATT_HOURS,
                "energy_type": Meter.NATURAL_GAS,
                "model": "seed.meter",
            }
        }
        self.assertEqual(json.loads(resp.content)['status'], "success")
        self.assertDictContainsSubset(expected['meter'], json.loads(resp.content)['meter'])

    def test_get_timeseries(self):
        """We get all the times series for a meter."""
        meter = Meter.objects.create(
            name='test',
            energy_type=Meter.ELECTRICITY,
            energy_units=Meter.KILOWATT_HOURS
        )

        for i in range(100):
            TimeSeries.objects.create(
                begin_time="2015-01-01T08:00:00.000Z",
                end_time="2015-01-01T08:00:00.000Z",
                reading=23,
                meter=meter
            )

        client = APIClient()
        client.login(username=self.user.username, password='secret')
        url = reverse('api:v2:meters-get-timeseries', args=(meter.pk,))
        resp = client.get(url)

        expected = {
            "begin": "2015-01-01 08:00:00+00:00",
            "end": "2015-01-01 08:00:00+00:00",
            "value": 23.0,
        }

        jdata = json.loads(resp.content)
        self.assertEqual(jdata['status'], "success")
        self.assertEqual(len(jdata['meter']['data']), 100)
        self.assertDictEqual(jdata['meter']['data'][0], expected)

        # Not yet implemented
        # def test_add_timeseries(self):
        #     """Adding time series works."""
        #     meter = Meter.objects.create(
        #         name='test',
        #         energy_type=Meter.ELECTRICITY,
        #         energy_units=Meter.KILOWATT_HOURS
        #     )
        #
        #     client = APIClient()
        #     client.login(username=self.user.username, password='secret')
        #     url = reverse('apiv2:meters-add-timeseries', args=(meter.pk,))
        #
        #     resp = client.post(url)
        #
        #             'timeseries': [
        #                 {
        #                     'begin_time': '2014-07-10T18:14:54.726Z',
        #                     'end_time': '2014-07-10T18:14:54.726Z',
        #                     'cost': 345,
        #                     'reading': 23.0,
        #                 },
        #                 {
        #                     'begin_time': '2014-07-09T18:14:54.726Z',
        #                     'end_time': '2014-07-09T18:14:54.726Z',
        #                     'cost': 33,
        #                     'reading': 11.0,
        #                 }
        #
        #             ]
        #         })
        #     )
        #
        #     self.assertEqual(TimeSeries.objects.all().count(), 0)
        #
        #     resp = json.loads(meters.add_timeseries(fake_request).content)

        #     self.assertEqual(resp, {'status': 'success'})
        #     self.assertEqual(TimeSeries.objects.all().count(), 2)

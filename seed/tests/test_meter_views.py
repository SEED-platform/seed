# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import ast
import copy
import json

from django.urls import reverse

from seed.data_importer.utils import \
    kbtu_thermal_conversion_factors as conversion_factors
from seed.landing.models import SEEDUser as User
from seed.models import Meter, Property
from seed.models.scenarios import Scenario
from seed.test_helpers.fake import FakePropertyViewFactory
from seed.tests.util import AccessLevelBaseTestCase, DeleteModelsTestCase
from seed.utils.organizations import create_organization


class TestMeterValidTypesUnits(DeleteModelsTestCase):
    def setUp(self):
        super().setUp()

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
        url = reverse('api:v3:properties-valid-meter-types-and-units')

        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            type: list(units.keys()) for type, units in conversion_factors("US").items()
        }

        self.assertEqual(result_dict, expectation)


class TestMeterCRUD(DeleteModelsTestCase):
    def setUp(self):
        super().setUp()

        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_user(
            email='test_user@demo.com', **self.user_details
        )

        self.org, _, _ = create_organization(self.user, 'meter crud test org')
        self.client.login(**self.user_details)

        # faker class for properties
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)

        self.their_user = User.objects.create_user(email='not.me@demo.com', username='not.me@demo.com', password='not.me')
        self.their_org, _, _ = create_organization(self.their_user, 'not my org nor user')
        self.their_property_view_factory = FakePropertyViewFactory(organization=self.their_org)

    def test_create_meter(self):
        property_view = self.property_view_factory.get_property_view()
        url = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id}) + "?organization_id=" + str(self.org.id)

        payload = {
            'type': 'Electric - Grid',
            'source': 'GreenButton',
            'source_id': '1234567890',
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertDictContainsSubset(payload, response.data)

        payload = {
            'type': 'Electric - Grid',
            'source': 'GreenButton',
            'source_id': '/v1/User/000/UsagePoint/123fakeID/MeterReading/000',
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # verify that the source_id gets updated when GreenButton
        self.assertEqual(response.data['source_id'], '123fakeID')
        self.assertEqual(response.data['alias'], 'Electric - Grid - GreenButton - 123fakeID')

        payload = {
            'type': 'Natural Gas',
            'source': 'Portfolio Manager',
            'source_id': 'A Custom Source ID',
            'is_virtual': True,
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertDictContainsSubset(payload, response.data)

    def test_create_meter_with_scenario(self):
        property_view = self.property_view_factory.get_property_view()
        url = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id}) + "?organization_id=" + str(self.org.id)

        # create a scenario and test again
        scenario = Scenario.objects.create(
            name='test scenario',
            property_state=property_view.state,
        )

        payload = {
            'type': 'Electric - Grid',
            'source': 'GreenButton',
            'source_id': '1234567890',
            'scenario_id': scenario.pk,
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['source_id'], '1234567890')
        self.assertEqual(response.json()['scenario_id'], scenario.pk)

        # check the scenario for the meter
        scenario = Scenario.objects.get(pk=scenario.pk)
        self.assertEqual(scenario.meter_set.count(), 1)
        self.assertEqual(scenario.meter_set.first().source_id, '1234567890')

    def test_create_meter_with_not_my_scenario(self):
        # verify that the scenario is not returned when not requested

        property_view_theirs = self.their_property_view_factory.get_property_view()
        their_scenario = Scenario.objects.create(
            name='test scenario',
            property_state=property_view_theirs.state,
        )

        property_view = self.property_view_factory.get_property_view()
        url = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id}) + "?organization_id=" + str(self.org.id)

        payload = {
            'type': 'Electric - Grid',
            'source': 'GreenButton',
            'source_id': '1234567890',
            'scenario_id': their_scenario.pk,
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['scenario_id']['status'], 'error')
        self.assertEqual(response.json()['scenario_id']['message'], 'Permission error assigning scenario to meter')

    def test_delete_meter(self):
        # create meter
        property_view = self.property_view_factory.get_property_view()
        url = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id}) + "?organization_id=" + str(self.org.id)
        payload = {
            'type': 'Natural Gas',
            'source': 'Portfolio Manager',
            'source_id': 'A Custom Source ID',
            'is_virtual': True,
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertDictContainsSubset(payload, response.data)

        # verify that there is only 1 meter for property
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        meter_id = response.data[0]['id']
        meter_url = reverse('api:v3:property-meters-detail', kwargs={'property_pk': property_view.id, 'pk': meter_id}) + "?organization_id=" + str(self.org.id)
        response = self.client.delete(meter_url, content_type='application/json')
        self.assertEqual(response.status_code, 204)
        # make sure there are no meters for property
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_update_meter(self):
        # create meter
        property_view = self.property_view_factory.get_property_view()
        url = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id}) + "?organization_id=" + str(self.org.id)
        payload = {
            'type': 'Natural Gas',
            'source': 'Portfolio Manager',
            'source_id': 'A Custom Source ID',
            'is_virtual': False,
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertDictContainsSubset(payload, response.data)

        new_payload = copy.deepcopy(payload)
        new_payload['is_virtual'] = True
        meter_id = response.data['id']
        meter_url = reverse('api:v3:property-meters-detail', kwargs={'property_pk': property_view.id, 'pk': meter_id}) + "?organization_id=" + str(self.org.id)
        response = self.client.put(meter_url, data=json.dumps(new_payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['is_virtual'], True)


class TestMetersPermissions(AccessLevelBaseTestCase, DeleteModelsTestCase):
    def setUp(self):
        super().setUp()

        self.property = self.property_factory.get_property()
        self.property_view = self.property_view_factory.get_property_view(self.property)
        self.meter = Meter.objects.create(property=self.property)

    def test_get_meters_detail_permissions(self):
        meter_url = reverse('api:v3:property-meters-detail', kwargs={'property_pk': self.property_view.id, 'pk': self.meter.id}) + "?organization_id=" + str(self.org.id)

        # root users can see meters in root
        self.login_as_root_member()
        response = self.client.get(meter_url)
        assert response.status_code == 200

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(meter_url)
        assert response.status_code == 404

    def test_get_meters_list_permissions(self):
        meter_url = reverse('api:v3:property-meters-list', kwargs={'property_pk': self.property_view.id}) + "?organization_id=" + str(self.org.id)

        # root users can see meters in root
        self.login_as_root_member()
        response = self.client.get(meter_url)
        assert response.status_code == 200

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(meter_url)
        assert response.status_code == 404

    def test_get_meters_delete_permissions(self):
        meter_url = reverse('api:v3:property-meters-detail', kwargs={'property_pk': self.property_view.id, 'pk': self.meter.id}) + "?organization_id=" + str(self.org.id)

        # child user cannot delte meters in root
        self.login_as_child_member()
        response = self.client.delete(meter_url)
        assert response.status_code == 404

        # root users can
        self.login_as_root_member()
        response = self.client.delete(meter_url)
        assert response.status_code == 204

    def test_create_meter_permisions(self):
        url = reverse('api:v3:property-meters-list', kwargs={'property_pk': self.property_view.id}) + "?organization_id=" + str(self.org.id)
        payload = {'type': 'Electric', 'source': 'Manual Entry', 'source_id': '1234567890'}

        # root users can create meters in root
        self.login_as_root_member()
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 201

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 404

    def test_update_meter_permisions(self):
        url = reverse('api:v3:property-meters-detail', kwargs={'property_pk': self.property_view.id, 'pk': self.meter.id}) + "?organization_id=" + str(self.org.id)
        payload = {'type': 'Electric', 'source': 'Manual Entry', 'source_id': 'boo'}

        # root users can see meters in root
        self.login_as_root_member()
        response = self.client.put(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 200

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 404


class TestMeterReadingCRUD(DeleteModelsTestCase):
    def setUp(self):
        super().setUp()

        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_user(
            email='test_user@demo.com', **self.user_details
        )
        self.org, _, _ = create_organization(self.user, 'meter crud test org')
        self.client.login(**self.user_details)

        # faker class for properties
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)

    def test_create_meter_readings(self):
        property_view = self.property_view_factory.get_property_view()
        url = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id}) + "?organization_id=" + str(self.org.id)

        payload = {
            'type': 'Electric',
            'source': 'Manual Entry',
            'source_id': '1234567890',
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        meter_pk = response.json()['id']

        # create meter readings
        url = reverse('api:v3:property-meter-readings-list', kwargs={'property_pk': property_view.id, 'meter_pk': meter_pk}) + "?organization_id=" + str(self.org.id)

        # write a few values to the database
        for values in [("2022-01-05 05:00:00", "2022-01-05 06:00:00", 6.0),
                       ("2022-01-05 06:00:00", "2022-01-05 07:00:00", 12.0),
                       ("2022-01-05 07:00:00", "2022-01-05 08:00:00", 18.0), ]:
            payload = {
                "start_time": values[0],
                "end_time": values[1],
                "reading": values[2],
                "source_unit": "Wh (Watt-hours)",
                # conversion factor is required and is the conversion from the source unit to kBTU (1 Wh = 0.00341 kBtu)
                "conversion_factor": 0.00341,
            }

            response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()['reading'], values[2])

        # read all the values from the meter and check the results
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)

    def test_create_two_meters_readings(self):
        """Test edge case to make sure that data for two different meters don't overwrite each other"""
        property_view = self.property_view_factory.get_property_view()
        url_meters = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id})
        url_meters += "?organization_id=" + str(self.org.id)

        payload = {
            'type': 'Electric',
            'source': 'Manual Entry',
            'source_id': '1234567890',
        }
        response = self.client.post(url_meters, data=json.dumps(payload), content_type='application/json')
        meter_pk_1 = response.json()['id']

        payload = {
            'type': 'Natural Gas',
            'source': 'Manual Entry',
            'source_id': '9876543210',
        }
        response = self.client.post(url_meters, data=json.dumps(payload), content_type='application/json')
        meter_pk_2 = response.json()['id']

        # create meter readings
        url_1 = reverse('api:v3:property-meter-readings-list', kwargs={'property_pk': property_view.id, 'meter_pk': meter_pk_1})
        url_2 = reverse('api:v3:property-meter-readings-list', kwargs={'property_pk': property_view.id, 'meter_pk': meter_pk_2})

        readings_1 = {
            "start_time": "2022-01-05 05:00:00",
            "end_time": "2022-01-05 06:00:00",
            "reading": 6.0,
            "source_unit": "Wh (Watt-hours)",
            "conversion_factor": 0.00341,
        }
        readings_2 = readings_1.copy()
        readings_2['reading'] = -6.0

        response_1 = self.client.post(url_1, data=json.dumps(readings_1), content_type='application/json')
        response_2 = self.client.post(url_2, data=json.dumps(readings_2), content_type='application/json')
        self.assertEqual(response_1.status_code, 201)
        self.assertEqual(response_2.status_code, 201)

        # check that there are two meters
        url_meters = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id})
        response_meters = self.client.get(url_meters, content_type='application/json')
        self.assertEqual(len(response_meters.json()), 2)

        # read all the values from the meter and check the results
        response_1 = self.client.get(url_1, content_type='application/json')
        response_2 = self.client.get(url_2, content_type='application/json')
        self.assertEqual(response_1.status_code, 200)
        self.assertEqual(response_2.status_code, 200)
        # check that the results are different between the two meters
        self.assertEqual(len(response_1.json()), 1)
        self.assertEqual(len(response_2.json()), 1)
        self.assertEqual(response_1.json()[0]['reading'], 6.0)
        self.assertEqual(response_2.json()[0]['reading'], -6.0)

    def test_create_two_meters_bulk_readings(self):
        """Test edge case to make sure that data for two different meters don't overwrite each other"""
        property_view = self.property_view_factory.get_property_view()
        url_meters = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id})
        url_meters += "?organization_id=" + str(self.org.id)

        payload = {
            'type': 'Electric',
            'source': 'Manual Entry',
            'source_id': '1234567890',
        }
        response = self.client.post(url_meters, data=json.dumps(payload), content_type='application/json')
        meter_pk_1 = response.json()['id']

        payload = {
            'type': 'Natural Gas',
            'source': 'Manual Entry',
            'source_id': '9876543210',
        }
        response = self.client.post(url_meters, data=json.dumps(payload), content_type='application/json')
        meter_pk_2 = response.json()['id']

        # create meter readings
        url_1 = reverse('api:v3:property-meter-readings-list', kwargs={'property_pk': property_view.id, 'meter_pk': meter_pk_1})
        url_2 = reverse('api:v3:property-meter-readings-list', kwargs={'property_pk': property_view.id, 'meter_pk': meter_pk_2})

        # write a few values to the database
        for values in [("2022-01-05 05:00:00", "2022-01-05 06:00:00", 6.0),
                       ("2022-01-05 06:00:00", "2022-01-05 07:00:00", 12.0),
                       ("2022-01-05 07:00:00", "2022-01-05 08:00:00", 18.0), ]:

            payload = {
                "start_time": values[0],
                "end_time": values[1],
                "reading": values[2],
                "source_unit": "Wh (Watt-hours)",
                # conversion factor is required and is the conversion from the source unit to kBTU (1 Wh = 0.00341 kBtu)
                "conversion_factor": 0.00341,
            }

            response = self.client.post(url_1, data=json.dumps(payload), content_type='application/json')
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()['reading'], values[2])
            # for the second readings just negate the reading value
            payload['reading'] = -values[2]
            response = self.client.post(url_2, data=json.dumps(payload), content_type='application/json')
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()['reading'], -values[2])

        # check that there are two meters
        url_meters = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id})
        response_meters = self.client.get(url_meters, content_type='application/json')
        self.assertEqual(len(response_meters.json()), 2)

        # read all the values from the meter and check the results
        response_1 = self.client.get(url_1, content_type='application/json')
        response_2 = self.client.get(url_2, content_type='application/json')
        self.assertEqual(response_1.status_code, 200)
        self.assertEqual(response_2.status_code, 200)
        # check that the results are different between the two meters
        self.assertEqual(len(response_1.json()), 3)
        self.assertEqual(len(response_2.json()), 3)
        self.assertEqual(response_1.json()[0]['reading'], 6.0)
        self.assertEqual(response_2.json()[0]['reading'], -6.0)

    def test_error_with_time_aware(self):
        property_view = self.property_view_factory.get_property_view()
        url = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id}) + "?organization_id=" + str(self.org.id)

        payload = {
            'type': 'Electric',
            'source': 'Manual Entry',
            'source_id': '1234567890',
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        meter_pk = response.json()['id']

        # create meter readings
        url = reverse('api:v3:property-meter-readings-list', kwargs={'property_pk': property_view.id, 'meter_pk': meter_pk}) + "?organization_id=" + str(self.org.id)

        # write a few values to the database
        payload = {
            "start_time": "2023-02-14T22:27:30Z",
            "end_time": "2023-02-14T22:28:30Z",
            "reading": 1000000,
            "source_unit": "Wh (Watt-hours)",
            # conversion factor is required and is the conversion from the source unit to kBTU (1 Wh = 0.00341 kBtu)
            "conversion_factor": 0.00341,
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
        self.assertEqual(response.json()['message'], 'start_time must be non-time zone aware')

        # verify that the end_time also errors
        payload = {
            "start_time": "2023-02-14T22:27:30",
            "end_time": "2023-02-14T22:28:30Z",
            "reading": 1000000,
            "source_unit": "Wh (Watt-hours)",
            # conversion factor is required and is the conversion from the source unit to kBTU (1 Wh = 0.00341 kBtu)
            "conversion_factor": 0.00341,
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
        self.assertEqual(response.json()['message'], 'end_time must be non-time zone aware')

    def test_bulk_import(self):
        # create property
        property_view = self.property_view_factory.get_property_view()
        url = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id}) + "?organization_id=" + str(self.org.id)

        payload = {
            'type': 'Electric',
            'source': 'Manual Entry',
            'source_id': '1234567890',
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        meter_pk = response.json()['id']

        url = reverse('api:v3:property-meter-readings-list', kwargs={'property_pk': property_view.id, 'meter_pk': meter_pk}) + "?organization_id=" + str(self.org.id)

        # prepare the data in bulk format
        payload = []
        for values in [("2022-01-05 05:00:00", "2022-01-05 06:00:00", 22.2),
                       ("2022-01-05 06:00:00", "2022-01-05 07:00:00", 44.4),
                       ("2022-01-05 07:00:00", "2022-01-05 08:00:00", 88.8), ]:
            payload.append({
                "start_time": values[0],
                "end_time": values[1],
                "reading": values[2],
                "source_unit": "Wh (Watt-hours)",
                # conversion factor is required and is the conversion from the source unit to kBTU (1 Wh = 0.00341 kBtu)
                "conversion_factor": 0.00341,
            })

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()[0]['reading'], 22.2)
        self.assertEqual(response.json()[1]['reading'], 44.4)

        # read all the values from the meter and check the results
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)

    def test_delete_meter_readings(self):
        # would be nice nice to make a factory out of the meter / meter reading requests
        property_view = self.property_view_factory.get_property_view()
        url = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id}) + "?organization_id=" + str(self.org.id)

        payload = {
            'type': 'Natural Gas',
            'source': 'Manual Entry',
            'source_id': '9876543210',
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        meter_pk = response.json()['id']

        # create meter reading  property-meter-readings-list
        url = reverse('api:v3:property-meter-readings-list', kwargs={'property_pk': property_view.id, 'meter_pk': meter_pk}) + "?organization_id=" + str(self.org.id)

        payload = {
            "start_time": "2022-01-05 05:00:00",
            "end_time": "2022-01-05 06:00:00",
            "reading": 10,
            "source_unit": "kBtu (Thousand BTU)",
            # conversion factor is required and is the conversion from the source unit to kBTU (1 Wh = 0.00341 kBtu)
            "conversion_factor": 1,
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['reading'], 10)

        # now delete the item and verify that there are no more readings in the database
        detail_url = reverse('api:v3:property-meter-readings-detail', kwargs={'property_pk': property_view.id, 'meter_pk': meter_pk, 'pk': '2022-01-05 05:00:00'})
        response = self.client.get(detail_url, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(detail_url, content_type='application/json')
        self.assertEqual(response.status_code, 204)

        # read all the values from the meter and check the results
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)


class TestMeterReadingPermission(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        self.property = Property.objects.create(organization=self.org, access_level_instance=self.org.root)
        self.view = self.property_view_factory.get_property_view(prprty=self.property)
        self.meter = Meter.objects.create(property=self.property)

    def test_meter_readings_list(self):
        url = (
            reverse('api:v3:property-meters-list', args=[self.view.id]) +
            f'?organization_id={self.org.pk}'
        )

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 404

    def test_meter_readings_get(self):
        url = reverse(
            'api:v3:property-meters-detail',
            kwargs={'property_pk': self.view.id, 'pk': self.meter.id}
        ) + "?organization_id=" + str(self.org.id)

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 404

    def test_meter_readings_update(self):
        url = reverse(
            'api:v3:property-meters-detail',
            kwargs={'property_pk': self.view.id, 'pk': self.meter.id}
        ) + "?organization_id=" + str(self.org.id)
        param = json.dumps({'type': 'Electric', 'source': 'Manual Entry', 'source_id': 'boo'})

        # root member can
        self.login_as_root_member()
        resp = self.client.put(url, param, content_type='application/json')
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.put(url, param, content_type='application/json')
        assert resp.status_code == 404

    def test_meter_readings_create(self):
        url = reverse(
            'api:v3:property-meters-list',
            kwargs={'property_pk': self.view.id}
        ) + "?organization_id=" + str(self.org.id)
        param = json.dumps({'type': 'Electric', 'source': 'Manual Entry', 'source_id': 'boo'})

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, param, content_type='application/json')
        assert resp.status_code == 201

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, param, content_type='application/json')
        assert resp.status_code == 404

    def test_meter_readings_delete(self):
        url = reverse(
            'api:v3:property-meters-detail',
            kwargs={'property_pk': self.view.id, 'pk': self.meter.id}
        ) + "?organization_id=" + str(self.org.id)

        # child member cannot
        self.login_as_child_member()
        resp = self.client.delete(url, content_type='application/json')
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.delete(url, content_type='application/json')
        assert resp.status_code == 204

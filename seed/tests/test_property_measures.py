# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import base64
import json

from django.urls import reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.models import Measure, PropertyMeasure, Scenario
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakePropertyViewFactory
)
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization


class TestPropertyMeasures(DeleteModelsTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.user.generate_key()
        self.org, _, _ = create_organization(self.user)

        auth_string = base64.urlsafe_b64encode(bytes(
            '{}:{}'.format(self.user.username, self.user.api_key), 'utf-8'
        ))
        self.auth_string = 'Basic {}'.format(auth_string.decode('utf-8'))
        self.headers = {'Authorization': self.auth_string}

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org, user=self.user)

    def test_get_property_measure(self):
        """
        Test PropertyMeasure view can retrieve all or individual PropertyMeasure model instances
        """
        property_view = self.property_view_factory.get_property_view()
        property_state = property_view.state
        measures = Measure.objects.all()
        scenario0 = Scenario.objects.create(property_state=property_state, name='scenario 0')
        scenario1 = Scenario.objects.create(property_state=property_state, name='scenario 1')

        property_measure0 = PropertyMeasure.objects.create(
            measure=measures[0],
            property_state=property_state,
            description="Property Measure 0"
        )
        property_measure1 = PropertyMeasure.objects.create(
            measure=measures[1],
            property_state=property_state,
            description="Property Measure 1"
        )
        property_measure2 = PropertyMeasure.objects.create(
            measure=measures[2],
            property_state=property_state,
            description="Property Measure 2"
        )
        property_measure3 = PropertyMeasure.objects.create(
            measure=measures[3],
            property_state=property_state,
            description="Property Measure 3"
        )

        property_measure0.scenario_set.add(scenario0.id)
        property_measure1.scenario_set.add(scenario0.id)
        property_measure2.scenario_set.add(scenario1.id)
        property_measure3.scenario_set.add(scenario1.id)

        url = reverse_lazy(
            'api:v3:property-measures-list',
            args=[property_view.id, 1234567]
        )
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['message'], "No Measures found for given pks")
        self.assertEqual(response.json()['status'], 'error')

        url = reverse_lazy(
            'api:v3:property-measures-list',
            args=[property_view.id, scenario0.id]
        )
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        data = response.json()['data']
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['description'], "Property Measure 0")
        self.assertEqual(data[1]['description'], "Property Measure 1")

        url = reverse_lazy(
            'api:v3:property-measures-list',
            args=[property_view.id, scenario1.id]
        )
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        data = response.json()['data']
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['description'], "Property Measure 2")
        self.assertEqual(data[1]['description'], "Property Measure 3")

        url = reverse_lazy(
            'api:v3:property-measures-detail',
            args=[property_view.id, scenario1.id, property_measure2.id]
        )
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertEqual(response.json()['data']['description'], "Property Measure 2")

        url = reverse_lazy(
            'api:v3:property-measures-detail',
            args=[property_view.id, scenario1.id, 1234]
        )
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['status'], 'error')
        self.assertEqual(response.json()['message'], "No Measure found for given pks")

    def test_update_property_measure(self):
        """
        Test PropertyMeasure view can update a PropertyMeasure model instances
        """
        property_view = self.property_view_factory.get_property_view()
        property_state = property_view.state
        measures = Measure.objects.all()
        scenario0 = Scenario.objects.create(property_state=property_state, name='scenario 0')
        property_measure0 = PropertyMeasure.objects.create(
            measure=measures[0],
            property_state=property_state,
            description="Property Measure 0",
            implementation_status=1
        )
        property_measure1 = PropertyMeasure.objects.create(
            measure=measures[1],
            property_state=property_state,
            description="Property Measure 1",
            implementation_status=1
        )
        property_measure0.scenario_set.add(scenario0.id)
        property_measure1.scenario_set.add(scenario0.id)

        property_measure_fields = {
            'description': 'updated desc',
            'implementation_status': 7
        }

        url = reverse_lazy(
            'api:v3:property-measures-detail',
            args=[property_view.id, scenario0.id, property_measure1.id]
        )

        response = self.client.put(
            url,
            data=json.dumps(property_measure_fields),
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        data = response.json()['data']
        self.assertEqual(data['description'], 'updated desc')
        self.assertEqual(data['implementation_status'], "Completed")

        property_measure0 = PropertyMeasure.objects.get(pk=property_measure0.id)
        property_measure1 = PropertyMeasure.objects.get(pk=property_measure1.id)

        self.assertEqual(property_measure0.implementation_status, 1)
        self.assertEqual(property_measure1.implementation_status, 7)

    def test_fail_to_update_property_measure_with_invalid_data(self):
        """
        Test Failure modes when property measure is updated with invalid data
        """
        property_view = self.property_view_factory.get_property_view()
        property_state = property_view.state
        measures = Measure.objects.all()
        scenario0 = Scenario.objects.create(property_state=property_state, name='scenario 0')
        property_measure0 = PropertyMeasure.objects.create(
            measure=measures[0],
            property_state=property_state,
            description="Property Measure 0",
            implementation_status=1
        )
        property_measure0.scenario_set.add(scenario0.id)
        # Invalid Field Name
        property_measure_fields = {
            'description': 'updated desc',
            'invalid_field': 123
        }

        url = reverse_lazy(
            'api:v3:property-measures-detail',
            args=[property_view.id, scenario0.id, property_measure0.id]
        )

        response = self.client.put(
            url,
            data=json.dumps(property_measure_fields),
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
        self.assertEqual(response.json()['message'], '"invalid_field" is not a valid property measure field')

        property_measure_fields = {
            'description': 'updated desc',
        }
        # Invalid Property Measure ID
        url = reverse_lazy(
            'api:v3:property-measures-detail',
            args=[property_view.id, scenario0.id, 99999]
        )

        response = self.client.put(
            url,
            data=json.dumps(property_measure_fields),
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['status'], 'error')
        self.assertEqual(response.json()['message'], 'No Property Measure found with given pks')

        url = reverse_lazy(
            'api:v3:property-measures-detail',
            args=[9999, scenario0.id, property_measure0.id]
        )

        response = self.client.put(
            url,
            data=json.dumps(property_measure_fields),
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['status'], 'error')
        self.assertEqual(response.json()['message'], 'No Property Measure found with given pks')

    def test_delete_property_measure(self):
        """
        Test views ability to delete the model
        """
        property_view = self.property_view_factory.get_property_view()
        property_state = property_view.state
        measures = Measure.objects.all()
        scenario = Scenario.objects.create(property_state=property_state)
        property_measure0 = PropertyMeasure.objects.create(
            measure=measures[0],
            property_state=property_state,
            description="Property Measure 0"
        )
        property_measure1 = PropertyMeasure.objects.create(
            measure=measures[1],
            property_state=property_state,
            description="Property Measure 1"
        )
        property_measure0.scenario_set.add(scenario.id)
        property_measure1.scenario_set.add(scenario.id)

        self.assertEqual(PropertyMeasure.objects.count(), 2)

        response = self.client.delete(
            reverse_lazy('api:v3:property-measures-detail', args=[property_view.id, scenario.id, property_measure0.id]),
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertEqual(response.json()['message'], 'Successfully Deleted Property Measure')
        self.assertEqual(PropertyMeasure.objects.count(), 1)

        response = self.client.delete(
            reverse_lazy('api:v3:property-measures-detail', args=[property_view.id, scenario.id, 9999]),
            **self.headers
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['status'], 'error')
        self.assertEqual(response.json()['message'], 'No Property Measure found with given pks')

# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
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
from seed.tests.util import AccessLevelBaseTestCase, DeleteModelsTestCase
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
        ) + f"?organization_id={self.org.id}"
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        data = response.json()['data']
        self.assertEqual(len(data), 0)

        url = reverse_lazy(
            'api:v3:property-measures-list',
            args=[property_view.id, scenario0.id]
        ) + f"?organization_id={self.org.id}"
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
        ) + f"?organization_id={self.org.id}"
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
        ) + f"?organization_id={self.org.id}"
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertEqual(response.json()['data']['description'], "Property Measure 2")

        url = reverse_lazy(
            'api:v3:property-measures-detail',
            args=[property_view.id, scenario1.id, 1234]
        ) + f"?organization_id={self.org.id}"
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
        ) + f"?organization_id={self.org.id}"

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
        ) + f"?organization_id={self.org.id}"

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
        ) + f"?organization_id={self.org.id}"

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
        ) + f"?organization_id={self.org.id}"

        response = self.client.put(
            url,
            data=json.dumps(property_measure_fields),
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['status'], 'error')
        self.assertEqual(response.json()['message'], 'No such resource.')

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
            reverse_lazy(
                'api:v3:property-measures-detail',
                args=[property_view.id, scenario.id, property_measure0.id]
            ) + f"?organization_id={self.org.id}",
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertEqual(response.json()['message'], 'Successfully Deleted Property Measure')
        self.assertEqual(PropertyMeasure.objects.count(), 1)

        response = self.client.delete(
            reverse_lazy(
                'api:v3:property-measures-detail', args=[property_view.id, scenario.id, 9999]
            ) + f"?organization_id={self.org.id}",
            **self.headers
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['status'], 'error')
        self.assertEqual(response.json()['message'], 'No Property Measure found with given pks')


class TestPropertyMeasuresPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.property_view = self.property_view_factory.get_property_view()
        self.property_state = self.property_view.state
        self.scenario = Scenario.objects.create(property_state=self.property_state, name='scenario')
        self.measures = Measure.objects.all()
        self.property_measure = PropertyMeasure.objects.create(
            measure=self.measures[5],
            property_state=self.property_state,
            description="Property Measure"
        )
        self.property_measure.scenario_set.add(self.scenario.id)

    def test_measures_list(self):
        url = reverse_lazy(
            'api:v3:property-measures-list',
            args=[self.property_view.id, self.scenario.id]
        ) + f"?organization_id={self.org.id}"

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 200

    def test_measures_get(self):
        url = reverse_lazy(
            'api:v3:property-measures-detail',
            args=[self.property_view.id, self.scenario.id, self.property_measure.id]
        ) + f"?organization_id={self.org.id}"

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 200

    def test_measures_edit(self):
        url = reverse_lazy(
            'api:v3:property-measures-detail',
            args=[self.property_view.id, self.scenario.id, self.property_measure.id]
        ) + f"?organization_id={self.org.id}"
        body = json.dumps({'description': 'updated desc', 'implementation_status': 7})

        # child member cannot
        self.login_as_child_member()
        resp = self.client.put(url, body, content_type='application/json')
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.put(url, body, content_type='application/json')
        assert resp.status_code == 200

    def test_measures_delete(self):
        url = reverse_lazy(
            'api:v3:property-measures-detail',
            args=[self.property_view.id, self.scenario.id, self.property_measure.id]
        ) + f"?organization_id={self.org.id}"

        # child member cannot
        self.login_as_child_member()
        resp = self.client.delete(url, content_type='application/json')
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.delete(url, content_type='application/json')
        assert resp.status_code == 200

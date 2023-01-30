# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import base64
import json
from django.utils.dateparse import parse_datetime

from seed.landing.models import SEEDUser as User
from seed.models import PropertyView, PropertyMeasure, Measure, Column, PropertyState
from seed.test_helpers.fake import (
    FakePropertyMeasureFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization
from django.urls import NoReverseMatch, reverse_lazy
from django.test import TestCase




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

    def test_get_propery_measure(self):
        """
        Test PropertyMeasure view can retrieve all or individual ProperyMeasure model instances
        """
        property_view = self.property_view_factory.get_property_view()
        property_state = property_view.state
        measures = Measure.objects.all()
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

        self.assertEqual(PropertyMeasure.objects.count(), 2)

        response = self.client.get(
            reverse_lazy(
                'api:v3:property-measures-list', 
                args=[property_view.id]
            ),
            **self.headers
        )

        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0].get('description'), "Property Measure 0")
        self.assertEqual(data[1].get('description'), "Property Measure 1")

        response0 = self.client.get(
            reverse_lazy(
                'api:v3:property-measures-detail', 
                args=[property_view.id, property_measure0.id]
            ),
            **self.headers
        )
        response1 = self.client.get(
            reverse_lazy(
                'api:v3:property-measures-detail', 
                args=[property_view.id, property_measure1.id]
            ),
            **self.headers
        )
        response2 = self.client.get(
            reverse_lazy(
                'api:v3:property-measures-detail', 
                args=[property_view.id, 999999]
            ),
            **self.headers
        )

        self.assertEqual(response0.status_code, 200)
        self.assertEqual(response0.json()['description'], 'Property Measure 0' )
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1.json()['description'], 'Property Measure 1' )
        self.assertEqual(response2.status_code, 404)


    # def test_create_property_measure(self):
    #     """
    #     Test PropertyMeasure view's ability to create new PropertyMeasure model instances
    #     """
    #     property_view = self.property_view_factory.get_property_view()
    #     property_state = property_view.state
    #     measures = Measure.objects.all()


    #     post_params = {
    #         # "description": "PropertyMeasure create",
    #         "implementation_status": 'Proposed',
    #         "application_scale": 'Multiple systems',
    #         "category_affected": 'Lighting',
    #         "measure_id": "water_and_sewer_conservation_systems.upgrade_operating_protocols_calibration_and_or_sequencing",
    #         "property_state_id": property_state.id,
    #     }
    #     url = reverse_lazy('api:v3:property-measures-list', args=[property_view.id])

    #     x = self.client.post(
    #         url,
    #         content_type='application/json',
    #         data=json.dumps(post_params),
    #         **self.headers
    #     )


    #     breakpoint()

    def test_delete_property_measure(self):
        """
        Test views ability to delete the model
        """
        property_view = self.property_view_factory.get_property_view()
        property_state = property_view.state
        measures = Measure.objects.all()
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

        self.assertEqual(PropertyMeasure.objects.count(), 2)

        response = self.client.delete(
            reverse_lazy('api:v3:property-measures-detail', args=[property_view.id, property_measure0.id]),
            **self.headers
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(PropertyMeasure.objects.count(), 1)

    def test_update_property_measure(self):
        self.assertEqual(1,1)

        property_view = self.property_view_factory.get_property_view()
        property_state = property_view.state
        measures = Measure.objects.all()
        property_measure = PropertyMeasure.objects.create(
            measure=measures[0],
            property_state=property_state,
            description="Property Measure 0"
        )

        response = self.client.get(
            reverse_lazy(
                'api:v3:property-measures-detail', 
                args=[property_view.id, property_measure.id]
            ),
            **self.headers
        )

        self.assertEqual(response.json()['description'], "Property Measure 0")

        url = reverse_lazy('api:v3:property-measures-detail', args=[property_view.id, property_measure.id])
        put_params = json.dumps({
            "description": "updated description",
            "implementation_status": 'Proposed',
            "application_scale": 'Multiple systems',
            "category_affected": 'Lighting',
        })

        response = self.client.put(
            url, 
            data=put_params,
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["description"], "updated description")
        self.assertEqual(data["implementation_status"], "Proposed")
        self.assertEqual(data["application_scale"], "Multiple systems")
        self.assertEqual(data["category_affected"], "Lighting")

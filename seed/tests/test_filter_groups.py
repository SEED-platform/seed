# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

import base64
import json

from django.test import TransactionTestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.models import FilterGroup, StatusLabel
from seed.utils.organizations import create_organization


class FilterGroupsTests(TransactionTestCase):

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',  # the username needs to be in the form of an email.
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Jaqen',
            'last_name': 'H\'ghar'
        }
        self.user = User.objects.create_user(**user_details)
        self.user.generate_key()
        self.org, _, _ = create_organization(self.user)

        auth_string = base64.urlsafe_b64encode(bytes(
            '{}:{}'.format(self.user.username, self.user.api_key), 'utf-8'
        ))
        self.auth_string = 'Basic {}'.format(auth_string.decode('utf-8'))
        self.headers = {'Authorization': self.auth_string}

        self.status_label = StatusLabel.objects.create(
            name='test', super_organization=self.org
        )

    def test_create_filter_group(self):
        # Action
        response = self.client.post(
            reverse('api:v3:filter_groups-list'),
            data=json.dumps({
                "name": "test_filter_group",
                "inventory_type": "Tax Lot",
                "query_dict": {},
                "label_logic": "exclude",
                "labels": [self.status_label.id]
            }),
            content_type='application/json',
            **self.headers,
        )

        # Assertion
        self.assertEqual(201, response.status_code)
        self.assertEqual(response.json()["status"], 'success')

        data = response.json()["data"]
        self.assertIsInstance(data["id"], int)
        self.assertEqual("test_filter_group", data["name"])
        self.assertEqual(self.org.id, data["organization_id"])
        self.assertEqual("Tax Lot", data["inventory_type"])
        self.assertEqual({}, data["query_dict"])
        self.assertEqual("exclude", data["label_logic"])
        self.assertEqual([self.status_label.id], data["labels"])

    def test_create_filter_group_no_name(self):
        # Action
        response = self.client.post(
            reverse('api:v3:filter_groups-list'),
            data=json.dumps({
                "inventory_type": "Tax Lot",
                "query_dict": {},
            }),
            content_type='application/json',
            **self.headers,
        )

        # Assertion
        self.assertEqual(400, response.status_code)

    def test_create_filter_group_bad_name(self):
        # Setup
        FilterGroup.objects.create(
            name="taken name",
            organization_id=self.org.id,
            inventory_type=1,  # Tax Lot
            query_dict={},
        )

        # Action
        response = self.client.post(
            reverse('api:v3:filter_groups-list'),
            data=json.dumps({
                "name": "taken name",
                "inventory_type": "Tax Lot",
                "query_dict": {},
            }),
            content_type='application/json',
            **self.headers,
        )

        # Assertion
        self.assertEqual(400, response.status_code)

    def test_create_filter_group_no_inventory_type(self):
        # Action
        response = self.client.post(
            reverse('api:v3:filter_groups-list'),
            data=json.dumps({
                "name": "test_filter_group",
                "query_dict": {},
            }),
            content_type='application/json',
            **self.headers,
        )

        # Assertion
        self.assertEqual(400, response.status_code)

    def test_create_filter_group_bad_inventory_type(self):
        # Action
        response = self.client.post(
            reverse('api:v3:filter_groups-list'),
            data=json.dumps({
                "name": "test_filter_group",
                "inventory_type": "bad inventory type",
                "query_dict": {},
            }),
            content_type='application/json',
            **self.headers,
        )

        # Assertion
        self.assertEqual(400, response.status_code)

    def test_create_filter_group_bad_label_logic(self):
        # Action
        response = self.client.post(
            reverse('api:v3:filter_groups-list'),
            data=json.dumps({
                "name": "test_filter_group",
                "inventory_type": "Tax Lot",
                "query_dict": {},
                "label_logic": "bad label logic",
            }),
            content_type='application/json',
            **self.headers,
        )

        # Assertion
        self.assertEqual(400, response.status_code)

    def test_create_filter_group_label_doesnt_exist(self):
        # Action
        response = self.client.post(
            reverse('api:v3:filter_groups-list'),
            data=json.dumps({
                "name": "test_filter_group",
                "inventory_type": "Tax Lot",
                "labels": [-1, -2, self.status_label.id]
            }),
            content_type='application/json',
            **self.headers,
        )

        # Assertion
        self.assertEqual(201, response.status_code)
        self.assertEqual(response.json()["status"], 'success')
        self.assertEqual(response.json()["warnings"], 'labels with ids do not exist: -1, -2')

        data = response.json()["data"]
        self.assertEqual([self.status_label.id], data["labels"])

    def test_get_filter_group(self):
        # Setup
        filter_group = FilterGroup.objects.create(
            name="test_filter_group",
            organization_id=self.org.id,
            inventory_type=1,  # Tax Lot
            query_dict={},
        )
        filter_group.save()

        # Action
        response = self.client.get(
            reverse('api:v3:filter_groups-detail', args=[filter_group.id]),
            **self.headers
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                'status': 'success',
                'data': {
                    "id": filter_group.id,
                    "name": "test_filter_group",
                    "organization_id": self.org.id,
                    "inventory_type": "Tax Lot",
                    "query_dict": {},
                    "labels": [],
                    "label_logic": "and",
                }
            },
            response.json(),
        )

    def test_get_all_filter_group(self):
        # Setup
        filter_group = FilterGroup.objects.create(
            name="test_filter_group",
            organization_id=self.org.id,
            inventory_type=1,  # Tax Lot
            query_dict={},
        )
        second_filter_group = FilterGroup.objects.create(
            name="second_test_filter_group",
            organization_id=self.org.id,
            inventory_type=0,  # Property
            query_dict={},
        )

        # Action
        response = self.client.get(
            reverse('api:v3:filter_groups-list'),
            **self.headers
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                'data': [
                    {
                        'id': filter_group.id,
                        'inventory_type': 'Tax Lot',
                        'name': 'test_filter_group',
                        'organization_id': self.org.id,
                        'query_dict': {},
                        "labels": [],
                        "label_logic": "and",
                    },
                    {
                        'id': second_filter_group.id,
                        'inventory_type': 'Property',
                        'name': 'second_test_filter_group',
                        'organization_id': self.org.id,
                        'query_dict': {},
                        "labels": [],
                        "label_logic": "and",
                    }
                ],
                'pagination': {
                    'end': 2,
                    'has_next': False,
                    'has_previous': False,
                    'num_pages': 1,
                    'page': 1,
                    'start': 1,
                    'total': 2
                },
                'status': 'success'
            },
            response.json(),
        )

    def test_delete_filter_group(self):
        # Setup
        filter_group = FilterGroup.objects.create(
            name="test_filter_group",
            organization_id=self.org.id,
            inventory_type=1,  # Tax Lot
            query_dict={},
        )

        filter_group_id = filter_group.id

        # Action
        response = self.client.delete(
            reverse('api:v3:filter_groups-detail', args=[filter_group_id]),
            **self.headers
        )

        # Assertion
        self.assertEqual(204, response.status_code)
        result = FilterGroup.objects.filter(id=filter_group_id)
        self.assertFalse(result.exists())

    def test_delete_filter_group_does_not_exist(self):
        # Action
        response = self.client.delete(
            reverse('api:v3:filter_groups-detail', args=['not_a_valid_id']),
            **self.headers
        )

        # Assertion
        self.assertEqual(404, response.status_code)

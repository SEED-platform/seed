# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.urls import reverse
from rest_framework import status

from seed.landing.models import SEEDUser as User
from seed.models import (
    Column,
)
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization


class ColumnListSettingsView(DeleteModelsTestCase):
    """
    Tests of the SEED default custom saved columns
    """

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user, "test-organization-a")

        self.column_1 = Column.objects.get(organization=self.org, table_name='PropertyState',
                                           column_name='address_line_1')
        self.column_2 = Column.objects.get(organization=self.org, table_name='PropertyState',
                                           column_name='city')
        self.column_3 = Column.objects.create(organization=self.org, table_name='PropertyState',
                                              column_name='extra data 1', is_extra_data=True)
        self.payload_data = {
            "name": "Test Column List Setting",
            "settings_location": "List View Settings",
            "inventory_type": "Property",
            "columns": [
                {"id": self.column_1.id, "pinned": False, "order": 1},
                {"id": self.column_2.id, "pinned": False, "order": 2},
                {"id": self.column_3.id, "pinned": True, "order": 3},
            ]
        }
        self.client.login(**user_details)

    def test_create_column_settings(self):
        response = self.client.post(
            reverse('api:v2:column_list_settings-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps(self.payload_data),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['data']['columns']), 3)
        self.assertEqual(data['data']['inventory_type'], 'Property')
        self.assertEqual(data['data']['settings_location'], 'List View Settings')

    def test_get_column_settings(self):
        # Create two list settings
        self.client.post(
            reverse('api:v2:column_list_settings-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps(self.payload_data),
            content_type='application/json'
        )
        self.client.post(
            reverse('api:v2:column_list_settings-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps(self.payload_data),
            content_type='application/json'
        )

        response = self.client.get(
            reverse('api:v2:column_list_settings-list') + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)
        self.assertEqual(len(data['data']), 2)

        # test getting a single one
        id = data['data'][0]['id']
        response = self.client.get(
            reverse('api:v2:column_list_settings-detail', args=[id]) + '?organization_id=' + str(
                self.org.id)
        )
        data = json.loads(response.content)
        self.assertEqual(data['data']['id'], id)
        self.assertEqual(len(data['data']['columns']), 3)

    def test_delete_column_settings(self):
        # Create two list settings
        to_delete = self.client.post(
            reverse('api:v2:column_list_settings-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps(self.payload_data),
            content_type='application/json'
        )
        self.client.post(
            reverse('api:v2:column_list_settings-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps(self.payload_data),
            content_type='application/json'
        )

        id_to_delete = json.loads(to_delete.content)['data']['id']
        response = self.client.delete(
            reverse('api:v2:column_list_settings-detail',
                    args=[id_to_delete]) + '?organization_id=' + str(self.org.id)
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # check to make sure that it isn't in the column list setting list.
        response = self.client.get(
            reverse('api:v2:column_list_settings-list') + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)
        self.assertEqual(len(data['data']), 1)
        self.assertNotEqual(data['data'][0]['id'], id_to_delete)

    def test_update_column_settings(self):
        cls = self.client.post(
            reverse('api:v2:column_list_settings-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps(self.payload_data),
            content_type='application/json'
        )
        payload = {
            "name": "New Name",
            "inventory_type": "Tax Lot",
            "settings_location": "List View Settings",
        }
        url = reverse('api:v2:column_list_settings-detail',
                      args=[json.loads(cls.content)['data']['id']]) + '?organization_id=' + str(
            self.org.id)

        response = self.client.put(url, data=json.dumps(payload), content_type='application/json')
        result = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The columns will be removed if you don't specity them again in an update method
        self.assertEqual(result['data']['inventory_type'], 'Tax Lot')
        self.assertEqual(len(result['data']['columns']), 0)

        payload['columns'] = [{"id": self.column_1.id, "pinned": True, "order": 999}]
        response = self.client.put(url, data=json.dumps(payload), content_type='application/json')
        result = json.loads(response.content)
        self.assertEqual(len(result['data']['columns']), 1)
        self.assertEqual(result['data']['columns'][0]['order'], 999)
        self.assertEqual(result['data']['columns'][0]['pinned'], True)

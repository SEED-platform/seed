# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.core.urlresolvers import reverse, reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.models import (
    Column,
)
from seed.utils.organizations import create_organization

DEFAULT_CUSTOM_COLUMNS = [
    'project_id',
    'project_building_snapshots__status_label__name',
    'address_line_1',
    'city',
    'state_province',
]

from seed.tests.util import DeleteModelsTestCase

COLUMNS_TO_SEND = DEFAULT_CUSTOM_COLUMNS + ['postal_code', 'pm_parent_property_id',
                                            'calculated_taxlot_ids', 'primary', 'extra_data_field',
                                            'jurisdiction_tax_lot_id', 'is secret lair',
                                            'paint color', 'number of secret gadgets']


class DefaultColumnsViewTests(DeleteModelsTestCase):
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

        Column.objects.create(column_name='test')
        Column.objects.create(column_name='extra_data_test', table_name='PropertyState', is_extra_data=True)

        self.client.login(**user_details)

    def test_set_default_columns(self):
        url = reverse_lazy('api:v1:set_default_columns')
        columns = ['s', 'c1', 'c2']
        post_data = {
            'columns': columns,
            'show_shared_buildings': True
        }
        # set the columns
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        data = json.loads(json_string)
        self.assertEqual(200, response.status_code)

        # get the columns
        # url = reverse_lazy('api:v1:columns-get-default-columns')
        # response = self.client.get(url)
        # json_string = response.content
        # data = json.loads(json_string)
        # self.assertEqual(data['columns'], columns)

        # get show_shared_buildings
        url = reverse_lazy('api:v2:users-shared-buildings', args=[self.user.pk])
        response = self.client.get(url)
        json_string = response.content
        data = json.loads(json_string)
        self.assertEqual(data['show_shared_buildings'], True)

        # set show_shared_buildings to False
        # post_data['show_shared_buildings'] = False
        # url = reverse_lazy('api:v1:set_default_columns')
        # response = self.client.post(
        #     url,
        #     content_type='application/json',
        #     data=json.dumps(post_data)
        # )
        # json_string = response.content
        # data = json.loads(json_string)
        # self.assertEqual(200, response.status_code)

        # get show_shared_buildings
        # url = reverse_lazy('api:v2:users-shared-buildings', args=[self.user.pk])
        # response = self.client.get(url)
        # json_string = response.content
        # data = json.loads(json_string)
        # self.assertEqual(data['show_shared_buildings'], False)

    def test_get_all_columns(self):
        # test building list columns
        response = self.client.get(reverse('api:v2:columns-list'), {
            'organization_id': self.org.id
        })
        data = json.loads(response.content)['columns']

        # remove the id columns to make checking existence easier
        for result in data:
            del result['id']

        expected = {
            u'name': u'pm_property_id',
            u'table_name': u'PropertyState',
            u'column_name': u'pm_property_id',
            u'display_name': u'PM Property ID',
            u'is_extra_data': False,
            u'data_type': u'string',
            u'related': False,
            u'sharedFieldType': u'None',
            u'pinnedLeft': True
        }

        # randomly check a column
        self.assertIn(expected, data)

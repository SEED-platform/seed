# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.urls import reverse, reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.models import (
    Column,
    PropertyState,
    TaxLotState,
    DATA_STATE_MATCHING,

)
from seed.utils.organizations import create_organization

DEFAULT_CUSTOM_COLUMNS = [
    'project_id',
    'project_building_snapshots__status_label__name',
    'address_line_1',
    'city',
    'state_province',
]
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
)

from seed.tests.util import DeleteModelsTestCase


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
        user_details_2 = {
            'username': 'test_user_2@demo.com',
            'password': 'test_pass_2',
            'email': 'test_user_2@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.user_2 = User.objects.create_superuser(**user_details_2)
        self.org, _, _ = create_organization(self.user, "test-organization-a")
        self.org_2, _, _ = create_organization(self.user_2, "test-organization-b")

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.tax_lot_state_factory = FakeTaxLotStateFactory(organization=self.org)

        Column.objects.create(column_name='test', organization=self.org)
        Column.objects.create(column_name='extra_data_test',
                              table_name='PropertyState',
                              organization=self.org,
                              is_extra_data=True)
        self.cross_org_column = Column.objects.create(column_name='extra_data_test',
                                                      table_name='PropertyState',
                                                      organization=self.org_2,
                                                      is_extra_data=True)

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
        data = response.json()
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
            del result['name']  # name is hard to compare because it is name_{ID}
            del result['organization_id']  # org changes based on test

        expected = {
            'table_name': 'PropertyState',
            'column_name': 'pm_property_id',
            'display_name': 'PM Property ID',
            'is_extra_data': False,
            'merge_protection': 'Favor New',
            'data_type': 'string',
            'geocoding_order': 0,
            'related': False,
            'sharedFieldType': 'None',
            'pinnedLeft': True,
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': True,
            'recognize_empty': False,
        }

        # randomly check a column
        self.assertIn(expected, data)

    def test_rename_column_property(self):
        column = Column.objects.filter(
            organization=self.org, table_name='PropertyState', column_name='address_line_1'
        ).first()

        for i in range(1, 10):
            self.property_state_factory.get_property_state(data_state=DATA_STATE_MATCHING)
            self.tax_lot_state_factory.get_taxlot_state(data_state=DATA_STATE_MATCHING)

        for ps in PropertyState.objects.filter(organization=self.org).order_by("pk"):
            # orig_data = [{"al1": ps.address_line_1,
            #               "ed": ps.extra_data,
            #               "na": ps.normalized_address}]
            expected_data = [{"al1": None,
                              "ed": {"address_line_1_extra_data": ps.address_line_1},
                              "na": None}]

        # test building list columns
        response = self.client.post(
            reverse('api:v2:columns-rename', args=[column.pk]),
            content_type='application/json',
            data=json.dumps({
                'new_column_name': 'address_line_1_extra_data',
                'overwrite': False
            })
        )
        result = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(result['success'])

        for ps in PropertyState.objects.filter(organization=self.org).order_by("pk"):
            new_data = [{"al1": ps.address_line_1,
                         "ed": ps.extra_data,
                         "na": ps.normalized_address}]

        self.assertListEqual(expected_data, new_data)

    def test_rename_column_property_existing(self):
        column = Column.objects.filter(
            organization=self.org, table_name='PropertyState', column_name='address_line_1'
        ).first()

        for i in range(1, 10):
            self.property_state_factory.get_property_state(data_state=DATA_STATE_MATCHING)

        for ps in PropertyState.objects.filter(organization=self.org).order_by("pk"):
            expected_data = [{"al1": None,
                              "pn": ps.address_line_1,
                              "na": None}]

        response = self.client.post(
            reverse('api:v2:columns-rename', args=[column.pk]),
            content_type='application/json',
            data=json.dumps({
                'new_column_name': 'property_name',
                'overwrite': False
            })
        )
        result = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(result['success'])

        response = self.client.post(
            reverse('api:v2:columns-rename', args=[column.pk]),
            content_type='application/json',
            data=json.dumps({
                'new_column_name': 'property_name',
                'overwrite': True
            })
        )
        result = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(result['success'])

        for ps in PropertyState.objects.filter(organization=self.org).order_by("pk"):
            new_data = [{"al1": ps.address_line_1,
                         "pn": ps.property_name,
                         "na": ps.normalized_address}]

        self.assertListEqual(expected_data, new_data)

    def test_rename_column_taxlot(self):
        column = Column.objects.filter(
            organization=self.org, table_name='TaxLotState', column_name='address_line_1'
        ).first()

        for i in range(1, 10):
            self.property_state_factory.get_property_state(data_state=DATA_STATE_MATCHING)
            self.tax_lot_state_factory.get_taxlot_state(data_state=DATA_STATE_MATCHING)

        for ps in TaxLotState.objects.filter(organization=self.org).order_by("pk"):
            # orig_data = [{"al1": ps.address_line_1,
            #               "ed": ps.extra_data,
            #               "na": ps.normalized_address}]
            expected_data = [{"al1": None,
                              "ed": {"address_line_1_extra_data": ps.address_line_1},
                              "na": None}]

        # test building list columns
        response = self.client.post(
            reverse('api:v2:columns-rename', args=[column.pk]),
            content_type='application/json',
            data=json.dumps({
                'new_column_name': 'address_line_1_extra_data',
                'overwrite': False
            })
        )
        result = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(result['success'])

        for ps in TaxLotState.objects.filter(organization=self.org).order_by("pk"):
            new_data = [{"al1": ps.address_line_1,
                         "ed": ps.extra_data,
                         "na": ps.normalized_address}]

        self.assertListEqual(expected_data, new_data)

    def test_rename_column_wrong_org(self):
        response = self.client.post(
            reverse('api:v2:columns-rename', args=[self.cross_org_column.pk]),
            content_type='application/json',
        )
        result = response.json()
        # self.assertFalse(result['success'])
        self.assertEqual(
            'Cannot find column in org=%s with pk=%s' % (self.org.id, self.cross_org_column.pk),
            result['message'],
        )

    def test_rename_column_dne(self):
        # test building list columns
        response = self.client.post(
            reverse('api:v2:columns-rename', args=[-999]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)
        result = response.json()
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'Cannot find column in org=%s with pk=-999' % self.org.id)

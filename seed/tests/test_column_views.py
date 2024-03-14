# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json

from django.urls import reverse, reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.models import DATA_STATE_MATCHING, Column, PropertyState, TaxLotState
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakeTaxLotStateFactory
)
from seed.tests.util import AccessLevelBaseTestCase, DeleteModelsTestCase
from seed.utils.organizations import create_organization

DEFAULT_CUSTOM_COLUMNS = [
    'project_id',
    'project_building_snapshots__status_label__name',
    'address_line_1',
    'city',
    'state_province',
]


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

    def test_create_column(self):
        # Set Up
        ps = self.property_state_factory.get_property_state(self.org)
        self.assertFalse("new_column" in ps.extra_data)

        url = reverse_lazy('api:v3:columns-list') + "?organization_id=" + str(self.org.id)
        post_data = {
            'column_name': 'new_column',
            'table_name': 'PropertyState',
        }

        # Act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )

        # Assert
        self.assertEqual(201, response.status_code)

        json_string = response.content
        data = json.loads(json_string)
        self.assertEqual(data["column"]["column_name"], post_data["column_name"])
        self.assertEqual(data["column"]["table_name"], post_data["table_name"])

        Column.objects.get(**post_data)  # error if doesn't exist.

    def test_create_column_name_of_access_level_instance(self):
        url = reverse_lazy('api:v3:columns-list') + "?organization_id=" + str(self.org.id)
        post_data = {
            'display_name': self.org.access_level_names[0],
            'organization_id': self.org.id,
            'table_name': 'PropertyState'
        }

        # Act
        response = self.client.post(url, content_type='application/json', data=json.dumps(post_data))

        # Assert
        self.assertEqual(400, response.status_code)

    def test_create_column_bad_no_data(self):
        # Set Up
        url = reverse_lazy('api:v3:columns-list') + "?organization_id=" + str(self.org.id)

        # Act - no data
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps({})
        )
        self.assertEqual(400, response.status_code)

        # Act - no table_name
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps({'column_name': 'new_column'})
        )
        self.assertEqual(400, response.status_code)

        # Act - no column_name
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps({'table_name': 'PropertyState'})
        )
        self.assertEqual(400, response.status_code)

        # Act - invalid key
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps({
                'column_name': 'new_column',
                'table_name': 'bad',
                'whoa': 'I shouldnt be here',
            })
        )
        self.assertEqual(400, response.status_code)

    def test_create_column_bad_table_name(self):
        # Set Up
        url = reverse_lazy('api:v3:columns-list') + "?organization_id=" + str(self.org.id)
        post_data = {
            'column_name': 'new_column',
            'table_name': 'bad',
        }

        # Act
        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )

        # Assert
        self.assertEqual(400, response.status_code)

    def test_get_all_columns(self):
        # test building list columns
        response = self.client.get(reverse('api:v3:columns-list'), {
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
            'column_description': 'PM Property ID',
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
            'comstock_mapping': None,
            'derived_column': None,
        }
        # randomly check a column
        self.assertIn(expected, data)

    def test_column_units_added(self):

        responseWithoutUnits = self.client.get(reverse('api:v3:columns-list'), {
            'organization_id': self.org.id,
            'display_units': 'false'
        })
        columnWithoutUnits = next((x for x in json.loads(responseWithoutUnits.content)['columns'] if x['column_name'] == 'source_eui_modeled'), None)
        self.assertEqual(columnWithoutUnits['display_name'], 'Source EUI Modeled')

        responseWithUnits = self.client.get(reverse('api:v3:columns-list'), {
            'organization_id': self.org.id,
            'display_units': 'true'
        })
        columnWithUnits = next((x for x in json.loads(responseWithUnits.content)['columns'] if x['id'] == columnWithoutUnits['id']), None)
        self.assertEqual(columnWithUnits['display_name'], 'Source EUI Modeled (kBtu/ft²/year)')

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
            reverse('api:v3:columns-rename', args=[column.pk]),
            content_type='application/json',
            data=json.dumps({
                'new_column_name': 'address_line_1_extra_data',
                'overwrite': False,
                'organization_id': self.org.id
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

    def test_rename_column_access_level_name(self):
        column = Column.objects.filter(organization=self.org, table_name='PropertyState', column_name='address_line_1').first()
        url = reverse_lazy('api:v3:columns-detail', args=[column.id]) + "?organization_id=" + str(self.org.id)
        payload = {'column_name': 'address_line_1', 'table_name': 'PropertyState', "sharedFieldType": "None", "comstock_mapping": None, "display_name": self.org.access_level_names[0]}

        response = self.client.put(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 400

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
            reverse('api:v3:columns-rename', args=[column.pk]),
            content_type='application/json',
            data=json.dumps({
                'new_column_name': 'property_name',
                'overwrite': False,
                'organization_id': self.org.id,
            })
        )
        result = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(result['success'])

        response = self.client.post(
            reverse('api:v3:columns-rename', args=[column.pk]),
            content_type='application/json',
            data=json.dumps({
                'new_column_name': 'property_name',
                'overwrite': True,
                'organization_id': self.org.id,
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
            reverse('api:v3:columns-rename', args=[column.pk]),
            content_type='application/json',
            data=json.dumps({
                'new_column_name': 'address_line_1_extra_data',
                'overwrite': False,
                'organization_id': self.org.id,
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
            reverse('api:v3:columns-rename', args=[self.cross_org_column.pk]),
            content_type='application/json',
            data={'organization_id': self.org.id}
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
            reverse('api:v3:columns-rename', args=[-999]),
            content_type='application/json',
            data={'organization_id': self.org.id},
        )
        self.assertEqual(response.status_code, 404)
        result = response.json()
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'Cannot find column in org=%s with pk=-999' % self.org.id)


class ColumnsViewPermissionsTests(AccessLevelBaseTestCase, DeleteModelsTestCase):
    def setUp(self):
        super().setUp()
        self.column = Column.objects.create(column_name='test', organization=self.org, table_name='PropertyState', is_extra_data=True)
        self.column.save()

    def test_column_create_permissions(self):
        url = reverse_lazy('api:v3:columns-list') + "?organization_id=" + str(self.org.id)
        payload = {'column_name': 'new_column', 'table_name': 'PropertyState'}

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 403

        # root users can create column in root
        self.login_as_root_member()
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 201

    def test_column_delete_permissions(self):
        url = reverse_lazy('api:v3:columns-detail', args=[self.column.id]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 200

    def test_column_update_permissions(self):
        url = reverse_lazy('api:v3:columns-detail', args=[self.column.id]) + "?organization_id=" + str(self.org.id)
        payload = {'column_name': 'boo', 'table_name': 'PropertyState', "sharedFieldType": "None", "comstock_mapping": None}

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 403

        # root users can see meters in root
        self.login_as_root_member()
        response = self.client.put(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 200

    def test_column_rename_permissions(self):
        url = reverse_lazy('api:v3:columns-rename', args=[self.column.id]) + "?organization_id=" + str(self.org.id)
        payload = {'new_column_name': 'boo'}

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_member()
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 200

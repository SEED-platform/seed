# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.test import TransactionTestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.models import FilterGroup, StatusLabel
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class FilterGroupsTests(TransactionTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',  # the username needs to be in the form of an email.
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Jaqen',
            'last_name': "H'ghar",
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user, 'test-organization-a')
        self.other_org, _, _ = create_organization(self.user, 'test-organization-b')
        self.client.login(**user_details)

        self.status_label = StatusLabel.objects.create(name='test', super_organization=self.org)

        self.filter_group = FilterGroup.objects.create(
            name='test_filter_group',
            organization_id=self.org.id,
            inventory_type=1,  # Tax Lot
            query_dict={'year_built__lt': ['1950']},
        )
        self.filter_group.and_labels.add(self.status_label.id)
        self.filter_group.save()

    def test_create_filter_group(self):
        # Action
        response = self.client.post(
            reverse('api:v3:filter_groups-list') + f'?organization_id={self.org.id}',
            data=json.dumps(
                {
                    'name': 'new_filter_group',
                    'inventory_type': 'Tax Lot',
                    'query_dict': {'year_built__lt': ['1950']},
                    'exclude_labels': [self.status_label.id],
                }
            ),
            content_type='application/json',
        )

        # Assertion
        self.assertEqual(201, response.status_code)
        self.assertEqual(response.json()['status'], 'success')

        data = response.json()['data']
        self.assertIsInstance(data['id'], int)
        self.assertEqual('new_filter_group', data['name'])
        self.assertEqual(self.org.id, data['organization_id'])
        self.assertEqual('Tax Lot', data['inventory_type'])
        self.assertEqual({'year_built__lt': ['1950']}, data['query_dict'])
        self.assertEqual([self.status_label.id], data['exclude_labels'])

    def test_create_filter_group_no_name(self):
        # Action
        response = self.client.post(
            reverse('api:v3:filter_groups-list') + f'?organization_id={self.org.id}',
            data=json.dumps(
                {
                    'inventory_type': 'Tax Lot',
                    'query_dict': {'year_built__lt': ['1950']},
                }
            ),
            content_type='application/json',
        )

        # Assertion
        self.assertEqual(400, response.status_code)

    def test_create_filter_group_bad_name(self):
        # Action
        response = self.client.post(
            reverse('api:v3:filter_groups-list') + f'?organization_id={self.org.id}',
            data=json.dumps(
                {
                    'name': self.filter_group.name,
                    'inventory_type': 'Tax Lot',
                    'query_dict': {'year_built__lt': ['1950']},
                }
            ),
            content_type='application/json',
        )

        # Assertion
        self.assertEqual(400, response.status_code)

    def test_create_filter_group_no_inventory_type(self):
        # Action
        response = self.client.post(
            reverse('api:v3:filter_groups-list') + f'?organization_id={self.org.id}',
            data=json.dumps(
                {
                    'name': 'new_filter_group',
                    'query_dict': {'year_built__lt': ['1950']},
                }
            ),
            content_type='application/json',
        )

        # Assertion
        self.assertEqual(400, response.status_code)

    def test_create_filter_group_bad_inventory_type(self):
        # Action
        response = self.client.post(
            reverse('api:v3:filter_groups-list') + f'?organization_id={self.org.id}',
            data=json.dumps(
                {
                    'name': 'new_filter_group',
                    'inventory_type': 'bad inventory type',
                    'query_dict': {'year_built__lt': ['1950']},
                }
            ),
            content_type='application/json',
        )

        # Assertion
        self.assertEqual(400, response.status_code)

    def test_create_filter_group_label_doesnt_exist(self):
        # Action
        response = self.client.post(
            reverse('api:v3:filter_groups-list') + f'?organization_id={self.org.id}',
            data=json.dumps({'name': 'new_filter_group', 'inventory_type': 'Tax Lot', 'and_labels': [-1, -2, self.status_label.id]}),
            content_type='application/json',
        )

        # Assertion
        self.assertEqual(201, response.status_code)
        self.assertEqual(response.json()['status'], 'success')
        self.assertEqual(response.json()['warnings'], 'labels with ids do not exist: -1, -2')

        data = response.json()['data']
        self.assertEqual([self.status_label.id], data['and_labels'])

    def test_get_filter_group(self):
        # Action
        response = self.client.get(
            reverse('api:v3:filter_groups-detail', args=[self.filter_group.id]) + f'?organization_id={self.org.id}',
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                'status': 'success',
                'data': {
                    'id': self.filter_group.id,
                    'name': 'test_filter_group',
                    'organization_id': self.org.id,
                    'inventory_type': 'Tax Lot',
                    'query_dict': {'year_built__lt': ['1950']},
                    'and_labels': [self.status_label.id],
                    'or_labels': [],
                    'exclude_labels': [],
                },
            },
            response.json(),
        )

    def test_get_all_filter_group(self):
        # Setup
        # second, as self.filter_group is the first
        second_filter_group = FilterGroup.objects.create(
            name='second_test_filter_group',
            organization_id=self.org.id,
            inventory_type=1,  # Taxlot
            query_dict={'year_built__lt': ['1950']},
        )

        # wrong org, shouldn't show up
        FilterGroup.objects.create(
            name='wrong org',
            organization_id=self.other_org.id,
            inventory_type=1,  # Taxlot
            query_dict={'year_built__lt': ['1950']},
        )

        # wrong inventory type, shouldn't show up
        FilterGroup.objects.create(
            name='wrong inventory type',
            organization_id=self.org.id,
            inventory_type=0,  # Property
            query_dict={'year_built__lt': ['1950']},
        )

        # Action
        response = self.client.get(
            reverse('api:v3:filter_groups-list') + '?inventory_type=Tax Lot' + f'&organization_id={self.org.id}',
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                'data': [
                    {
                        'id': self.filter_group.id,
                        'inventory_type': 'Tax Lot',
                        'name': 'test_filter_group',
                        'organization_id': self.org.id,
                        'query_dict': {'year_built__lt': ['1950']},
                        'and_labels': [self.status_label.id],
                        'or_labels': [],
                        'exclude_labels': [],
                    },
                    {
                        'id': second_filter_group.id,
                        'inventory_type': 'Tax Lot',
                        'name': 'second_test_filter_group',
                        'organization_id': self.org.id,
                        'query_dict': {'year_built__lt': ['1950']},
                        'and_labels': [],
                        'or_labels': [],
                        'exclude_labels': [],
                    },
                ],
                'pagination': {'end': 2, 'has_next': False, 'has_previous': False, 'num_pages': 1, 'page': 1, 'start': 1, 'total': 2},
                'status': 'success',
            },
            response.json(),
        )

    def test_update_filter_group_name(self):
        # Action
        response = self.client.put(
            reverse('api:v3:filter_groups-detail', args=[self.filter_group.id]) + f'?organization_id={self.org.id}',
            data=json.dumps({'name': 'new_name'}),
            content_type='application/json',
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                'status': 'success',
                'data': {
                    'id': self.filter_group.id,
                    'name': 'new_name',
                    'organization_id': self.org.id,
                    'inventory_type': 'Tax Lot',
                    'query_dict': {'year_built__lt': ['1950']},
                    'and_labels': [self.status_label.id],
                    'or_labels': [],
                    'exclude_labels': [],
                },
            },
            response.json(),
        )

    def test_update_filter_group_labels(self):
        # Setup
        first_label = StatusLabel.objects.create(name='1', super_organization=self.org)
        second_label = StatusLabel.objects.create(name='2', super_organization=self.org)

        # Action
        response = self.client.put(
            reverse('api:v3:filter_groups-detail', args=[self.filter_group.id]) + f'?organization_id={self.org.id}',
            data=json.dumps(
                {
                    'and_labels': [first_label.id, second_label.id],
                }
            ),
            content_type='application/json',
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                'status': 'success',
                'data': {
                    'id': self.filter_group.id,
                    'name': 'test_filter_group',
                    'organization_id': self.org.id,
                    'inventory_type': 'Tax Lot',
                    'query_dict': {'year_built__lt': ['1950']},
                    'and_labels': [first_label.id, second_label.id],
                    'or_labels': [],
                    'exclude_labels': [],
                },
            },
            response.json(),
        )

        # Action
        response = self.client.put(
            reverse('api:v3:filter_groups-detail', args=[self.filter_group.id]) + f'?organization_id={self.org.id}',
            data=json.dumps({'or_labels': [first_label.id], 'exclude_labels': [second_label.id]}),
            content_type='application/json',
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                'status': 'success',
                'data': {
                    'id': self.filter_group.id,
                    'name': 'test_filter_group',
                    'organization_id': self.org.id,
                    'inventory_type': 'Tax Lot',
                    'query_dict': {'year_built__lt': ['1950']},
                    'and_labels': [],
                    'or_labels': [first_label.id],
                    'exclude_labels': [second_label.id],
                },
            },
            response.json(),
        )

    def test_update_filter_group_bad_labels(self):
        # Setup
        first_label = StatusLabel.objects.create(name='1', super_organization=self.org)

        # Action
        response = self.client.put(
            reverse('api:v3:filter_groups-detail', args=[self.filter_group.id]) + f'?organization_id={self.org.id}',
            data=json.dumps(
                {
                    'and_labels': [first_label.id, -1],
                    'or_labels': [first_label.id, -1],
                }
            ),
            content_type='application/json',
        )

        # Assertion
        self.assertEqual(400, response.status_code)

        # Action
        response = self.client.get(
            reverse('api:v3:filter_groups-detail', args=[self.filter_group.id]) + f'?organization_id={self.org.id}',
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                'status': 'success',
                'data': {
                    'id': self.filter_group.id,
                    'name': 'test_filter_group',
                    'organization_id': self.org.id,
                    'inventory_type': 'Tax Lot',
                    'query_dict': {'year_built__lt': ['1950']},
                    'and_labels': [self.status_label.id],
                    'or_labels': [],
                    'exclude_labels': [],
                },
            },
            response.json(),
        )

    def test_delete_filter_group(self):
        # Setup
        filter_group = FilterGroup.objects.create(
            name='new_filter_group',
            organization_id=self.org.id,
            inventory_type=1,  # Tax Lot
            query_dict={'year_built__lt': ['1950']},
        )

        filter_group_id = filter_group.id

        # Action
        response = self.client.delete(
            reverse('api:v3:filter_groups-detail', args=[filter_group_id]) + f'?organization_id={self.org.id}',
        )

        # Assertion
        self.assertEqual(204, response.status_code)
        result = FilterGroup.objects.filter(id=filter_group_id)
        self.assertFalse(result.exists())

    def test_delete_filter_group_does_not_exist(self):
        # Action
        response = self.client.delete(
            reverse('api:v3:filter_groups-detail', args=['not_a_valid_id']) + f'?organization_id={self.org.id}',
        )

        # Assertion
        self.assertEqual(404, response.status_code)


class FilterGroupsPermissionsTests(AccessLevelBaseTestCase, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.filter_group = FilterGroup.objects.create(
            name='test_filter_group',
            organization_id=self.org.id,
            inventory_type=1,  # Tax Lot
            query_dict={'year_built__lt': ['1950']},
        )
        self.status_label = StatusLabel.objects.create(name='test', super_organization=self.org)

    def test_filter_group_delete(self):
        url = reverse('api:v3:filter_groups-detail', args=[self.filter_group.id]) + f'?organization_id={self.org.id}'

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 403

        # root user can
        self.login_as_root_member()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 204

    def test_filter_group_create(self):
        url = reverse('api:v3:filter_groups-list') + f'?organization_id={self.org.id}'
        post_params = json.dumps(
            {
                'name': 'new_filter_group',
                'inventory_type': 'Tax Lot',
                'query_dict': {'year_built__lt': ['1950']},
                'label_logic': 'exclude',
                'labels': [self.status_label.id],
            }
        )

        # root user can
        self.login_as_root_member()
        response = self.client.post(url, post_params, content_type='application/json')
        assert response.status_code == 201

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, post_params, content_type='application/json')
        assert response.status_code == 403

    def test_filter_group_update(self):
        url = reverse('api:v3:filter_groups-detail', args=[self.filter_group.id]) + f'?organization_id={self.org.id}'
        params = json.dumps({'name': 'new_name'})

        # root user can
        self.login_as_root_member()
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 200

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 403

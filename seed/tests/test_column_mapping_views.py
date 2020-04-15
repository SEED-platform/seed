# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.urls import reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.models import (
    Column, ColumnMapping
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


class TestColumnMappingViews(DeleteModelsTestCase):
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

        self.client.login(**user_details)

        foo_col = Column.objects.create(organization=self.org, column_name="foo")
        bar_col = Column.objects.create(organization=self.org, column_name="bar")
        baz_col = Column.objects.create(organization=self.org, column_name="baz")

        self.cm1 = ColumnMapping.objects.create(super_organization=self.org)
        self.cm1.column_raw.add(foo_col)
        self.cm1.column_mapped.add(baz_col)

        self.cm2 = ColumnMapping.objects.create(super_organization=self.org)
        self.cm2.column_raw.add(foo_col, bar_col)
        self.cm2.column_mapped.add(baz_col)

    def test_delete_mapping(self):
        url = reverse_lazy('api:v2:column_mappings-detail', args=[self.cm1.id])
        url = url + '?organization_id=%s' % self.org.id
        response = self.client.delete(url, content_type='application/json')

        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['message'], 'Column mapping deleted')

    def test_deleting_non_existent_mapping(self):
        url = reverse_lazy('api:v2:column_mappings-detail', args=[999999999999])
        url = url + '?organization_id=%s' % self.org.id
        response = self.client.delete(url, content_type='application/json')

        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['message'],
                         'Column mapping with id and organization did not exist, nothing removed')

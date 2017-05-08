# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pipermerriam@gmail.com>', Paul Munday<paul@paulmunday.net>

Unit tests for seed/views/labels.py
"""
from django.core.urlresolvers import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import (
    StatusLabel as Label,
)
from seed.test_helpers.fake import (
    mock_queryset_factory,
)
from seed.utils.organizations import (
    create_organization,
)
from seed.views.labels import (
    UpdateInventoryLabelsAPIView,
)


class TestLabelsViewSet(TestCase):
    """Test the label DRF viewset"""

    def test_results_are_not_actually_paginated(self):
        """
        Ensure that labels are not actually paginated.
        """
        user = User.objects.create_superuser(
            email='test_user@demo.com',
            username='test_user@demo.com',
            password='secret',
        )
        organization, _, _ = create_organization(user, "test-organization")

        # Create 101 labels.  This should be pretty future proof against any
        # reasonable default pagination settings as well as realistic number of
        # labels.
        for i in range(101):
            Label.objects.create(
                color="red",
                name="test_label-{0}".format(i),
                super_organization=organization,
            )

        client = APIClient()
        client.login(username=user.username, password='secret')

        url = reverse('apiv2:labels-list')

        response = client.get(url, {'organization_id': organization.pk, 'inventory_type': 'property'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), organization.labels.count())

        results = response.data

        self.assertEqual(len(results), organization.labels.count())

    def test_organization_query_param_is_used(self):
        """
        Ensure that when the organization_id query parameter is provided, that
        the endpoint returns the appropriate labels for that organization.
        """
        user = User.objects.create_superuser(
            email='test_user@demo.com',
            username='test_user@demo.com',
            password='secret',
        )
        organization_a, _, _ = create_organization(user, "test-organization-a")
        organization_b, _, _ = create_organization(user, "test-organization-b")

        # Ensures that at least a single label exists to ensure that we aren't
        # relying on auto-creation of labels for this test to pass.
        Label.objects.create(
            color="red",
            name="test_label-a",
            super_organization=organization_a,
        )

        Label.objects.create(
            color="red",
            name="test_label-b",
            super_organization=organization_b,
        )

        client = APIClient()
        client.login(username=user.username, password='secret')

        url = reverse('apiv2:labels-list')

        response_a = client.get(url, {'organization_id': organization_a.pk, 'inventory_type': 'property'})
        response_b = client.get(url, {'organization_id': organization_b.pk, 'inventory_type': 'property'})

        self.assertEqual(response_a.status_code, status.HTTP_200_OK)
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)

        results_a = set(result['organization_id'] for result in response_a.data)
        results_b = set(result['organization_id'] for result in response_b.data)

        assert results_a == {organization_a.pk}
        assert results_b == {organization_b.pk}


class TestUpdateInventoryLabelsAPIView(TestCase):

    def setUp(self):
        self.api_view = UpdateInventoryLabelsAPIView()

        # Models can't  be imported directly hence self
        self.PropertyLabels = self.api_view.models['property']
        self.TaxlotLabels = self.api_view.models['taxlot']
        self.mock_property_queryset = mock_queryset_factory(
            self.PropertyLabels,
            flatten=True,
            property_id=range(1, 11),
            statuslabel_id=[1] * 3 + [2] * 3 + [3] * 2 + [4] * 2
        )
        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**self.user_details)
        self.org = Organization.objects.create()
        self.org_user = OrganizationUser.objects.create(
            user=self.user, organization=self.org
        )
        self.status_label = Label.objects.create(
            name='test', super_organization=self.org
        )
        self.client.login(**self.user_details)

    def tearDown(self):
        self.user.delete()
        self.org.delete()
        self.org_user.delete()
        self.status_label.delete()

        # Models can't be imported directly hence self
        self.PropertyLabels.objects.all().delete()
        self.TaxlotLabels.objects.all().delete()

    def test_get_label_desc(self):
        add_label_ids = [self.status_label.id]
        remove_label_ids = []
        result = self.api_view.get_label_desc(
            add_label_ids, remove_label_ids
        )[0]
        expected = {
            'id': self.status_label.id,
            'name': 'test',
            'color': 'green'
        }
        self.assertEqual(result, expected)

    def test_get_inventory_id(self):
        result = self.api_view.get_inventory_id(
            self.mock_property_queryset[0], 'property'
        )
        self.assertEqual(result, 1)

    def test_exclude(self):
        result = self.api_view.exclude(
            self.mock_property_queryset, 'property', [3, 4]
        )
        expected = {3: [7, 8], 4: [9, 10]}
        self.assertEqual(result, expected)

    def test_label_factory(self):
        result = self.api_view.label_factory('property', 100, 100)
        self.assertEqual(
            result.__class__.__name__, self.PropertyLabels.__name__
        )
        self.assertEqual(result.property_id, 100)
        self.assertEqual(result.statuslabel_id, 100)

    def test_add_remove_labels(self):
        result = self.api_view.add_labels(
            self.mock_property_queryset, 'property',
            [1, 2, 3], [5, 6]
        )
        self.assertEqual(result, [1, 2, 3] * 2)
        qs = self.PropertyLabels.objects.all()
        self.assertEqual(len(qs), 6)
        self.assertEqual(qs[0].property_id, 1)
        self.assertEqual(qs[0].statuslabel_id, 5)

        result = self.api_view.remove_labels(qs, 'property', [5, 6])
        qs = self.PropertyLabels.objects.all()
        self.assertEqual(len(qs), 0)

    def test_put(self):
        client = APIClient()
        client.login(
            username=self.user_details['username'],
            password=self.user_details['password']
        )
        r = reverse('apiv2:property-labels')
        url = "{}?organization_id={}".format(
            r, self.org.id
        )

        post_params = {
            'add_label_ids': [self.status_label.id],
            'remove_label_ids': [],
            'inventory_ids': [1, 2, 3],
        }
        response = client.put(
            url, post_params, format='json'
        )
        result = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['num_updated'], 3)

        label = result['labels'][0]
        self.assertEqual(label['color'], self.status_label.color)
        self.assertEqual(label['id'], self.status_label.id)
        self.assertEqual(label['name'], self.status_label.name)

        post_params = {
            'add_label_ids': [],
            'remove_label_ids': [self.status_label.id],
            'inventory_ids': [1, 2, 3],
        }
        response = client.put(
            url, post_params, format='json'
        )
        result = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['num_updated'], 3)

        label = result['labels'][0]
        self.assertEqual(label['color'], self.status_label.color)
        self.assertEqual(label['id'], self.status_label.id)
        self.assertEqual(label['name'], self.status_label.name)

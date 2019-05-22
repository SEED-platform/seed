# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pipermerriam@gmail.com>', Paul Munday<paul@paulmunday.net>

Unit tests for seed/views/labels.py
"""
from django.db import IntegrityError
from django.db import transaction
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APIClient

from seed.landing.models import SEEDUser as User
from seed.models import (
    Property,
    StatusLabel as Label,
    TaxLot,
)
from seed.test_helpers.fake import (
    mock_queryset_factory,
)
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization
from seed.views.labels import (
    UpdateInventoryLabelsAPIView,
)


class TestLabelsViewSet(DeleteModelsTestCase):
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

        url = reverse('api:v2:labels-list')

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

        # Ensures that at least a single label exists to ensure that we are not
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

        url = reverse('api:v2:labels-list')

        response_a = client.get(url, {'organization_id': organization_a.pk, 'inventory_type': 'property'})
        response_b = client.get(url, {'organization_id': organization_b.pk, 'inventory_type': 'property'})

        self.assertEqual(response_a.status_code, status.HTTP_200_OK)
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)

        results_a = set(result['organization_id'] for result in response_a.data)
        results_b = set(result['organization_id'] for result in response_b.data)

        assert results_a == {organization_a.pk}
        assert results_b == {organization_b.pk}


class TestUpdateInventoryLabelsAPIView(DeleteModelsTestCase):

    def setUp(self):
        self.api_view = UpdateInventoryLabelsAPIView()

        # Models can't  be imported directly hence self
        self.PropertyLabels = self.api_view.models['property']
        self.TaxlotLabels = self.api_view.models['taxlot']

        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**self.user_details)
        self.org, _, _ = create_organization(self.user)
        self.status_label = Label.objects.create(
            name='test', super_organization=self.org
        )
        self.client.login(**self.user_details)

        self.label_1 = Label.objects.all()[0]
        self.label_2 = Label.objects.all()[1]
        self.label_3 = Label.objects.all()[2]
        self.label_4 = Label.objects.all()[3]

        # Create some real Properties and StatusLabels since validations happen
        for i in range(1, 11):
            Property.objects.create(organization=self.org)

        self.property_ids = Property.objects.all().order_by('id').values_list('id', flat=True)

        self.mock_property_label_qs = mock_queryset_factory(
            self.PropertyLabels,
            flatten=True,
            property_id=self.property_ids,
            statuslabel_id=[self.label_1.id] * 3 + [self.label_2.id] * 3 + [self.label_3.id] * 2 + [self.label_4.id] * 2
        )

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
            self.mock_property_label_qs[0], 'property'
        )
        self.assertEqual(result, self.property_ids[0])

    def test_exclude(self):
        result = self.api_view.exclude(
            self.mock_property_label_qs, 'property', [self.label_3.id, self.label_4.id]
        )

        pid_7 = self.property_ids[6]
        pid_8 = self.property_ids[7]
        pid_9 = self.property_ids[8]
        pid_10 = self.property_ids[9]

        expected = {self.label_3.id: [pid_7, pid_8], self.label_4.id: [pid_9, pid_10]}
        self.assertEqual(result, expected)

    def test_label_factory(self):
        result = self.api_view.label_factory('property', self.label_1.id, self.property_ids[0])
        self.assertEqual(
            result.__class__.__name__, self.PropertyLabels.__name__
        )
        self.assertEqual(result.property_id, self.property_ids[0])
        self.assertEqual(result.statuslabel_id, self.label_1.id)

    def test_add_remove_labels(self):
        pid_1 = self.property_ids[0]
        pid_2 = self.property_ids[1]
        pid_3 = self.property_ids[2]

        result = self.api_view.add_labels(
            self.mock_property_label_qs, 'property',
            [pid_1, pid_2, pid_3], [self.label_2.id, self.label_3.id]
        )
        self.assertEqual(result, [pid_1, pid_2, pid_3] * 2)
        qs = self.PropertyLabels.objects.all()
        self.assertEqual(len(qs), 6)
        self.assertEqual(qs[0].property_id, pid_1)
        self.assertEqual(qs[0].statuslabel_id, self.label_2.id)

        result = self.api_view.remove_labels(qs, 'property', [self.label_2.id, self.label_3.id])
        qs = self.PropertyLabels.objects.all()
        self.assertEqual(len(qs), 0)

    def test_put(self):
        client = APIClient()
        client.login(
            username=self.user_details['username'],
            password=self.user_details['password']
        )
        r = reverse('api:v2:property-labels')
        url = "{}?organization_id={}".format(
            r, self.org.id
        )

        pid_1 = self.property_ids[0]
        pid_2 = self.property_ids[1]
        pid_3 = self.property_ids[2]

        post_params = {
            'add_label_ids': [self.status_label.id],
            'remove_label_ids': [],
            'inventory_ids': [pid_1, pid_2, pid_3],
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
            'inventory_ids': [pid_1, pid_2, pid_3],
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

    def test_error_occurs_when_trying_to_apply_a_label_from_a_different_org(self):
        org_2, _, _ = create_organization(self.user)
        org_2_status_label = Label.objects.create(
            name='org_2_label', super_organization=org_2
        )

        org_1_property = Property.objects.create(organization=self.org)

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                self.api_view.add_labels(
                    self.api_view.models['property'].objects.none(),
                    'property',
                    [org_1_property.id],
                    [org_2_status_label.id]
                )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                org_1_property.labels.add(org_2_status_label)

        self.assertFalse(Property.objects.get(pk=org_1_property.id).labels.all().exists())

        # Repeat for TaxLot
        org_1_taxlot = TaxLot.objects.create(organization=self.org)

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                self.api_view.add_labels(
                    self.api_view.models['taxlot'].objects.none(),
                    'taxlot',
                    [org_1_taxlot.id],
                    [org_2_status_label.id]
                )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                org_1_taxlot.labels.add(org_2_status_label)

        self.assertFalse(TaxLot.objects.get(pk=org_1_taxlot.id).labels.all().exists())

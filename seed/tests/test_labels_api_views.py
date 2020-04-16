# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pipermerriam@gmail.com>', Paul Munday<paul@paulmunday.net>

Unit tests for seed/views/labels.py
"""
from collections import defaultdict

from datetime import datetime

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from seed.landing.models import SEEDUser as User
from seed.models import (
    Property,
    PropertyView,
    StatusLabel as Label,
)
from seed.test_helpers.fake import (
    mock_queryset_factory,
    FakeCycleFactory,
    FakePropertyStateFactory,
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
        self.PropertyViewLabels = self.api_view.models['property']
        self.TaxlotViewLabels = self.api_view.models['taxlot']

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
        self.status_label_2 = Label.objects.create(
            name='test_2', super_organization=self.org
        )
        self.client.login(**self.user_details)

        self.label_1 = Label.objects.all()[0]
        self.label_2 = Label.objects.all()[1]
        self.label_3 = Label.objects.all()[2]
        self.label_4 = Label.objects.all()[3]

        # Create some real PropertyViews, Properties, PropertyStates, and StatusLabels since validations happen
        cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        cycle = cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=timezone.get_current_timezone()))
        property_state_factory = FakePropertyStateFactory(organization=self.org)
        for i in range(1, 11):
            ps = property_state_factory.get_property_state()
            p = Property.objects.create(organization=self.org)
            PropertyView.objects.create(
                cycle=cycle,
                state=ps,
                property=p
            )

        self.propertyview_ids = PropertyView.objects.all().order_by('id').values_list('id', flat=True)

        self.mock_propertyview_label_qs = mock_queryset_factory(
            self.PropertyViewLabels,
            flatten=True,
            propertyview_id=self.propertyview_ids,
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
            self.mock_propertyview_label_qs[0], 'property'
        )
        self.assertEqual(result, self.propertyview_ids[0])

    def test_exclude(self):
        result = self.api_view.exclude(
            self.mock_propertyview_label_qs, 'property', [self.label_3.id, self.label_4.id]
        )

        pvid_7 = self.propertyview_ids[6]
        pvid_8 = self.propertyview_ids[7]
        pvid_9 = self.propertyview_ids[8]
        pvid_10 = self.propertyview_ids[9]

        expected = {self.label_3.id: [pvid_7, pvid_8], self.label_4.id: [pvid_9, pvid_10]}
        self.assertEqual(result, expected)

    def test_label_factory(self):
        result = self.api_view.label_factory('property', self.label_1.id, self.propertyview_ids[0])
        self.assertEqual(
            result.__class__.__name__, self.PropertyViewLabels.__name__
        )
        self.assertEqual(result.propertyview_id, self.propertyview_ids[0])
        self.assertEqual(result.statuslabel_id, self.label_1.id)

    def test_add_remove_labels(self):
        pvid_1 = self.propertyview_ids[0]
        pvid_2 = self.propertyview_ids[1]
        pvid_3 = self.propertyview_ids[2]

        result = self.api_view.add_labels(
            self.mock_propertyview_label_qs, 'property',
            [pvid_1, pvid_2, pvid_3], [self.label_2.id, self.label_3.id]
        )
        self.assertEqual(result, [pvid_1, pvid_2, pvid_3] * 2)
        qs = self.PropertyViewLabels.objects.all()
        self.assertEqual(len(qs), 6)
        self.assertEqual(qs[0].propertyview_id, pvid_1)
        self.assertEqual(qs[0].statuslabel_id, self.label_2.id)

        result = self.api_view.remove_labels(qs, 'property', [self.label_2.id, self.label_3.id])
        qs = self.PropertyViewLabels.objects.all()
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

        pvid_1 = self.propertyview_ids[0]
        pvid_2 = self.propertyview_ids[1]
        pvid_3 = self.propertyview_ids[2]

        post_params = {
            'add_label_ids': [self.status_label.id, self.status_label_2.id],
            'remove_label_ids': [],
            'inventory_ids': [pvid_1, pvid_2, pvid_3],
        }
        response = client.put(
            url, post_params, format='json'
        )
        result = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['num_updated'], 3)

        self.assertEqual(self.PropertyViewLabels.objects.count(), 6)
        label_assignments = defaultdict(list)
        for prop_label in self.PropertyViewLabels.objects.all():
            label_assignments[prop_label.statuslabel_id].append(prop_label.propertyview_id)
        expected_label_assignments = {
            self.status_label.id: [pvid_1, pvid_2, pvid_3],
            self.status_label_2.id: [pvid_1, pvid_2, pvid_3],
        }
        self.assertEqual(label_assignments, expected_label_assignments)

        post_params = {
            'add_label_ids': [],
            'remove_label_ids': [self.status_label.id],
            'inventory_ids': [pvid_1, pvid_2],
        }
        response = client.put(
            url, post_params, format='json'
        )
        result = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['num_updated'], 2)

        self.assertEqual(self.PropertyViewLabels.objects.count(), 4)
        label_assignments = defaultdict(list)
        for prop_label in self.PropertyViewLabels.objects.all():
            label_assignments[prop_label.statuslabel_id].append(prop_label.propertyview_id)
        expected_label_assignments = {
            self.status_label.id: [pvid_3],
            self.status_label_2.id: [pvid_1, pvid_2, pvid_3],
        }
        self.assertEqual(label_assignments, expected_label_assignments)

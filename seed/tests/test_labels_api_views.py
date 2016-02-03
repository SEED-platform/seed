# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pipermerriam@gmail.com>'
"""
"""
Unit tests for seed/views/labels.py
"""

from django.test import TestCase
from django.core.urlresolvers import reverse

from rest_framework.test import APIClient
from rest_framework import status

from seed.utils.organizations import (
    create_organization,
)
from seed.models import (
    StatusLabel as Label,
)
from seed.landing.models import SEEDUser as User


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

        url = reverse('labels:label-list')

        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], organization.labels.count())

        results = response.data['results']

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

        url = reverse('labels:label-list')

        response_a = client.get(url, {'organization_id': organization_a.pk})
        response_b = client.get(url, {'organization_id': organization_b.pk})

        self.assertEqual(response_a.status_code, status.HTTP_200_OK)
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)

        results_a = set(result['organization_id'] for result in response_a.data['results'])
        results_b = set(result['organization_id'] for result in response_b.data['results'])

        assert results_a == {organization_a.pk}
        assert results_b == {organization_b.pk}

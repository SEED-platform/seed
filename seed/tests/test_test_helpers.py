# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.models import PropertyState
from seed.test_helpers.fake import FakePropertyStateFactory
from seed.utils.organizations import create_organization


class TestFakerFactories(TestCase):

    def test_fake_property_state_hash_does_not_change_after_refetch_and_save(self):
        """A regression test for #2493"""
        # Setup
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Test',
            'last_name': 'User',
        }
        user = User.objects.create_user(**user_details)
        org, _, _ = create_organization(user)
        factory = FakePropertyStateFactory(organization=org)

        # Act
        property_state = factory.get_property_state(organization=org)

        # Assert
        refreshed_property_state = PropertyState.objects.get(id=property_state.id)
        refreshed_property_state.save()
        self.assertEqual(property_state.hash_object, refreshed_property_state.hash_object)

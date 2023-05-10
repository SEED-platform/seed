# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import base64

from django.test import TransactionTestCase
from seed.landing.models import SEEDUser as User
from seed.models import PropertyState, Ubid
from seed.utils.organizations import create_organization
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakePropertyViewFactory
)
from unittest import skip
from django.db.models import Q



class UbidModelTests(TransactionTestCase):

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.user.generate_key()
        self.org, _, _ = create_organization(self.user)

        auth_string = base64.urlsafe_b64encode(bytes(
            '{}:{}'.format(self.user.username, self.user.api_key), 'utf-8'
        ))
        self.auth_string = 'Basic {}'.format(auth_string.decode('utf-8'))
        self.headers = {'Authorization': self.auth_string}

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org, user=self.user)
    
    def test_pass(self):
        self.assertTrue(True)

    def test_ubid_model(self):

        ps1 = self.property_view_factory.get_property_view().state
        ps2 = self.property_view_factory.get_property_view().state
        ps3 = self.property_view_factory.get_property_view().state

        ubid1a = Ubid.objects.create(
            ubid="8772WW7W+867V4X3-4803-1389-4816-1389",  # Example UBID from https://www.youtube.com/watch?v=wCfdWyjq_xs
            property=ps1
        )
        ubid1b = Ubid.objects.create(
            ubid="1111BBBB+1111BBB-1111-1111-1111-1111",
            property=ps1,
            preferred=True
        )
        ubid2 = Ubid.objects.create(
            ubid="1111BBBB+1111BBB-1111-1111-1111-1111",
            property=ps2,
            preferred=True
        )
        ubid3 = Ubid.objects.create(
            ubid="3333AAAA+3333AAA-3333-3333-3333-3333",
            property=ps3,
        )
        breakpoint()
        # model properties
        self.assertEqual(ubid1a.property, ps1)
        self.assertEqual(ubid1b.property, ps1)
        self.assertEqual(ubid2.property, ps2)
        self.assertEqual(ubid3.property, ps3)

        self.assertEqual(ps1.ubid_set.count(), 2)
        self.assertEqual(ps1.ubid_set.first(), ubid1a)
        self.assertEqual(ps1.ubid_set.last(), ubid1b)
        self.assertEqual(ps2.ubid_set.first(), ubid2)
        self.assertEqual(ps3.ubid_set.first(), ubid3)

        self.assertEqual(ps1.ubid_set.first().preferred, False)
        self.assertEqual(ps1.ubid_set.last().preferred, True)
        self.assertEqual(ps2.ubid_set.first().preferred, True)
        self.assertEqual(ps3.ubid_set.first().preferred, False)

        ubid = ps3.ubid_set.first()
        ubid.preferred = True 
        ubid.save()
        self.assertEqual(ps3.ubid_set.first().preferred, True)

        # Cascade Delete is one way
        self.assertEqual(Ubid.objects.count(), 4)
        ps1.delete()
        self.assertEqual(Ubid.objects.count(), 2)
        ps2.delete()
        self.assertEqual(Ubid.objects.count(), 1)

        ubid3.delete() 
        self.assertEqual(PropertyState.objects.count(), 1)
        breakpoint()


# class UbidViewTests(TransactionTestCase):
    
#     def setUp(self):
#         user_details = {
#             'username': 'test_user@demo.com',
#             'password': 'test_pass',
#             'email': 'test_user@demo.com'
#         }
#         self.user = User.objects.create_superuser(**user_details)
#         self.user.generate_key()
#         self.org, _, _ = create_organization(self.user)

#         auth_string = base64.urlsafe_b64encode(bytes(
#             '{}:{}'.format(self.user.username, self.user.api_key), 'utf-8'
#         ))
#         self.auth_string = 'Basic {}'.format(auth_string.decode('utf-8'))
#         self.headers = {'Authorization': self.auth_string}

#         self.property_state_factory = FakePropertyStateFactory(organization=self.org)
#         self.property_view_factory = FakePropertyViewFactory(organization=self.org, user=self.user)


#     def test_pass(self):
#         self.assertEqual(1, 1)
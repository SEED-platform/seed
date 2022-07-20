# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

import base64
import json

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import (
    ROLE_MEMBER,
    ROLE_OWNER,
    ROLE_VIEWER,
    OrganizationUser
)
from seed.models import FilterGroup
from seed.utils.organizations import create_organization


class FilterGroupsTests(TestCase):

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',  # the username needs to be in the form of an email.
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Jaqen',
            'last_name': 'H\'ghar'
        }
        self.user = User.objects.create_user(**user_details)
        self.user.generate_key()
        self.org, _, _ = create_organization(self.user)

        auth_string = base64.urlsafe_b64encode(bytes(
            '{}:{}'.format(self.user.username, self.user.api_key), 'utf-8'
        ))
        self.auth_string = 'Basic {}'.format(auth_string.decode('utf-8'))
        self.headers = {'Authorization': self.auth_string}

    def test_create_filter_group(self):
        response = self.client.post(
            "/api/v3/filter_groups/",
            data=json.dumps({
                "name": "test_filter_group",
                "inventory_type": "Tax Lot",
                "query_dict": {},
            }),
            content_type='application/json',
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "name": "test_filter_group",
                "organization_id": self.org.id,
                "inventory_type": "Tax Lot",
                "query_dict": {},
            }
        )

    def test_get_filter_group(self):
        filter_group = FilterGroup(
            name="test_filter_group",
            organization_id=self.org.id,
            inventory_type=1,  # Tax Lot
            query_dict={},
        )

        filter_group.save()

        response = self.client.get(
            f"/api/v3/filter_groups/{filter_group.id}",
            follow=True,
            data={},
            **self.headers
        )

        print(response.json())
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "name": "test_filter_group",
                "organization_id": self.org.id,
                "inventory_type": "Tax Lot",
                "query_dict": {},
            }
        )

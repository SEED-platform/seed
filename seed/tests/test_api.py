# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import base64
import json
from datetime import date

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import Cycle
from seed.utils.api import get_api_endpoints
from seed.utils.organizations import create_organization


class SchemaGenerationTests(TestCase):
    def test_get_api_endpoints_utils(self):
        """
        Test of function that traverses all URLs looking for api endpoints.
        """
        res = get_api_endpoints()
        for url, fn in res.items():
            self.assertTrue(fn.is_api_endpoint)
            self.assertTrue(url.startswith('/'))


class TestApi(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',  # the username needs to be in the form of an email.
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Jaqen',
            'last_name': "H'ghar",
        }
        self.user = User.objects.create_user(**user_details)
        self.user.generate_key()
        self.org, _, _ = create_organization(self.user)
        self.default_cycle = Cycle.objects.filter(organization_id=self.org).first()
        self.cycle, _ = Cycle.objects.get_or_create(
            name='Test Hack Cycle 2015',
            organization=self.org,
            start=date(2015, 1, 1),
            end=date(2015, 12, 31),
        )
        auth_string = base64.urlsafe_b64encode(bytes(f'{self.user.username}:{self.user.api_key}', 'utf-8'))
        self.auth_string = 'Basic {}'.format(auth_string.decode('utf-8'))
        self.headers = {'Authorization': self.auth_string}

    def get_org_id(self, response, username):
        """Return the org id from the passed dictionary and username"""
        org_id = None
        for ctr in range(len(response['organizations'])):
            if response['organizations'][ctr]['owners'][0]['email'] == username:
                org_id = response['organizations'][ctr]['org_id']
                break

        return org_id

    def test_user_profile(self):
        # test logging in with the password, the remaining versions will use the HTTP Authentication
        self.client.login(username='test_user@demo.com', password='test_pass')
        r = self.client.get('/api/v3/users/' + str(self.user.pk) + '/', follow=True)
        self.assertEqual(r.status_code, 200)

        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['first_name'], 'Jaqen')
        self.assertEqual(r['last_name'], "H'ghar")
        self.client.logout()

    def test_with_http_authorization(self):
        r = self.client.get(f'/api/v3/users/{self.user.pk!s}/', follow=True, data={}, **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertNotEqual(r, None)

    def test_organization(self):
        self.client.login(username='test_user@demo.com', password='test_pass')
        r = self.client.get('/api/v3/organizations/', follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)

        # {
        #     "organizations": [{
        #           "is_parent": true,
        #           "user_role": "owner",
        #           "sub_orgs": [],
        #           "number_of_users": 1,
        #           "id": 1,
        #           "owners": [
        #               {
        #                   "first_name": "Jaqen",
        #                   "last_name": "H'ghar",
        #                   "email": "test_user@demo.com",
        #                   "id": 1
        #               }
        #           ],
        #           "name": "",
        #           "created": "2016-09-16",
        #           "org_id": 1,
        #           "user_is_owner": true,
        #           "parent_id": 1,
        #           "cycles": []
        #           }]
        # }
        r = json.loads(r.content)
        self.assertEqual(len(r['organizations']), 1)
        self.assertEqual(len(r['organizations'][0]['sub_orgs']), 0)
        # Num buildings is no longer valid. The count of properties are in the cycle
        # self.assertEqual(r['organizations'][0]['num_buildings'], 0)
        self.assertEqual(len(r['organizations'][0]['owners']), 1)
        self.assertEqual(r['organizations'][0]['number_of_users'], 1)
        self.assertEqual(r['organizations'][0]['user_role'], 'owner')
        self.assertEqual(r['organizations'][0]['owners'][0]['first_name'], 'Jaqen')
        self.assertEqual(
            r['organizations'][0]['cycles'],
            [
                {
                    'name': str(date.today().year - 1) + ' Calendar Year',
                    'num_properties': 0,
                    'num_taxlots': 0,
                    'cycle_id': self.default_cycle.pk,
                },
                {
                    'name': 'Test Hack Cycle 2015',
                    'num_properties': 0,
                    'num_taxlots': 0,
                    'cycle_id': self.cycle.pk,
                },
            ],
        )

    def test_organization_details(self):
        r = self.client.get('/api/v3/organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        # get details on the organization
        r = self.client.get('/api/v3/organizations/' + str(organization_id) + '/', follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)

        # {
        #     "status": "success",
        #     "organization": {
        #         "sub_orgs": [],
        #         "num_buildings": 0,
        #         "owners": [
        #             {
        #                 "first_name": "Jaqen",
        #                 "last_name": "H'ghar",
        #                 "email": "test_user@demo.com",
        #                 "id": 2
        #             }
        #         ],
        #         "number_of_users": 1,
        #         "name": "",
        #         "user_role": "owner",
        #         "is_parent": true,
        #         "org_id": 2,
        #         "id": 2,
        #         "user_is_owner": true
        #     }
        # }

        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['organization']['number_of_users'], 1)
        self.assertEqual(len(r['organization']['owners']), 1)
        self.assertEqual(r['organization']['user_is_owner'], True)

    def test_update_user(self):
        user_payload = {'first_name': 'Arya', 'last_name': 'Stark', 'email': self.user.username}
        r = self.client.put(
            f'/api/v3/users/{self.user.pk}/', data=json.dumps(user_payload), content_type='application/json', **self.headers
        )

        # re-retrieve the user profile
        r = self.client.get('/api/v3/users/' + str(self.user.pk) + '/', follow=True, **self.headers)
        r = json.loads(r.content)

        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['first_name'], 'Arya')
        self.assertEqual(r['last_name'], 'Stark')

    def test_adding_user(self):
        r = self.client.get('/api/v3/organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)
        root = AccessLevelInstance.objects.get(organization_id=organization_id, depth=1)
        new_user = {
            'organization_id': organization_id,
            'first_name': 'Brienne',
            'last_name': 'Tarth',
            'email': 'test+1@demo.com',
            'role': 'member',
            'access_level_instance_id': root.id,
        }

        r = self.client.post(
            '/api/v3/users/?organization_id=' + str(organization_id),
            data=json.dumps(new_user),
            content_type='application/json',
            **self.headers,
        )
        self.assertEqual(r.status_code, 200)

        r = self.client.get('/api/v3/organizations/%s/' % organization_id, follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['organization']['number_of_users'], 2)

        # get org users
        r = self.client.get('/api/v3/organizations/%s/users/' % organization_id, content_type='application/json', **self.headers)
        self.assertEqual(r.status_code, 200)
        # {
        #     "status": "success",
        #     "users": [
        #         {
        #             "role": "owner",
        #             "first_name": "Jaqen",
        #             "last_name": "H'ghar",
        #             "user_id": 1,
        #             "email": "test_user@demo.com"
        #         },
        #         {
        #             "role": "member",
        #             "first_name": "Brienne",
        #             "last_name": "Tarth",
        #             "user_id": 2,
        #             "email": "test+1@demo.com"
        #         }
        #     ]
        # }

        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')
        self.assertEqual(len(r['users']), 2)

        # get the user id of the new user
        user_id = next(i for i in r['users'] if i['last_name'] == 'Tarth')['user_id']

        # Change the user role
        payload = {'organization_id': organization_id, 'role': 'owner'}

        r = self.client.put(
            f'/api/v3/users/{user_id}/role/?organization_id={organization_id}',
            data=json.dumps(payload),
            content_type='application/json',
            **self.headers,
        )
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')

        r = self.client.get('/api/v3/organizations/%s/users/' % organization_id, content_type='application/json', **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        new_user = next(i for i in r['users'] if i['last_name'] == 'Tarth')
        self.assertEqual(new_user['role'], 'owner')

    def test_get_query_threshold(self):
        r = self.client.get('/api/v3/organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        r = self.client.get('/api/v3/organizations/%s/query_threshold/' % organization_id, follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['query_threshold'], None)

    def test_shared_fields(self):
        r = self.client.get('/api/v3/organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        r = self.client.get('/api/v3/organizations/%s/shared_fields/' % organization_id, follow=True, **self.headers)

        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['public_fields'], [])

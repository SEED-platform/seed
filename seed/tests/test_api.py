# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import base64
import datetime
import json
import os
import time
from unittest import skip

from django.urls import reverse_lazy, reverse
from django.test import TestCase
from django.utils import timezone

from seed.landing.models import SEEDUser as User
from seed.models import (
    Cycle,
)
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

    def test_get_api_schema(self):
        """
        Test of 'schema' generator.
        """
        url = reverse('api:v2:schema')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        endpoints = json.loads(res.content)

        # the url we just hit should be in here
        self.assertTrue(url in endpoints)
        endpoint = endpoints[url]
        self.assertEqual(endpoint['name'], 'get_api_schema')
        self.assertTrue('description' in endpoint)


class TestApi(TestCase):
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
        self.default_cycle = Cycle.objects.filter(organization_id=self.org).first()
        self.cycle, _ = Cycle.objects.get_or_create(
            name='Test Hack Cycle 2015',
            organization=self.org,
            start=datetime.datetime(2015, 1, 1, tzinfo=timezone.get_current_timezone()),
            end=datetime.datetime(2015, 12, 31, tzinfo=timezone.get_current_timezone()),
        )
        auth_string = base64.urlsafe_b64encode(bytes(
            '{}:{}'.format(self.user.username, self.user.api_key), 'utf-8'
        ))
        self.auth_string = 'Basic {}'.format(auth_string.decode('utf-8'))
        self.headers = {'Authorization': self.auth_string}

    def get_org_id(self, dict, username):
        """Return the org id from the passed dictionary and username"""
        id = None
        for ctr in range(len(dict['organizations'])):
            if dict['organizations'][ctr]['owners'][0]['email'] == username:
                id = dict['organizations'][ctr]['org_id']
                break

        return id

    def test_user_profile(self):
        # test logging in with the password, the remaining versions will use the HTTP Authentication
        self.client.login(username='test_user@demo.com', password='test_pass')
        r = self.client.get('/api/v3/users/' + str(self.user.pk) + '/', follow=True)
        self.assertEqual(r.status_code, 200)

        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['first_name'], 'Jaqen')
        self.assertEqual(r['last_name'], 'H\'ghar')
        self.client.logout()

    def test_with_http_authorization(self):
        r = self.client.get(
            '/api/v3/users/{}/'.format(str(self.user.pk)),
            follow=True,
            data={},
            **self.headers
        )
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
        self.assertEqual(r['organizations'][0]['cycles'], [
            {
                'name': str(datetime.date.today().year - 1) + ' Calendar Year',
                'num_properties': 0,
                'num_taxlots': 0,
                'cycle_id': self.default_cycle.pk,
            }, {
                'name': 'Test Hack Cycle 2015',
                'num_properties': 0,
                'num_taxlots': 0,
                'cycle_id': self.cycle.pk,
            }])

    def test_organization_details(self):
        r = self.client.get('/api/v3/organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        # get details on the organization
        r = self.client.get('/api/v3/organizations/' + str(organization_id) + '/', follow=True,
                            **self.headers)
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
        user_payload = {
            'first_name': 'Arya',
            'last_name': 'Stark',
            'email': self.user.username
        }
        r = self.client.put('/api/v3/users/{}/'.format(self.user.pk), data=json.dumps(user_payload),
                            content_type='application/json', **self.headers)

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
        new_user = {
            'organization_id': organization_id,
            'first_name': 'Brienne',
            'last_name': 'Tarth',
            'email': 'test+1@demo.com',
            'role': 'member',
        }

        r = self.client.post('/api/v3/users/?organization_id=' + str(organization_id),
                             data=json.dumps(new_user),
                             content_type='application/json',
                             **self.headers)
        self.assertEqual(r.status_code, 200)

        r = self.client.get('/api/v3/organizations/%s/' % organization_id, follow=True,
                            **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['organization']['number_of_users'], 2)

        # get org users
        r = self.client.get('/api/v3/organizations/%s/users/' % organization_id,
                            content_type='application/json', **self.headers)
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
        user_id = [i for i in r['users'] if i['last_name'] == 'Tarth'][0]['user_id']

        # Change the user role
        payload = {
            'organization_id': organization_id,
            'role': 'owner'
        }

        r = self.client.put(
            '/api/v3/users/{}/role/?organization_id={}'.format(user_id, organization_id),
            data=json.dumps(payload),
            content_type='application/json',
            **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')

        r = self.client.get('/api/v3/organizations/%s/users/' % organization_id,
                            content_type='application/json', **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        new_user = [i for i in r['users'] if i['last_name'] == 'Tarth'][0]
        self.assertEqual(new_user['role'], 'owner')

    def test_get_query_threshold(self):
        r = self.client.get('/api/v3/organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        r = self.client.get("/api/v3/organizations/%s/query_threshold/" % organization_id,
                            follow=True,
                            **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['query_threshold'], None)

    def test_shared_fields(self):
        r = self.client.get('/api/v3/organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        r = self.client.get("/api/v3/organizations/%s/shared_fields/" % organization_id,
                            follow=True,
                            **self.headers)

        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['public_fields'], [])

    @skip('appears to be broken by use of login_required')
    def test_upload_buildings_file(self):
        r = self.client.get('/api/v3/organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        raw_building_file = os.path.abspath(
            os.path.join('seed/tests/data', 'covered-buildings-sample.csv'))
        self.assertTrue(os.path.isfile(raw_building_file), 'could not find file')

        payload = {'name': 'API Test'}

        # create the data set
        r = self.client.post('/api/v3/datasets/?organization_id=' + str(organization_id),
                             data=json.dumps(payload),
                             content_type='application/json',
                             **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')

        data_set_id = r['id']

        # retrieve the upload details
        upload_details = self.client.get('/api/v2/get_upload_details/', follow=True, **self.headers)
        self.assertEqual(upload_details.status_code, 200)
        upload_details = json.loads(upload_details.content)
        self.assertEqual(upload_details['upload_path'], '/api/v3/upload/')

        # create hash for /data/upload/
        fsysparams = {
            'import_record': data_set_id,
            'source_type': 'Assessed Raw',
            'file': open(raw_building_file, 'rb')
        }

        # upload data and check response
        r = self.client.post(upload_details['upload_path'], fsysparams, **self.headers)
        self.assertEqual(r.status_code, 200)

        r = json.loads(r.content)
        self.assertEqual(r['success'], True)
        import_file_id = r['import_file_id']
        self.assertNotEqual(import_file_id, None)

        # Save the data to the Property / TaxLots
        payload = {
            'cycle_id': self.cycle.id,
        }
        r = self.client.post('/api/v3/import_files/' + str(import_file_id) + '/start_save_data/?organization_id=' + organization_id,
                             data=json.dumps(payload),
                             content_type='application/json',
                             follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)

        # {
        #     "status": "success",
        #     "progress_key": ":1:SEED:save_raw_data:PROG:1"
        # }
        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')
        self.assertIsNotNone(r['progress_key'])
        time.sleep(15)

        # check the progress bar
        progress_key = r['progress_key']
        r = self.client.get(reverse_lazy('api:v3:progress-detail', args=[progress_key]),
                            content_type='application/json', follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)

        r = json.loads(r.content)
        # {
        #   "status": "success",
        #   "progress": 100,
        #   "progress_key": ":1:SEED:save_raw_data:PROG:1"
        # }
        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['progress'], 100)

        # Save the column mappings.
        payload = {
            'mappings': [
                {
                    'from_field': 'City',  # raw field in import file
                    'to_field': 'city',
                    'to_table_name': 'PropertyState',
                }, {
                    'from_field': 'Zip',  # raw field in import file
                    'to_field': 'postal_code',
                    'to_table_name': 'PropertyState',
                }, {
                    'from_field': 'GBA',  # raw field in import file
                    'to_field': 'gross_floor_area',
                    'to_table_name': 'PropertyState',
                }, {
                    'from_field': 'BLDGS',  # raw field in import file
                    'to_field': 'building_count',
                    'to_table_name': 'PropertyState',
                }, {
                    'from_field': 'UBI',  # raw field in import file
                    'to_field': 'jurisdiction_tax_lot_id',
                    'to_table_name': 'TaxLotState',
                }, {
                    'from_field': 'State',  # raw field in import file
                    'to_field': 'state_province',
                    'to_table_name': 'PropertyState',
                }, {
                    'from_field': 'Address',  # raw field in import file
                    'to_field': 'address_line_1',
                    'to_table_name': 'PropertyState',
                }, {
                    'from_field': 'Owner',  # raw field in import file
                    'to_field': 'owner',
                    'to_table_name': 'PropertyState',
                }, {
                    'from_field': 'Property Type',  # raw field in import file
                    'to_field': 'use_description',
                    'to_table_name': 'PropertyState',
                }, {
                    'from_field': 'AYB_YearBuilt',  # raw field in import file
                    'to_field': 'year_built',
                    'to_table_name': 'PropertyState',
                }
            ]
        }
        r = self.client.post(
            '/api/v3/organizations/' + str(organization_id) + '/column_mappings/?import_file_id=' + str(import_file_id),
            data=json.dumps(payload),
            content_type='application/json',
            follow=True,
            **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)

        # {
        #   "status": "success"
        # }
        self.assertEqual(r['status'], 'success')

        # Map the buildings with new column mappings.
        payload = {
            'remap': True,
        }
        r = self.client.post('/api/v3/import_files/' + str(import_file_id) + '/map/?organization_id=' + str(organization_id),
                             data=json.dumps(payload), content_type='application/json', follow=True,
                             **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)

        # {
        #     "status": "success",
        #     "progress_key": ":1:SEED:map_data:PROG:1"
        # }

        self.assertEqual(r['status'], 'success')
        self.assertNotEqual(r['progress_key'], None)

        # time.sleep(10)
        # TODO: create a loop to check the progress. stop when status is success

        # check the progress bar
        progress_key = r['progress_key']
        r = self.client.get('/api/v3/progress/{}/'.format(progress_key),
                            content_type='application/json', follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)

        r = json.loads(r.content)
        # {
        #   "status": "success",
        #   "progress": 100,
        #   "progress_key": ":1:SEED:map_data:PROG:1"
        # }

        # self.assertEqual(r['status'], 'success')
        # self.assertEqual(r['progress'], 100)

        # # Get the mapping suggestions
        r = self.client.post(
            '/api/v3/import_files/{}/mapping_suggestions/?organization_id={}'.format(import_file_id,
                                                                                     organization_id),
            content_type='application/json',
            follow=True,
            **self.headers
        )

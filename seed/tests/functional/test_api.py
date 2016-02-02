# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nlong
"""
import json
import os
import time

from django.test import TestCase
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.landing.models import SEEDUser as User


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
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        self.headers = {'HTTP_AUTHORIZATION': '%s:%s' % (self.user.username, self.user.api_key)}

    def get_org_id(self, dict, username):
        '''Return the org id from the passed dictionary and username'''
        id = None
        for ctr in range(len(dict['organizations'])):
            if dict['organizations'][ctr]['owners'][0]['email'] == username:
                id = dict['organizations'][ctr]['org_id']
                break

        return id

    def test_user_profile(self):
        # test logging in with the password, the remaining versions will use the HTTP Authentication
        self.client.login(username='test_user@demo.com', password='test_pass')
        r = self.client.get('/app/accounts/get_user_profile', follow=True)
        self.assertEqual(r.status_code, 200)

        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['user']['first_name'], 'Jaqen')
        self.assertEqual(r['user']['last_name'], 'H\'ghar')
        self.client.logout

    def test_with_http_authorization(self):
        r = self.client.get('/app/accounts/get_user_profile', follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertNotEqual(r, None)

    def test_organization(self):
        r = self.client.get('/app/accounts/get_organizations/', follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)

        # {
        # "organizations": [
        #   { "sub_orgs": [], "num_buildings": 0, "owners": [{...}],
        #     "number_of_users": 1, "name": "", "user_role": "owner", "is_parent": true, "org_id": 1, "id": 1,
        #     "user_is_owner": true}
        #   ]
        # }
        r = json.loads(r.content)
        self.assertEqual(len(r['organizations']), 1)
        self.assertEqual(len(r['organizations'][0]['sub_orgs']), 0)
        self.assertEqual(r['organizations'][0]['num_buildings'], 0)
        self.assertEqual(len(r['organizations'][0]['owners']), 1)
        self.assertEqual(r['organizations'][0]['number_of_users'], 1)
        self.assertEqual(r['organizations'][0]['user_role'], 'owner')
        self.assertEqual(r['organizations'][0]['owners'][0]['first_name'], 'Jaqen')
        self.assertEqual(r['organizations'][0]['num_buildings'], 0)

    def test_organization_details(self):
        r = self.client.get('/app/accounts/get_organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        # get details on the organization
        r = self.client.get('/app/accounts/get_organization/?organization_id=%s' % organization_id, follow=True,
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
        self.assertEqual(r['organization']['num_buildings'], 0)
        self.assertEqual(r['organization']['number_of_users'], 1)
        self.assertEqual(len(r['organization']['owners']), 1)
        self.assertEqual(r['organization']['user_is_owner'], True)

    def test_update_user(self):
        user_payload = {'user': {
            'first_name': 'Arya',
            'last_name': 'Stark',
            'email': self.user.username}
        }
        r = self.client.post('/app/accounts/update_user/', data=json.dumps(user_payload),
                             content_type='application/json', **self.headers)

        # re-retrieve the user profile
        r = self.client.get('/app/accounts/get_user_profile', follow=True, **self.headers)
        r = json.loads(r.content)

        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['user']['first_name'], 'Arya')
        self.assertEqual(r['user']['last_name'], 'Stark')

    def test_adding_user(self):
        r = self.client.get('/app/accounts/get_organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)
        new_user = {
            'organization_id': organization_id,
            'first_name': 'Brienne',
            'last_name': 'Tarth',
            'email': 'test+1@demo.com',
            'role': {
                'name': 'Member',
                'value': 'member'
            }
        }

        r = self.client.post('/app/accounts/add_user/', data=json.dumps(new_user), content_type='application/json',
                             **self.headers)
        self.assertEqual(r.status_code, 200)

        r = self.client.get('/app/accounts/get_organization/?organization_id=%s' % organization_id, follow=True,
                            **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['organization']['number_of_users'], 2)

        # get org users
        r = self.client.post('/app/accounts/get_organizations_users/', data='{"organization_id": %s}' % organization_id,
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
            'user_id': user_id,
            'role': 'owner'
        }

        r = self.client.post('/app/accounts/update_role/', data=json.dumps(payload), content_type='application/json',
                             **self.headers)

        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')

        r = self.client.post('/app/accounts/get_organizations_users/', data='{"organization_id": %s}' % organization_id,
                             content_type='application/json', **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        new_user = [i for i in r['users'] if i['last_name'] == 'Tarth'][0]
        self.assertEqual(new_user['role'], 'owner')

    def test_get_query_threshold(self):
        r = self.client.get('/app/accounts/get_organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        r = self.client.get("/app/accounts/get_query_threshold/?organization_id=%s" % organization_id, follow=True,
                            **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['query_threshold'], None)

    def test_shared_fields(self):
        r = self.client.get('/app/accounts/get_organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        r = self.client.get("/app/accounts/get_shared_fields/?organization_id=%s" % organization_id, follow=True,
                            **self.headers)

        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['public_fields'], [])
        self.assertEqual(r['shared_fields'], [])

    def test_upload_buildings_file(self):
        r = self.client.get('/app/accounts/get_organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        raw_building_file = os.path.relpath(os.path.join('seed/tests/data', 'covered-buildings-sample.csv'))
        self.assertTrue(os.path.isfile(raw_building_file), 'could not find file')

        payload = {'organization_id': organization_id, 'name': 'API Test'}

        # create the data set
        r = self.client.post('/app/create_dataset/', data=json.dumps(payload), content_type='application/json',
                             **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['status'], 'success')

        data_set_id = r['id']

        # retrieve the upload details
        upload_details = self.client.get('/data/get_upload_details/', follow=True, **self.headers)
        self.assertEqual(upload_details.status_code, 200)
        upload_details = json.loads(upload_details.content)
        self.assertEqual(upload_details['upload_mode'], 'filesystem')

        # create hash for /data/upload/
        fsysparams = {
            'qqfile': raw_building_file,
            'import_record': data_set_id,
            'source_type': 'Assessed Raw',
            'filename': open(raw_building_file, 'rb')
        }

        # upload data and check response
        r = self.client.post(upload_details['upload_path'], fsysparams, follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)

        r = json.loads(r.content)
        self.assertEqual(r['success'], True)
        import_file_id = r['import_file_id']
        self.assertNotEqual(import_file_id, None)

        # Save the data to BuildingSnapshots
        payload = {
            'file_id': import_file_id,
            'organization_id': organization_id
        }
        r = self.client.post('/app/save_raw_data/', data=json.dumps(payload), content_type='application/json',
                             follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)

        # {
        #     "status": "success",
        #     "progress_key": ":1:SEED:save_raw_data:PROG:1"
        # }
        r = json.loads(r.content)
        print(r)
        self.assertEqual(r['status'], 'success')
        self.assertNotEqual(r['progress_key'], None)
        time.sleep(15)

        # check the progress bar
        progress_key = r['progress_key']
        r = self.client.post('/app/progress/', data=json.dumps({'progress_key': progress_key}),
                             content_type='application/json', follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)

        r = json.loads(r.content)
        print(r)
        # {
        #   "status": "success",
        #   "progress": 100,
        #   "progress_key": ":1:SEED:save_raw_data:PROG:1"
        # }
        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['progress'], 100)

        # Save the column mappings.
        payload = {
            'import_file_id': import_file_id,
            'organization_id': organization_id
        }
        payload['mappings'] = [[u'city', u'City'],
                               [u'postal_code', u'Zip'],
                               [u'gross_floor_area', u'GBA'],
                               [u'building_count', u'BLDGS'],
                               [u'tax_lot_id', u'UBI'],
                               [u'state_province', u'State'],
                               [u'address_line_1', u'Address'],
                               [u'owner', u'Owner'],
                               [u'use_description', u'Property Type'],
                               [u'year_built', u'AYB_YearBuilt']]
        r = self.client.post('/app/save_column_mappings/', data=json.dumps(payload),
                             content_type='application/json', follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)

        # {
        #   "status": "success"
        # }
        self.assertEqual(r['status'], 'success')

        # Map the buildings with new column mappings.
        payload = {
            'file_id': import_file_id,
            'organization_id': organization_id
        }
        r = self.client.post('/app/remap_buildings/', data=json.dumps(payload),
                             content_type='application/json', follow=True, **self.headers)
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
        print progress_key
        r = self.client.post('/app/progress/', data=json.dumps({'progress_key': progress_key}),
                             content_type='application/json', follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)

        r = json.loads(r.content)
        print r
        # {
        #   "status": "success",
        #   "progress": 100,
        #   "progress_key": ":1:SEED:map_data:PROG:1"
        # }

        # self.assertEqual(r['status'], 'success')
        # self.assertEqual(r['progress'], 100)

        # # Get the mapping suggestions
        payload = {
            'import_file_id': import_file_id,
            'org_id': organization_id
        }
        r = self.client.post('/app/get_column_mapping_suggestions/', json.dumps(payload),
                             content_type='application/json', follow=True, **self.headers)
        print r


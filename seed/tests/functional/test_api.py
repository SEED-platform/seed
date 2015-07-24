import json
import os

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

        fsysparams = {
            'qqfile': raw_building_file,
            'import_record': data_set_id,
            'source_type': 'Assessed Raw'
        }

        #  files={'filename': open(raw_building_file, 'rb')},
        # print upload_details['upload_path']
        # r = self.client.post(upload_details['upload_path'], json.dumps(fsysparams),
        #                      content_type='application/json', **self.headers)
        # self.assertEqual(r.status_code, 200)
        # print r


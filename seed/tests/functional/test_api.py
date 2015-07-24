from django.test import TestCase
# from selenium.webdriver.firefox.webdriver import WebDriver

from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.landing.models import SEEDUser as User

import json


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
        r = json.loads(r.content)
        self.assertEqual(r['organization']['number_of_users'], 2)

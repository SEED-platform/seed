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

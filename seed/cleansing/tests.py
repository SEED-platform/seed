from django.test import TestCase
from django.core.urlresolvers import reverse

from tos.models import TermsOfService
from seed.landing.models import SEEDUser as User
from seed.cleansing.models import Cleansing


class UserLoginTest(TestCase):

    def setUp(self):
        self.user_details = {'username': 'testuser@example.com',
                             'email': 'testuser@example.com',
                             'password': 'test_password'}
        self.user = User.objects.create_user(**self.user_details)
        self.login_url = reverse('landing:login')

    def test_simple_login(self):
        self.client.post(self.login_url, self.user_details, secure=True)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_cleansing_init(self):
        c = Cleansing()
        self.assertTrue(c.rules_data)
        self.assertEqual(c.rules_data['modules'][0]['name'], u'Missing Matching Field')


    def test_cleanse_task(self):
        c = Cleansing()

        # c.do_something.delay
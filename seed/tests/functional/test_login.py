from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.firefox.webdriver import WebDriver

import logging
import time

from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.landing.models import SEEDUser as User

class LogIn(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(self):
        super(LogIn, self).setUpClass()
        self.selenium = WebDriver()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(LogIn, cls).tearDownClass()

    def test_login(self):
        user_details = {
            'username': 'test_user@demo.com', # the username needs to be in the form of an email.
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_user(**user_details)
        self.user.generate_key()
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        self.selenium.get('%s' % self.live_server_url)

        username_input = self.selenium.find_element_by_id("id_email")
        username_input.send_keys('test_user@demo.com')
        password_input = self.selenium.find_element_by_id("id_password")
        password_input.send_keys('test_pass')

        self.selenium.find_element_by_xpath('//input[@value="Log In"]').click()


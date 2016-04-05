# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located
)
from selenium.webdriver.support.wait import WebDriverWait

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test.client import Client

from seed.landing.models import SEEDUser
from seed.lib.superperms.orgs.models import Organization, OrganizationUser

import logging
_log = logging.getLogger(__name__)


class FunctionalLiveServerBaseTestCase(StaticLiveServerTestCase):
    capabilities = {
        'platform': 'OS X 10.11',
        'browserName': 'firefox',
        'version': '44',
        'javascriptEnabled': True,
        'selenium-version': '2.52.0',
        'loggingPrefs': {
            'browser': 'ALL',
        },
    }

    @classmethod
    def get_driver(cls):
        # Assume tests are being ran locally.
        if not os.getenv('TRAVIS') == 'true':
            return webdriver.Firefox()

        hub_url = "%s:%s@localhost:4445" % (os.getenv('SAUCE_USERNAME'), os.getenv('SAUCE_ACCESS_KEY'))
        print hub_url
        _log.error(hub_url)
        capabilities = {
            'tunnel-identifier': os.environ.get('TRAVIS_JOB_NUMBER'),
            'build': os.environ.get('TRAVIS_BUILD_NUMBER'),
            'name': '%s (%s)' % ('Build #%s' % os.environ.get('TRAVIS_JOB_NUMBER'), cls.__name__)
        }
        capabilities.update(cls.capabilities)

        driver = webdriver.Remote(
            desired_capabilities=capabilities,
            command_executor="http://%s/wd/hub" % hub_url
        )
        return driver

    @classmethod
    def setUpClass(cls):
        super(FunctionalLiveServerBaseTestCase, cls).setUpClass()
        cls.browser = cls.get_driver()

    def setUp(self):
        self.browser.implicitly_wait(30)

        # Generate User and Selenium Resources
        user_details = {
            'username': 'test@example.com',  # the username needs to be in the form of an email.
            'password': 'password',
            'email': 'test@example.com',
            'first_name': 'Jane',
            'last_name': 'Doe'
        }
        self.user = SEEDUser.objects.create_user(**user_details)
        self.user.generate_key()
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)
        self.headers = {'HTTP_AUTHORIZATION': '%s:%s' % (self.user.username, self.user.api_key)}

    def login(self):
        # Selenium will not set a cookie unless you've alreaday fetched a page from
        # said domain.
        self.browser.get('%s/' % self.live_server_url)

        # Log the user in using the Django test client's login method.
        client = Client()
        client.login(username=self.user.username, password='password')

        # Snag the cookie out of the client's cookies. Note that this is not
        # a normal dict, but an instance of SimpleCookie.
        cookie = client.cookies[settings.SESSION_COOKIE_NAME]

        # Add the cookie to our browser with values appropriately translated.
        set_to = {
            'name': cookie.key,
            'value': cookie.value,
            'domain': 'localhost',
            'path': '/',
            'secure': False
        }
        self.browser.add_cookie(set_to)

    def logout(self):
        self.browser.delete_cookie(settings.SESSION_COOKIE_NAME)

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super(FunctionalLiveServerBaseTestCase, cls).tearDownClass()

    # Helper methods
    def wait_for_element_by_css(self, selector, timeout=15):
        return WebDriverWait(self.browser, timeout).until(presence_of_element_located((By.CSS_SELECTOR, selector,)))


class LoggedInFunctionalTestCase(FunctionalLiveServerBaseTestCase):
    def setUp(self):
        super(LoggedInFunctionalTestCase, self).setUp()
        self.login()


class LoggedOutFunctionalTestCase(FunctionalLiveServerBaseTestCase):
    pass

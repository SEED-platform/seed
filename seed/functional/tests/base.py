# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located
)
from selenium.webdriver.support.wait import WebDriverWait

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test.client import Client

from seed.landing.models import SEEDUser
from seed.lib.superperms.orgs.models import Organization, OrganizationUser

################################################################################
#                            WARNING! HACK ALERT                               #
#                                                                              #
#   There's a bug with Firefox version >= 47.0 that prevents the Selenium      #
#   webdriver from working: https://github.com/SeleniumHQ/selenium/issues/2110 #
#   There is a fix coming:                                                     #
#   https://developer.mozilla.org/en-US/docs/Mozilla/QA/Marionette/WebDriver   #
#   In the meantime you can manually install it to get things working.         #
#   It will need to be on the sytem search path e.g. /usr/local/bin/wires      #
#                                                                              #
#   N.B it will need to be named wires not geckodriver                         #
#                                                                              #
#   The following is a hack to detect the browser version and check to see     #
#   if Marionette is installed and if so, use it.                              #
#                                                                              #
#   It should be removed when the upstream fix lands. Check if to see          #
#   if it has landed if your browser version > 47.0                            #
#                                                                              #
#                                                                              #
#   If you do please add the test_building_detail_th_resize test               #
#   from test_chrome to SmokeTests in test_firefox                             #
#                                                                              #
################################################################################

from distutils.spawn import find_executable
import errno
import subprocess
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

FIREFOX_IS_BROKEN = False
HAS_MARIONETTE = False

# Assume tests are being ran locally.
if not os.getenv('TRAVIS') == 'true':
    HAS_MARIONETTE = find_executable('wires')
    THIS_PATH = os.path.dirname(os.path.realpath(__file__))
    THIS_FILE = os.path.join(THIS_PATH, 'base.py')

    try:
        FIREFOX_VERSION = subprocess.check_output(
            ['firefox', '--version']).rstrip().split()[-1]
        FIREFOX_IS_BROKEN = FIREFOX_VERSION >= '47.0'
    except OSError as err:
        print "Can't find Firefox!"
        errmsg = os.strerror(errno.ENOPKG)
        errmsg += 'Firefox See: {}'.format(THIS_FILE)
        raise EnvironmentError(errno.ENOPKG, errmsg)

    if FIREFOX_IS_BROKEN and not HAS_MARIONETTE:
        errmsg = os.strerror(errno.ENOPKG)
        errmsg += ': Marionette. See: {}'.format(THIS_FILE)
        raise EnvironmentError(errno.ENOPKG, errmsg)


# Don't remove if hack is not longer needed, just remove
# elif FIREFOX_IS_BROKEN and HAS_MARIONETTE section
def get_webdriver(browser):
    if browser.lower() == 'chrome' and not os.getenv('TRAVIS') == 'true':
        driver = webdriver.Chrome()
    elif FIREFOX_IS_BROKEN and HAS_MARIONETTE:
        caps = DesiredCapabilities.FIREFOX
        caps["marionette"] = True
        caps["binary"] = find_executable('firefox')
        driver = webdriver.Firefox(capabilities=caps)
    else:
        driver = webdriver.Firefox()
    return driver

################################################################################
#                                    HACK ENDS                                 #
################################################################################

# FIXME: should this be hard coded?
FIREFOX_DEFINITION = {
    'platform': 'OS X 10.11',
    'browserName': 'firefox',
    'version': '44',
    'javascriptEnabled': True,
    'selenium-version': '2.52.0',
    'loggingPrefs': {
        'browser': 'ALL',
    },
}


class FunctionalLiveServerBaseTestCase(StaticLiveServerTestCase):

    @classmethod
    def get_capabilities(cls):
        capabilities = None
        if os.getenv('TRAVIS') == 'true':
            build_id = 'Build #{}'.format(os.environ.get('TRAVIS_JOB_NUMBER'))
            capabilities = {
                'tunnel-identifier': os.environ.get('TRAVIS_JOB_NUMBER'),
                'build': os.environ.get('TRAVIS_BUILD_NUMBER'),
                'name': '{} ({})'.format(build_id, cls.__name__)
            }

            # FIXME: should this be hard coded?
            capabilities.update(FIREFOX_DEFINITION)
        return capabilities

    @classmethod
    def setUpClass(cls):
        super(FunctionalLiveServerBaseTestCase, cls).setUpClass()
        cls.capabilities = cls.get_capabilities()

    def get_driver(self, browser):
        # Assume tests are being ran locally.
        if os.getenv('TRAVIS') == 'true':
            capabilities = self.get_capabilities()
            hub_url = "{}:{}@localhost:4445".format(
                os.getenv('SAUCE_USERNAME'), os.getenv('SAUCE_ACCESS_KEY')
            )
            driver = webdriver.Remote(
                desired_capabilities=capabilities,
                command_executor="http://{}/wd/hub".format(hub_url)
            )
        else:
            driver = get_webdriver(browser)
        return driver

    def setUp(self, browser=None):
        self.browser = self.get_driver(browser)
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

    def tearDown(self):
        self.browser.quit()
        super(FunctionalLiveServerBaseTestCase, self).tearDown()

    # Helper methods
    def wait_for_element_by_css(self, selector, timeout=15):
        return WebDriverWait(self.browser, timeout).until(presence_of_element_located((By.CSS_SELECTOR, selector,)))

    def get_action_chains(self):
        """
        Return an ActionChains instance that can be used to
        simulate user interactions.

        actions = self.get_action_chains()
        my_button = self.browser.find_element_by_id('my_button')
        actions.move_to_element(my_button)
        actions.click(my_button)
        actions.perform()

        assert my_button.text == 'You clicked the button!'
        """
        return ActionChains(self.browser)


class LoggedOutFunctionalTestCase(FunctionalLiveServerBaseTestCase):
    pass


class LoggedInFunctionalTestCase(FunctionalLiveServerBaseTestCase):
    def setUp(self):
        super(LoggedInFunctionalTestCase, self).setUp()
        self.login()


# N.B These require the Chorme webdriver to be installed
# See: https://sites.google.com/a/chromium.org/chromedriver/home

class LoggedInFunctionalTestCaseChrome(FunctionalLiveServerBaseTestCase):
    def setUp(self):
        super(LoggedInFunctionalTestCaseChrome, self).setUp('Chrome')
        self.login()


class LoggedOutFunctionalTestCaseChrome(FunctionalLiveServerBaseTestCase):
    def setUp(self):
        super(LoggedOutFunctionalTestCaseChrome, self).setUp('Chrome')

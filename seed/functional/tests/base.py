# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA

..warning::
    SEE README BEFORE EDITING THIS FILE!

:author Paul Munday<paul@paulmunday.net>
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

from seed.data_importer.models import ImportFile, ImportRecord
from seed.functional.tests.browser_definitions import BROWSERS
from seed.landing.models import SEEDUser
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import BuildingSnapshot, CanonicalBuilding


class FunctionalLiveServerBaseTestCase(StaticLiveServerTestCase):
    """
    Base class for Functioal/Selenium tests.

    Sets up browser and user for all tests. Includes helper methods.

    ..::WARNING
        Don't use this class directly for tests, use one of the subclasses.
    """

    # Magic! We need this since the class methods are only indirectly
    # invoked by the test runner, without it the tests won't run.
    def runTest(self):
        pass

    def get_capabilities(self):
        # used by Travis/Sauce Labs
        capabilities = None
        if os.getenv('TRAVIS') == 'true':
            build_id = 'Build #{}'.format(os.environ.get('TRAVIS_JOB_NUMBER'))
            capabilities = {
                'tunnel-identifier': os.environ.get('TRAVIS_JOB_NUMBER'),
                'build': os.environ.get('TRAVIS_BUILD_NUMBER'),
                'name': '{} ({})'.format(build_id, self.__class__.__name__)
            }
            capabilities.update(self.browser_type.capabilities)
        return capabilities

    def get_driver(self):
        """Sets the right driver for the platform the tests are run on."""
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
            driver = self.browser_type.driver()
        return driver

    def setUp(self):
        """Generate Selnium resources/browser and a user for tests."""
        self.browser = self.get_driver()
        self.browser.implicitly_wait(30)

        # Generate User and Selenium Resources
        user_details = {
            # the username needs to be in the form of an email.
            'username': 'test@example.com',
            'password': 'password',
            'email': 'test@example.com',
            'first_name': 'Jane',
            'last_name': 'Doe'
        }
        self.user = SEEDUser.objects.create_user(**user_details)
        self.user.generate_key()
        self.org = Organization.objects.create()
        self.org_user = OrganizationUser.objects.create(
            user=self.user, organization=self.org)
        self.headers = {
            'HTTP_AUTHORIZATION': '{}:{}'.format(
                self.user.username, self.user.api_key
            )
        }

    def login(self):
        """Login the test user."""
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
        """Logout the test user."""
        self.browser.delete_cookie(settings.SESSION_COOKIE_NAME)

    def tearDown(self):
        """Close browser and delete user."""
        self.browser.quit()
        self.org_user.delete()
        self.org.delete()
        self.user.delete()
        super(FunctionalLiveServerBaseTestCase, self).tearDown()

    # Helper methods
    def wait_for_element_by_css(self, selector, timeout=15):
        """
        Get a page element by css, allowing time for the page to load.

        :returns WebElement.
        """
        return WebDriverWait(self.browser, timeout).until(presence_of_element_located((By.CSS_SELECTOR, selector,)))

    def get_action_chains(self):
        """
        Return an ActionChains instance that can be used to
        simulate user interactions.

        :returns selenium.webdriver.common.action_chains.ActionChains

        :Example:

        actions = self.get_action_chains()
        my_button = self.browser.find_element_by_id('my_button')
        actions.move_to_element(my_button)
        actions.click(my_button)
        actions.perform()

        assert my_button.text == 'You clicked the button!'
        """
        return ActionChains(self.browser)

    def create_import(self, **kw):
        """
        Create an ImportRecord object and the associated ImportFile.

        Set up a minimal ImportRecords and ImportFile sufficient to run a
        test. The import record contains only the owner and super_organization
        and by default, the ImportFile only references the ImportRecord.

        Any keywords supplied will be passed to ImportFile.object.create

        :param **kw: keywords passed to ImportFile.object.create

        :returns: ImportFile, ImportRecord

        :Example:

        import_file = self.create_import_file()
        import_file = self.create_import_file(source_type='csv')
        """
        import_record = ImportRecord.objects.create(
            owner=self.user,
            super_organization=self.org
        )
        import_file = ImportFile.objects.create(
            import_record=import_record, **kw
        )
        return import_file, import_record

    def create_building(self, import_file, **kw):
        """
        Create a CanonicalBuilding and an associated BuildingSnapshot.

        Set up a minimal CanonicalBuilding and BuildingSnapshot suitable for
        use in tests. The defaults for the BuildingSnapshot set the
        super_organization, the import file (as supplied) and address_line_1
        with a value of 'address'. Any supplied keywords will be passed to
        BuildingSnapshot.objects.create and will overide the defaults.

        :param import_file: an ImportFile object (created by create_import_file)
        : param **kw: keywords passed to BuildingSnapshot.objects.create

        :returns: CanonicalBuilding instance
        """
        canonical_building = CanonicalBuilding.objects.create()
        snapshot_params = {
            'super_organization': self.org,
            'import_file': import_file,
            'canonical_building': canonical_building,
            'address_line_1': 'address'
        }
        snapshot_params.update(kw)
        building = BuildingSnapshot.objects.create(**snapshot_params)
        canonical_building.canonical_snapshot = building
        canonical_building.save()
        return canonical_building


class LoggedInFunctionalTestCase(FunctionalLiveServerBaseTestCase):
    """Private class for inheritance"""
    def setUp(self):
        super(LoggedInFunctionalTestCase, self).setUp()
        self.login()


def loggedOutFunctionalTestCaseFactory(browser):
    """
    Dynamically create a browser specific LoggedOutFunctionalTestCase class.

    e.g. loggedOutFunctionalTestCaseFactory(firefox) generates
    LoggedOutFunctionalTestCaseFirefox.
    """
    classname = get_classname('LoggedOutFunctionalTestCase', browser.name)
    return type(
        classname, (FunctionalLiveServerBaseTestCase, ),
        {'browser_type': browser}
    )


def loggedInFunctionalTestCaseFactory(browser):
    """
    Dynamically create a browser specific LoggedInFunctionalTestCase class.

    e.g. loggedInFunctionalTestCaseFactory(firefox) generates
    LoggedInFunctionalTestCaseFirefox.
    """
    classname = get_classname('LoggedInFunctionalTestCase', browser.name)
    return type(
        classname, (LoggedInFunctionalTestCase, ),
        {'browser_type': browser}
    )


def get_classname(classname, browser):
    """Return a browser specific class name."""
    return "{}{}".format(classname, browser)


# Dynamically create Test Classes for browsers named in BROWSERS
LOGGED_IN_CLASSES = {}
LOGGED_OUT_CLASSES = {}
for browser in BROWSERS:
    bname = browser.name
    LOGGED_IN_CLASSES[bname] = loggedInFunctionalTestCaseFactory(browser)
    LOGGED_OUT_CLASSES[bname] = loggedOutFunctionalTestCaseFactory(browser)

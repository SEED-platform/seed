# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA

.. warning::

    SEE README BEFORE EDITING THIS FILE!

.. codeauthor:: Paul Munday<paul@paulmunday.net>
"""
from __future__ import print_function
import os
import sys

import mock

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located
)
from selenium.webdriver.support.wait import WebDriverWait

from django.db.models.fields.files import FieldFile
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test.client import Client

from seed.data_importer.models import ImportFile, ImportRecord
from seed.functional.tests.browser_definitions import BROWSERS
from seed.test_helpers.fake import FakeBuildingSnapshotFactory
from seed.landing.models import SEEDUser
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.lib.superperms.orgs.models import ROLE_LEVEL_CHOICES
from seed.lib.superperms.orgs.exceptions import TooManyNestedOrgs
from seed.models import CanonicalBuilding
from seed.models import Project, ProjectBuilding


STRATEGIES = {
    'CLASS_NAME': By.CLASS_NAME,
    'CSS_SELECTOR': By.CSS_SELECTOR,
    'ID': By.ID,
    'LINK_TEXT': By.LINK_TEXT,
    'NAME': By.NAME,
    'PARTIAL_LINK_TEXT': By.PARTIAL_LINK_TEXT,
    'TAG_NAME': By.TAG_NAME,
    'XPATH': By.XPATH,
}

USER_ROLES = {role[1]: role[0] for role in ROLE_LEVEL_CHOICES}


class FunctionalLiveServerBaseTestCase(StaticLiveServerTestCase):
    """
    Base class for Functional/Selenium tests.

    Sets up browser and user for all tests. Includes helper methods.

    .. warning::
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
        """Generate Selenium resources/browser and a user for tests."""
        self.browser = self.get_driver()

        # Generate User and Selenium Resources
        user_details = {
            # the username needs to be in the form of an email.
            'username': 'test@example.com',
            'password': 'password',
            'email': 'test@example.com',
            'first_name': 'Jane',
            'last_name': 'Doe'
        }
        self.user = self.create_user(generate_key=True, **user_details)
        self.org, self.org_user = self.create_org(name='Org')
        self.headers = {
            'HTTP_AUTHORIZATION': '{}:{}'.format(
                self.user.username, self.user.api_key
            )
        }
        num_owners = getattr(self, 'num_owners', 5)
        self.building_factory = FakeBuildingSnapshotFactory(
            super_organization=self.org,
            num_owners=num_owners
        )

    def login(self):
        """Login the test user."""
        # Selenium will not set a cookie unless you've already fetched a page
        # from said domain.
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
        """Log out the test user."""
        self.browser.delete_cookie(settings.SESSION_COOKIE_NAME)

    def tearDown(self):
        """Close browser and delete user."""
        # delete all org_users
        OrganizationUser.objects.all().delete()
        # delete all orgs (in case there are sub orgs)
        OrganizationUser.objects.all().delete()
        # delete all users
        SEEDUser.objects.all().delete()
        self.browser.quit()
        super(FunctionalLiveServerBaseTestCase, self).tearDown()

    # Helper methods

    def wait_for_element(self, strategy, search, timeout=15):
        """
        Get a page element, allowing time for the page to load.

        :returns: WebElement.

        """
        return WebDriverWait(self.browser, timeout).until(
            presence_of_element_located(
                (STRATEGIES[strategy], search,)
            )
        )

    def wait_for_element_by_css(self, selector, timeout=15):
        """
        Get a page element by css, allowing time for the page to load.

        :returns: WebElement

        """
        return self.wait_for_element('CSS_SELECTOR', selector, timeout=timeout)

    def get_action_chains(self):
        """
        Return an Action Chains instance that can be used to
        simulate user interactions.

        :returns: selenium.webdriver.common.action_chains.ActionChains

        Example::
        actions = self.get_action_chains()
        my_button = self.browser.find_element_by_id('my_button')
        actions.move_to_element(my_button)
        actions.click(my_button)
        actions.perform()

        assert my_button.text == 'You clicked the button!'
        """
        return ActionChains(self.browser)

    def create_import(self, name=None, mock_file=None, **kw):
        """
        Create an ImportRecord object and the associated ImportFile.

        Set up a minimal ImportRecords and ImportFile sufficient to run a
        test. The import record contains only the owner and super_organization
        and by default, the ImportFile only references the ImportRecord.

        As ImportFile.file is a django.db.models.FileField field it can be tricky
        to manipulate/mock. Use mock_file to pass in a mock_file instance
        generated by mock_file_factory. This will be added after the record is
        created and can be used to set the file  name etc.

        Any other keywords supplied will be passed to ImportFile.objects.create

        :param: name: a name for the Import Record
        :param: mock_file: Attach a mock_file to the Import File.
        :param kw: keywords passed to ImportFile.objects.create

        :type: name: string
        :type: mock_file: a mock_file instance generated by mock_file_factory.
        :returns: ImportFile, ImportRecord

        Example::
        import_file = self.create_import_file()
        import_file = self.create_import_file(source_type='csv')

        >>> from seed.functional.tests.base import mock_file_factory
        >>> mock_file = mock_file_factory('myfile.csv')
        >>> import_record, import_file = self.create_import_file(mock_file=mock_file)
        >>> import_file.filename_only
        myfile
        >>> assert import_file.filename_only == mock_file.base_name
        True
        """
        name = name if name else "Unamed Dataset"
        import_record = ImportRecord.objects.create(
            name=name,
            owner=self.user,
            super_organization=self.org
        )
        import_file = ImportFile.objects.create(
            import_record=import_record, **kw
        )
        if mock_file:
            import_file.file = mock_file
            import_file.save()
        return import_file, import_record

    def create_import_record(self, name=None, **kw):
        """
        Create an ImportRecord object and the associated ImportFile.

        Set up a minimal ImportRecord sufficient to run a
        test. The import record contains only the owner and super_organization
        by default.

        :param: name: a name for the Import Record/Dataset
        :param kw: keywords passed to ImporRecors.objects.create

        :type: name: string
        :returns: ImportRecord

        Example::
        import_file = self.create_import_record(name="Test Dataset")
        import_file = self.create_import_file(source_type='csv')

        >>> from seed.functional.tests.base import mock_file_factory
        >>> mock_file = mock_file_factory('myfile.csv')
        >>> import_record, import_file = self.create_import_file(mock_file=mock_file)
        >>> import_file.filename_only
        myfile
        >>> assert import_file.filename_only == mock_file.base_name
        True
        """
        name = name if name else "Unamed Dataset"
        import_record = ImportRecord.objects.create(
            name=name,
            owner=self.user,
            super_organization=self.org,
            **kw
        )
        return import_record

    def create_import_file(self, import_record, mock_file=None, **kw):
        """
        Create an ImportRecord object and the associated ImportFile.

        Set up a  ImportFile sufficient to run a test and attach it to an Import
        Record. By default, the ImportFile only references the ImportRecord.

        As ImportFile.file is a django.db.models.FileField field it can be tricky
        to manipulate/mock. Use mock_file to pass in a mock_file instance
        generated by mock_file_factory. This will be added after the record is
        created and can be used to set the file  name etc.

        Any other keywords supplied will be passed to ImportFile.objects.create

        :param: import_record: Import Record the Import File will be attached to
        :param: mock_file: Attach a mock_file to the Import File.
        :param: kw: keywords passed to ImportFile.objects.create

        :type: import_record: ImportRecord instance
        :type: mock_file: a mock_file instance generated by mock_file_factory.
        :returns: ImportFile

        Example::
        import_file = self.create_import_file()
        import_file = self.create_import_file(source_type='csv')

        >>> from seed.functional.tests.base import mock_file_factory
        >>> mock_file = mock_file_factory('myfile.csv')
        >>> import_record, import_file = self.create_import_file(mock_file=mock_file)
        >>> import_file.filename_only
        myfile
        >>> assert import_file.filename_only == mock_file.base_name
        True
        """
        import_file = ImportFile.objects.create(
            import_record=import_record, **kw
        )
        if mock_file:
            import_file.file = mock_file
            import_file.save()
        return import_file

    def create_building(self, import_file, **kw):
        """
        Create a CanonicalBuilding and an associated BuildingSnapshot.

        Set up a minimal CanonicalBuilding and BuildingSnapshot suitable for
        use in tests. The defaults for the BuildingSnapshot set the
        super_organization, the import file (as supplied) and address_line_1
        with a value of 'address'. Any supplied keywords will be passed to
        BuildingSnapshot.objects.create and will override the defaults.

        :param:import_file: an ImportFile object (created by create_import_file)
        :param: kw: keywords passed to BuildingSnapshot.objects.create

        :returns: CanonicalBuilding instance

        """
        canonical_building = CanonicalBuilding.objects.create()
        snapshot_params = {
            'super_organization': self.org,
            'import_file': import_file,
            'canonical_building': canonical_building,
        }
        if 'address_line_1' not in kw:
            snapshot_params.update({'address_line_1': 'address'})
        snapshot_params.update(kw)
        building = self.building_factory.building_snapshot(**snapshot_params)
        canonical_building.canonical_snapshot = building
        canonical_building.save()
        return canonical_building

    def generate_buildings(self, num, import_file, **kw):
        """
        Create num CanonicalBuildings and associated BuildingSnapshots.

        Set up multiple CanonicalBuilding and BuildingSnapshots  for
        use in tests. The defaults for the BuildingSnapshot set the
        super_organization, the import file (as supplied). Any supplied
        keywords will be passed to BuildingSnapshot.objects.create
        and will override the defaults.

        The buildings themselves will be populated with pseudo-random,
        but predictable data, see first_500_buildings.csv for details

        :param:import_file: an ImportFile object (created by create_import_file)
        :param: num: number of buildings to create
        :param: kw: keywords passed to BuildingSnapshot.objects.create

        """
        for _ in range(num):
            canonical_building = CanonicalBuilding.objects.create()
            snapshot_params = {
                'super_organization': self.org,
                'import_file': import_file,
                'canonical_building': canonical_building,
            }
            snapshot_params.update(kw)
            building = self.building_factory.building_snapshot(
                **snapshot_params
            )
            canonical_building.canonical_snapshot = building
            canonical_building.save()

    def get_canonical_building(self, building_id):
        """
        Get a canonical building.

        :param: building_id: id of building
        :type: building_id: int

        """
        return CanonicalBuilding.objects.get(pk=building_id)

    def create_org(self, is_sub_org=False, parent=None, name=None, user=None):
        """
        Create an organization.

        :param: :is_sub_org: is this a child of another org. default False
        :param: parent: parent if sub_org, default self.org.
        :param: name: name of org: default 'Test'
        :param: user: user to add as organization owner, default is self.user

        :type: is_sub_org: bool
        :type: parent: Organization instance. self.org if None and is_sub_org
        :type: name: None, string
        :type: user: None, SEEDUser instance

        :returns: org, org_user

        """
        if parent and not isinstance(parent, Organization):
            errmsg = "parent must be an Organization"
            raise TypeError(errmsg)
        if is_sub_org and not parent:
            parent = self.org
        name = name if isinstance(name, basestring) else "Test"
        if user:
            if not isinstance(user, SEEDUser):
                errmsg = "user must be a SEEDUser or None"
                raise TypeError(errmsg)
        else:
            user = self.user

        org = Organization.objects.create(name=name)
        org_user = self.create_org_user(user=user, org=org)

        if is_sub_org:
            org.parent_org = parent
            try:
                org.save()
            except TooManyNestedOrgs as error:
                org.delete()
                raise error
        return org, org_user

    def create_org_user(self, user=None, org=None, role=None):
        """
        Create an OrganizationUser.

        Role should be one of viewer/member/owner (or the int representing
        the equivalent ROLE_LEVEL).

        :param: user: user to add to organization user, default is self.user
        :param: org: organization to add, default is self.organization
        :param: role: role of user, default is owner.

        :type: user: None, SEEDUser instance
        :type: org: None, Organization instance
        :type: role: string/int enumerated in USER_ROLES, case insensitive

        :returns: org_user

        """
        if user:
            if not isinstance(user, SEEDUser):
                errmsg = "user must be a SEEDUser or None"
                raise TypeError(errmsg)
        else:
            user = self.user

        if org:
            if not isinstance(org, Organization):
                errmsg = "org must be a instance of Organization or None"
                raise TypeError(errmsg)
        else:
            org = self.org

        if role:
            if isinstance(role, basestring) and role.title() in\
                    USER_ROLES.keys():
                role_level = USER_ROLES[role.title()]
            elif isinstance(role, int) and role in USER_ROLES.values():
                role_level = role
            else:
                errmsg = "Role must None or one of {} or {}".format(
                    str(USER_ROLES.keys()), str(USER_ROLES.values())
                )
                raise TypeError(errmsg)
        else:
            role_level = USER_ROLES['Owner']
        org_user = OrganizationUser.objects.create(
            user=user, organization=org, role_level=role_level
        )
        return org_user

    def create_sub_org(self, name=None):
        """
        Create a sub organization.

        :param: name: name of org. default: Sub Org
        :type: name: string, None

        :return: Sub Org

        """
        name = name if isinstance(name, basestring) else "Sub Org"
        return self.create_org(is_sub_org=True, name=name)

    def create_project(self, name=None, building=None):
        """
        Create a project and (optionally) a project building.

        :param: name: project name
        :param: :building: canonical building

        :type: name: string
        :type: building: CanonicalBuilding instance

        :returns: project, project building/None

        """
        name = name if name else 'test'
        project_building = None
        project = Project.objects.create(
            name=name, owner=self.user,
            super_organization=self.org
        )
        if building:
            project_building = ProjectBuilding.objects.create(
                project=project,
                building_snapshot=building.canonical_snapshot
            )
        return project, project_building

    def create_user(self, generate_key=None, **kw):
        """
        Create a SEEDUser.
        default username/password: test_user@example.com/password

        keywords are passed through to SEEDUser.objects.create_user.

        :param: create_key: Create an API Key for the User: default No.
        :type: create_key: bool or None

        :returns: user

        """
        user_details = {
            # the username needs to be in the form of an email.
            'username': 'test_user@example.com',
            'password': 'password',
        }
        user_details.update(kw)
        user = SEEDUser.objects.create_user(**user_details)
        if generate_key:
            user.generate_key()
        return user

    def set_buildings_list_columns(self, column_list):
        """
        Set the columns to display in the Buildings list view.
        address_line_1 is always added if not present.

        :param: column_list: list of columns to display
        :type: column_list: list (or string if a single column is supplied)

        """
        if not isinstance(column_list, list):
            column_list = [column_list]
        if 'address_line_1' not in column_list:
            column_list.append('address_line_1')
        self.user.default_custom_columns = column_list
        self.user.save()


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


def eprint(*args, **kwargs):
    """Print to standard error."""
    print(*args, file=sys.stderr, **kwargs)


def mock_file_factory(name, size=None, url=None, path=None):
    """
    This creates a mock instance of a FieldFile from
    django.db.models.fields.files.

    This is used to represent a file stored in Django and is linked file storage
    so it handles uploading and saving to disk.

    The mock allow you to set the file name etc without having to save a file to disk.
    """
    mock_file = mock.MagicMock(spec=FieldFile)
    mock_file._committed = True
    mock_file.file_name = name
    mock_file.base_name = os.path.splitext(name)[0]
    mock_file.__unicode__.return_value = name

    def __eq__(other):
        if hasattr(other, 'name'):
            return name == other.name
        else:
            return name == other
    mock_file.__eq__.side_effect = __eq__

    def __ne__(other):
        return not __eq__(other)

    mock_file.__ne__.side_effect = __ne__
    mock_file._get_size.return_value = size
    mock_size = mock.PropertyMock(return_value=size)
    type(mock_file).size = mock_size
    mock_file._get_path.return_value = path
    mock_path = mock.PropertyMock(return_value=path)
    type(mock_file).path = mock_path
    mock_file._get_url.return_value = url
    mock_url = mock.PropertyMock(return_value=url)
    type(mock_file).url = mock_url
    mock_file._get_closed.return_value = True
    mock_closed = mock.PropertyMock(return_value=True)
    type(mock_file).closed = mock_closed
    return mock_file


# Dynamically create Test Classes for browsers named in BROWSERS
LOGGED_IN_CLASSES = {}
LOGGED_OUT_CLASSES = {}
for browser in BROWSERS:
    bname = browser.name
    LOGGED_IN_CLASSES[bname] = loggedInFunctionalTestCaseFactory(browser)
    LOGGED_OUT_CLASSES[bname] = loggedOutFunctionalTestCaseFactory(browser)

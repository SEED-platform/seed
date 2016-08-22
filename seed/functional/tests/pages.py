
# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA

This module defines Page objects representing view in SEED.

:Example:

Defining a page object
======================

Class definition::

    class Home(Page):
        def __init__(self, test_obj):
            url = "/index.html"
            self.locator = Locator('NAME', 'my-button')
            super(Home, self).__init__(test_obj, locator, url=url)
        self.load_page()

.. warning::

    a locator must be defined and passed to super(Class, self)__init__

Calling the page object in a test::

    from seed.functional.tests.browser_definitions import import BROWSERS
    from seed.functional.tests.base import LOGGED_IN_CLASSES
    from seed.functional.tests.pages import Home


    def my_tests_generator():
        for browser in BROWSERS:

            class Tests((LOGGED_OUT_CLASSES[browser.name]):

            def my_test(self):
                home_page = Home(self)
                my_element = home_page.get_element_by_name('example')
                assert my_element.text = 'example text'

:Example:

Defining the Page Object for a page with a table
================================================

Class definition::

    class Home(Page):
        def __init__(self, test_obj):
            url = "index.html"
            locator = Locator('NAME', 'my-button')
            # will cause ensure_table_is_loaded method to be added
            self.table_locator = Locator('XPATH', '//table')
            super(Home, self).__init__(test_obj, locator, url=url)
            self.load_page()

Calling the table object in a test::

    from seed.functional.tests.browser_definitions import import BROWSERS
    from seed.functional.tests.base import LOGGED_IN_CLASSES
    from seed.functional.tests.pages import Home


    def my_tests_generator():
        for browser in BROWSERS:

            class Tests((LOGGED_OUT_CLASSES[browser.name]):

            def my_test(self):
                home_page = Home(self)
                table = home.page.ensure_table_is_loaded()
                assert table[0][0].text = 'example text'

:author: Paul Munday<paul@paulmunday.net>

"""
from seed.functional.tests.page import (
    Locator, Organization, Page, Table, TableRow, table_factory
)


class AccountsPage(Page):
    """
    Page object for the Organizations/account page. app/#/accounts

    An import record and building will be created if url is True.
    An accounts page object will have an org attribute. This is
    self.org from the test case.
    It may also have a 'sub_org' attribute. It is only present if
    a sub_org exists. The sub_org will either be test_obj.sub_org if it
    already exists when the object is initialized, otherwise the first sub_org
    created.

    :param: use_url: if True load by url, if False assume page is loaded
    :create_import: create an Import record (with building) if true
    :param import_file: define additional attributes of the import file
    :param building: define additional attributes of the building snapshot
    :sub_org: create a SubOrganization if True or string(name) or list (names).

    :type: url: bool ,None.
    :type: create_import: bool, None
    :type: import_file: dict
    :type: building: dict
    :type: sub_org: bool, string

    """
    def __init__(self, test_obj, use_url=None, create_import=None,
                 import_file=None, building=None, sub_org=None):
        locator = Locator('ID', 'org-owned-tables')
        sub_org_name = sub_org if isinstance(sub_org, basestring) else None
        url = "app/#/accounts" if use_url else None

        super(AccountsPage, self).__init__(
            test_obj, locator, url=url
        )

        # page set up
        if create_import:
            imports, self.canonical_building = self.create_record(
                create_building=True,
                import_file=import_file,
                building=building
            )
            self.building_id = self.canonical_building.id
            self.import_file = imports.import_file
            self.import_record = imports.import_record

        self.org = getattr(test_obj, 'org', None)
        self.sub_org = getattr(test_obj, 'sub_org', None)
        if sub_org:
            if not isinstance(sub_org, list):
                sub_org = [sub_org]
            for name in sub_org:
                sub_org = test_obj.create_sub_org(name=sub_org_name)
                if not self.sub_org:
                    self.sub_org = sub_org
        if not self.sub_org:
            del self.sub_org
        self.load_page()

    def create_sub_org(self, name):
        """Create a sub organization"""
        is_self_sub_org = False
        sub_org = self.test_obj.create_sub_org(name=name)
        if not self.sub_org:
            self.sub_org = sub_org
            is_self_sub_org = True
        return sub_org, is_self_sub_org

    def get_managed_org_tables(self):
        """
        Return a list of managed(owned) organizations.

        Each organization is a named tuple of type Organization.
        Organization.org is a TableRow for the organization.
        Organization.sub_orgs is a list containing sub-organizations if any.

        If there are sub orgs/the org is parent org, or capable of being so,
        the first row of sub orgs is a TableRow whose first cell is the
        (header) text 'Sub-Organizations', and whose  second contains the
        'Create new sub-organization' link.

        Then any sub orgs will be listed.
        All TableRows have two parts: the first cell contains the organization
        name (or 'Sub-Organizations') the second the controls i.e. links to
        'Settings' and 'Members' if its  a sub/child organization,
        'Settings', 'Sharing', 'Data', 'Cleansing', 'Sub-Organizations',
        'Members' if it's a parent organization.

        The keys are 'ORGANIZATION' and 'Col_1' respectively.
        """
        orgs = []
        orgs_div = self.wait_for_element_by_id('org-owned-tables')
        tables = orgs_div.find_elements_by_tag_name('table')
        for table in tables:
            parent = None
            sub_orgs = []
            body = table.find_element_by_tag_name('tbody')
            rows = body.find_elements_by_tag_name('tr')
            parent_row = rows[0]
            parent = TableRow([
                (
                    'ORGANIZATION',
                    parent_row.find_element_by_class_name('parent_org')
                ),
                ('Col_1', parent_row.find_element_by_class_name('right'))
            ])
            # sub orgs has hidden row
            if len(rows) > 2:
                cells = rows[1].find_elements_by_class_name('sub_head')
                sub_orgs.append(TableRow(
                    [('ORGANIZATION', cells[0]), ('Col_1', cells[1])]
                ))
                for row in rows[2:]:
                    cells = row.find_elements_by_class_name('account_org')
                    sub_orgs.append(TableRow(
                        [('ORGANIZATION', cells[0]), ('Col_1', cells[1])]
                    ))
            orgs.append(Organization(parent, sub_orgs))
        self.managed_orgs = orgs
        return orgs

    def get_member_orgs_table(self):
        """
        Return a the table of organizations the user belongs to.
        """
        container_div = self.wait_for_element_by_id('org-member-tables')
        table_element = container_div.find_element_by_tag_name('table')
        return table_factory(table_element)


class BuildingInfo(Page):
    """
    Page object for the building details page.

    The page will load directly(by url) if create_record or a building_id
    is set.

    Pass a dictionary to create_building to define additional attributes of
    building record/snapshot.

    building_id and create_building are mutually exclusive. building_id
    will take priority. If create project is true and there is a building
    (i.e. create_building or building id is True), it will be added to the
    project.

    :param: building_id: Canonical building id, page will load by url if set.
    :param: create_building: Create a building when instantiating.
    :param: create_project: Create a project . Supply string for project name.
    :param import_file: define additional attributes of the import file.

    :type: building_id: int
    :type: create_building: bool, None or dict
    :type: create_project: bool, string, None
    :type: import_file: dict

    """
    def __init__(self, test_obj, building_id=None, create_building=None,
                 create_project=None, import_file=None):
        if building_id or create_building:
            url = "app/#/buildings"
        else:
            url = None
        locator = Locator('ID', 'building')
        # will cause ensure_table_is_loaded method to be added
        self.table_locator = Locator('XPATH', '//table')

        super(BuildingInfo, self).__init__(
            test_obj, locator, url=url
        )
        # create building record
        if create_building and not building_id:
            imports, self.canonical_building = self.create_record(
                create_building=True,
                import_file=import_file,
                building=create_building
            )
            building_id = self.canonical_building.id
            self.import_file = imports.import_file
            self.import_record = imports.import_record
        elif building_id:
            self.canonical_building = self.get_canonical_building(
                id=building_id)
        self.building_id = building_id

        if create_project:
            name = create_project if isinstance(
                create_project, basestring
            ) else None
            self.project, self.project_building = self.create_project(name=name)

        # append building id to self.url
        if self.building_id:
            self.url += "/{}".format(self.building_id)
        self.load_page()


class BuildingsList(Page):
    """
    Page object for the buildings list page.

    An import record and building will be created if url is True.

    :param: url: if True load by url, if False assume page is loaded
    :param import_file: define additional attributes of the import file
    :param building: define additional attributes of the building snapshot
    :num_buildings: number of additional buildings to create (assumes use_url)

    :type: url: bool or string, if string append to self.url.
    :type: import_file: dict
    :type: building: dict
    :type: num_buildings: int

    """
    def __init__(self, test_obj, url=None, import_file=None, building=None,
                 num_buildings=0):
        locator = Locator('ID', 'btnBuildingActions')
        # will cause ensure_table_is_loaded method to be added
        self.table_locator = Locator('XPATH', '//table')

        page = "app/#/buildings" if url else None
        if isinstance(url, basestring):
            page = "{}/{}".format(page, url)

        super(BuildingsList, self).__init__(
            test_obj, locator, url=page
        )

        # page set up
        if url:
            imports, self.canonical_building = self.create_record(
                create_building=True,
                import_file=import_file,
                building=building
            )
            self.building_id = self.canonical_building.id
            self.import_file = imports.import_file
            self.import_record = imports.import_record
            if num_buildings > 0:
                self.generate_buildings(99, building_details=building)

        self.load_page()


class BuildingLabels(Page):
    """
    Page object for the building reports page.

    :param: use_url: load page directly by url

    :type: use_url: bool

    """
    def __init__(self, test_obj, use_url=None):
        url = "app/#/buildings/labels" if use_url else None
        locator = Locator('CLASS_NAME', 'newLabelInput')

        super(BuildingLabels, self).__init__(
            test_obj, locator, url=url
        )
        self.load_page()


class BuildingListSettings(Page):
    """
    Page object for the building list settings page.

    :param: use_url: load page directly by url

    :type: use_url: bool

    """
    def __init__(self, test_obj, use_url=None):
        url = "app/#/settings" if use_url else None
        locator = Locator('ID', 'building-settings')

        super(BuildingListSettings, self).__init__(
            test_obj, locator, url=url
        )
        self.load_page()

    def ensure_table_is_loaded(self):
        """
        Page uses stacked table to get fixed header, so needs own method.
        """
        table_header = self.wait_for_element_by_class_name(
            'table_highlight_first'
        )
        header_row = table_header.find_element_by_tag_name('tr')
        headerlist = header_row.find_elements_by_tag_name('th')
        headers = [
            header.text if header.text else "Col_{}".format(idx)
            for idx, header in enumerate(headerlist)
        ]
        table_body = self.find_element_by_class_name('table_scroll')
        rows = table_body.find_elements_by_tag_name('tr')
        rows = [row.find_elements_by_tag_name('td') for row in rows]
        return Table(headers, rows)


class BuildingProjects(Page):
    """
    Page object for the building reports page.

    :param: id: building_id, page will load directly(by url) if supplied.

    :type: id: int

    """
    def __init__(self, test_obj, id=None):
        url = "app/#/buildings/{id}/projects".format(id) if id else None
        locator = Locator('CLASS_NAME', 'section_action_container')
        # will cause ensure_table_is_loaded method to be added
        self.table_locator = Locator('CLASS_NAME', 'table')

        super(BuildingProjects, self).__init__(
            test_obj, locator, url=url,
            use_text='Projects That Include This Building'
        )
        self.load_page()


class BuildingReports(Page):
    """
    Page object for the building reports page.

    :param: use_url: load page directly by url

    :type: use_url: bool

    """
    def __init__(self, test_obj, use_url=None):
        url = "app/#/buildings/reports" if use_url else None
        locator = Locator('CLASS_NAME', 'chart-holder')

        super(BuildingReports, self).__init__(
            test_obj, locator, url=url
        )
        self.load_page()


class DataMapping(Page):
    """
    Page object for the data mapping page

    dataset_id and create_import are mutually exclusive. dataset_id
    will take priority. The page will load directly (by url) if dataset_id or
    create_import are set. If import_record, import_record or building are
    supplied create_import will be set to True.

    :param: dataset_id: id of dataset (used in url)
    :param  create_import: create an import record before loading
    :param import_record: define additional attributes of the import record
    :param import_file: define additional attributes of the import file
    :param building: Add building if true, use dict for additional attributes

    :type: dataset_id: int
    :type: use_url: bool
    :type: create_import: bool
    :type: import_file: dict
    :type: import_record: dict
    :type: building: bool or dict

    """
    def __init__(self, test_obj, dataset_id=None, create_import=None,
                 import_record=None, import_file=None, building=None):
        locator = Locator('CLASS_NAME', 'mapping')
        # will cause ensure_table_is_loaded method to be added
        self.table_locator = Locator('CLASS_NAME', 'table')
        if import_record or import_file or building:
            create_import = True
        url = "app/#/data" if dataset_id or create_import else None

        super(DataMapping, self).__init__(
            test_obj, locator, url=url
        )

        # page set up
        if create_import and not dataset_id:
            create_building = True if building else False
            building = building if isinstance(building, dict) else None
            imports, canonical_building = self.create_record(
                create_building=create_building,
                import_record=import_record,
                import_file=import_file,
                building=building
            )
            if canonical_building:
                self.canonical_building = canonical_building
                self.building_id = self.canonical_building.id
            self.import_file = imports.import_file
            self.import_record = imports.import_record
            dataset_id = self.import_record.id
        if dataset_id:
            self.dataset_id = dataset_id
            self.url += "/{}".format(dataset_id)

        self.load_page()


class DataSetsList(Page):
    """
    Page object for the data sets list page.

    The page will load directly (by url) if create_import is set.

    :param  create_import: create an import record before loading
    :param import_file: define additional attributes of the import file
    :param building: Add building if true, use dict for additional attributes

    :type: use_url: bool
    :type: create_import: bool
    :type: import_file: dict
    :type: building: bool or dict

    """
    def __init__(self, test_obj,
                 create_import=None, import_file=None, building=None):
        locator = Locator('CLASS_NAME', 'dataset_list')
        # will cause ensure_table_is_loaded method to be added
        self.table_locator = Locator('XPATH', '//table')

        url = "app/#/data" if create_import else None
        super(DataSetsList, self).__init__(
            test_obj, locator, url=url
        )

        # page set up
        if create_import:
            create_building = True if building else False
            building = building if isinstance(building, dict) else None
            imports, canonical_building = self.create_record(
                create_building=create_building,
                import_file=import_file,
                building=building
            )
            if canonical_building:
                self.canonical_building = canonical_building
                self.building_id = self.canonical_building.id
            self.import_file = imports.import_file
            self.import_record = imports.import_record
        self.load_page()


class DataSetInfo(Page):
    """
    Page object for the data set info page

    dataset_id and create_import are mutually exclusive. dataset_id
    will take priority. The page will load directly (by url) if dataset_id or
    create_import are set. If import_record, import_record or building are
    supplied create_import will be set to True.

    :param: dataset_id: id of dataset (used in url)
    :param  create_import: create an import record before loading
    :param import_record: define additional attributes of the import record
    :param import_file: define additional attributes of the import file
    :param building: Add building if true, use dict for additional attributes

    :type: dataset_id: int
    :type: use_url: bool
    :type: create_import: bool
    :type: import_file: dict
    :type: import_record: dict
    :type: building: bool or dict

    """
    def __init__(self, test_obj, dataset_id=None, create_import=None,
                 import_record=None, import_file=None, building=None):
        locator = Locator('CLASS_NAME', 'import_results')
        # will cause ensure_table_is_loaded method to be added
        self.table_locator = locator
        if import_record or import_file or building:
            create_import = True
        url = "app/#/data" if dataset_id or create_import else None

        super(DataSetInfo, self).__init__(
            test_obj, locator, url=url
        )

        # page set up
        if create_import and not dataset_id:
            create_building = True if building else False
            building = building if isinstance(building, dict) else None
            imports, canonical_building = self.create_record(
                create_building=create_building,
                import_record=import_record,
                import_file=import_file,
                building=building
            )
            if canonical_building:
                self.canonical_building = canonical_building
                self.building_id = self.canonical_building.id
            self.import_file = imports.import_file
            self.import_record = imports.import_record
            dataset_id = self.import_record.id
        if dataset_id:
            self.dataset_id = dataset_id
            self.url += "/{}".format(dataset_id)

        self.load_page()


class LandingPage(Page):
    """
    Page object for the  Landing (Front/Home) Page.

    :param: use_url: if True load by url, if False assume page is loaded

    :type: use_url: bool

    """
    def __init__(self, test_obj, use_url=None):
        if use_url:
            use_url = '/'
        locator = Locator('CLASS_NAME', 'section_forms')
        super(LandingPage, self).__init__(
            test_obj, locator, url=use_url
        )
        self.load_page()


class MainPage(Page):
    """
    Page object for the Main Page. /app/#/

    :param: use_url: if True load by url, if False assume page is loaded

    :type: use_url: bool

    """
    def __init__(self, test_obj, use_url=None):
        if use_url:
            use_url = 'app/#/'
        locator = Locator('CLASS_NAME', 'page')
        super(MainPage, self).__init__(
            test_obj, locator, url=use_url
        )
        self.load_page()


class ProfilePage(Page):
    """
    Page object for the Profile Page. /app/#/profile

    :param: use_url: if True load by url, if False assume page is loaded
    :param: section: Which tab will be loaded. Default = profile

    :type: use_url: bool.
    :type: section: string one of profile/security/developer, case insensitive.

    """
    def __init__(self, test_obj, use_url=None, section=None):
        # set use text
        section = section if section else 'profile'
        self._set_section(section)
        url = "app/#/profile" if use_url else None
        if use_url and section.lower() != 'profile':
            url = "{}/{}".format(url, section.lower())
        locator = Locator('CLASS_NAME', 'section_header')
        super(ProfilePage, self).__init__(
            test_obj, locator, url=url
        )
        self.load_page()

    def _set_section(self, section):
        """Sets self.use_text and self.section from section."""
        if not (isinstance(section, basestring) and
                section.lower() in ['profile', 'security', 'developer']):
            raise ValueError(
                "Section must be one of profile/security/developer."
            )
        use_text = {
            'profile': 'Profile Information',
            'security': 'Change Password',
            'developer': 'API Key',
        }
        self.section = section.lower()
        self.use_text = use_text[self.section]

    def get_api_key_table(self):
        """
        Return API Key table.
        """
        assert self.section == 'developer'
        container_div = self.wait_for_element_by_class_name(
            'table_list_container'
        )
        table_element = container_div.find_element_by_tag_name('table')
        return table_factory(table_element)

    def reload(self, section=None):
        """Set section(use_text) before reloading.
        :param: section: Which tab will be loaded. Default = previous.

        :type: section: None/string one of profile/security/developer.
        """
        if section:
            self._set_section(section)
        super(ProfilePage, self).reload()


class ProjectsList(Page):
    """
    Page object for the Projects Page. /app/#/projects

    :param: use_url: if True load by url, if False assume page is loaded
    :param: building_id: Canonical building id to add to project.
    :param: create_building: Create a building when instantiating.
    :param: create_project: Create a project. Supply string to set name
    :param import_file: define additional attributes of the import file.

    :type: use_url: bool
    :type: building_id: int
    :type: create_building: bool, None or dict
    :type: create_project: bool, None
    :type: import_file: dict

    """
    def __init__(self, test_obj, use_url=None, building_id=None,
                 create_building=None, create_project=None, import_file=None):
        if use_url:
            use_url = 'app/#/projects'
        locator = Locator('ID', 'project-table')
        # will cause ensure_table_is_loaded method to be added
        self.table_locator = Locator('CLASS_NAME', 'table')
        super(ProjectsList, self).__init__(
            test_obj, locator, url=use_url
        )
        # create building record
        if create_building and not building_id:
            imports, self.canonical_building = self.create_record(
                create_building=True,
                import_file=import_file,
                building=create_building
            )
            building_id = self.canonical_building.id
            self.import_file = imports.import_file
            self.import_record = imports.import_record
        elif building_id:
            self.canonical_building = self.get_canonical_building(
                id=building_id)
        self.building_id = building_id

        if create_project:
            name = create_project if isinstance(
                create_project, basestring
            ) else None
            self.project, self.project_building = self.create_project(name=name)
        self.load_page()


class ProjectPage(Page):
    """
    Page object for the Projects Page. /app/#/projects

    Pass a dictionary to create_building to define additional attributes of
    building record/snapshot.

    building_id and create_building are mutually exclusive. building_id
    will take priority. If create project is true and there is a building
    (i.e. create_building or building id is True), it will be added to the
    project.

    :param: name: Project name. If set will load by url appending name to url
    :param: building_id: Canonical building id to add to project.
    :param: create_building: Create a building when instantiating.
    :param: create_project: Create a project.
    :param import_file: define additional attributes of the import file.

    :type: name: str
    :type: building_id: int
    :type: create_building: bool, None or dict
    :type: create_project: bool, None
    :type: import_file: dict

    """
    def __init__(self, test_obj, name=None, building_id=None,
                 create_building=None, create_project=None, import_file=None):
        if name and isinstance(name, basestring):
            url = 'app/#/projects/{}'.format(name)
        else:
            url = None
        locator = Locator('ID', 'building-list-table')
        # will cause ensure_table_is_loaded method to be added
        self.table_locator = Locator('ID', 'verify-mapping-table')
        super(ProjectPage, self).__init__(
            test_obj, locator, url=url
        )
        # create building record
        if create_building and not building_id:
            imports, self.canonical_building = self.create_record(
                create_building=True,
                import_file=import_file,
                building=create_building
            )
            building_id = self.canonical_building.id
            self.import_file = imports.import_file
            self.import_record = imports.import_record
        elif building_id:
            self.canonical_building = self.get_canonical_building(
                id=building_id)
        self.building_id = building_id

        if create_project:
            self.project, self.project_building = self.create_project(name=name)
        self.load_page()


class ProjectBuildingInfo(Page):
    """
    Page object for the Project building information page.

    This is largely the same as the BuildingInfo page

    The page will load directly(by url) if create_project or use_url is True.

    If use_url is set you *must* supply name and building id.
    If use_url is not set you *must* supply name.

    Pass a dictionary to create_building to define additional attributes of
    building record/snapshot.

    building_id and create_building are mutually exclusive. building_id
    will take priority.
    If create project is true a building will be added to the project.
    Therefore either create_building must be True or building_id must be set.

    :param: use_url: if True load by url, if False assume page is loaded
    :param: name: Project name.
    :param: building_id: Canonical building id
    :param: create_building: Create a building when instantiating.
    :param: create_project: Create a project.
    :param import_file: define additional attributes of the import file.

    :type: use_url: bool
    :type: name: str
    :type: building_id: int
    :type: create_building: bool, None or dict
    :type: create_project: bool,  None
    :type: import_file: dict

    """
    def __init__(self, test_obj, use_url=False, name=None, building_id=None,
                 create_building=None, create_project=None, import_file=None):
        if use_url and not (name and building_id):
            error = "name and building_id must be supplied if use_url is true"
            raise AttributeError(error)
        if not use_url and not create_project and not name:
            error = "name must be set if use_url and create_project are False"
            raise AttributeError(error)
        if use_url or create_project:
            url = "app/#/projects"
        else:
            url = None
        locator = Locator('PARTIAL_LINK_TEXT', 'Project:')
        # will cause ensure_table_is_loaded method to be added
        self.table_locator = Locator('CLASS_NAME', 'table')

        super(ProjectBuildingInfo, self).__init__(
            test_obj, locator, url=url
        )
        # create building record
        if create_building and not building_id:
            imports, self.canonical_building = self.create_record(
                create_building=True,
                import_file=import_file,
                building=create_building
            )
            building_id = self.canonical_building.id
            self.import_file = imports.import_file
            self.import_record = imports.import_record
        elif building_id:
            self.canonical_building = self.get_canonical_building(
                id=building_id)
        self.building_id = building_id

        if create_project:
            name = name if isinstance(
                name, basestring
            ) else None
            self.project, self.project_building = self.create_project(name=name)
            self.project_name = self.project.name
        else:
            self.project_name = name

        # use_text must be set to uniquely id this page
        self.use_text = "Project: {}".format(self.project_name)

        # if building id and name to self.url
        if self.building_id and self.project_name and use_url or create_project:
            self.url += "/{}/{}".format(self.project_name, self.building_id)

        self.load_page()

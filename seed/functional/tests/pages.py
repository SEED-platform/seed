
# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA

This module defines Page objects representing view in SEED.


:Example:

Defining a page object
----------------------

class Home(Page):
    def __init__(self, test_obj):
        url = "/index.html"
        self.locator = Locator('NAME', 'my-button')
        super(Home, self).__init__(test_obj, locator, url=url)
        self.load_page()


..warning:
    a locator must be defined and passed to super(Class, self)__init__

Calling the page object in a test
---------------------------------
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

:author Paul Munday<paul@paulmunday.net>
"""
from seed.functional.tests.page import Locator, Page, Table


class BuildingInfo(Page):
    """
    Page object for the building details page.

    The page will load directly(by url) if create_record or a building_id is set.

    Pass a dictionary to create_building to define additional attributes of
    building record/snapshot.

    building_id and create_building are mutually exclusive. building_id
    will take priority. If create project is true and there is a building
    (i.e. create_building or building id is True), it will be added to the project.

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
            self.canonical_building = self.get_canonical_building(id=building_id)
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

    :type: url: Bool or string, if string append to self.url.
    :type: import_file: dict
    :type: building: dict
    """
    def __init__(self, test_obj, url=None, import_file=None, building=None):
        locator = Locator('ID', 'building-list')
        # will cause ensure_table_is_loaded method to be added
        self.table_locator = Locator('XPATH', '//table')

        page = "app/#/buildings" if url else None
        if isinstance(url, str):
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
        table_header = self.wait_for_element_by_class_name('table_highlight_first')
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
            test_obj, locator, url=url, use_text='Projects That Include This Building'
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
    def __init__(self, test_obj, create_import=None, import_file=None, building=None):
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

    :param: url: if True load by url, if False assume page is loaded
    :type: url: bool
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

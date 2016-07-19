# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA

..warning::
    SEE README BEFORE EDITING THIS FILE!

:author nlong, Paul Munday<paul@paulmunday.net>
"""
from datetime import date
import inspect
import os


from seed.functional.tests.browser_definitions import BROWSERS
from seed.functional.tests.base import eprint
from seed.functional.tests.base import LOGGED_IN_CLASSES
from seed.functional.tests.base import LOGGED_OUT_CLASSES
from seed.functional.tests.base import mock_file_factory
from seed.functional.tests.pages import BuildingInfo, BuildingLabels
from seed.functional.tests.pages import BuildingsList, BuildingListSettings
from seed.functional.tests.pages import BuildingProjects, BuildingReports
from seed.functional.tests.pages import DataMapping, DataSetInfo, DataSetsList
from seed.functional.tests.pages import LandingPage, MainPage

from seed.data_importer.models import ROW_DELIMITER
# from seed.models import Project, ProjectBuilding, StatusLabel


def loggedout_tests_generator():
    """
    Generator containing the LoggedOut Test Class definition.

    Any tests added to the definition will be expanded at run time to
    cover all browsers and yielded individually to the test runner.
    """
    for browser in BROWSERS:

        # TestClass definition for tests run when the user is not
        # logged in. Add your test methods here
        class LoggedOutTests(LOGGED_OUT_CLASSES[browser.name]):

            def test_login(self):
                page = LandingPage(self, use_url=True)
                username_input = page.find_element_by_id("id_email")
                username_input.send_keys('test@example.com')
                password_input = page.find_element_by_id("id_password")
                password_input.send_keys('password')
                page.find_element_by_css_selector('input[value="Log In"]').click()
                # should now be on main page
                main_page = MainPage(self)
                title_container = main_page.wait_for_element(
                    'CLASS_NAME', 'home_hero_content_container'
                )
                title = title_container.find_element_by_tag_name('h1')
                assert title.text == 'Getting Started'

        # ================= TESTS GO ABOVE THIS LINE ======================

        # Leave this at the end
        Test = LoggedOutTests()
        tests = get_tsts(Test)
        for test in tests:
            yield test


def loggedin_tests_generator():
    """
    Generator containing the Logged In Test Class definition.

    Any tests added to the definition will be expanded at run time to
    cover all browsers and yielded individually to the test runner.
    """
    for browser in BROWSERS:

        # TestClass definition for tests run when the user is
        # logged in. Add your test methods here
        class LoggedInTests(LOGGED_IN_CLASSES[browser.name]):

            def test_dataset_list(self):
                """Make sure dataset list works."""
                # load imports
                self.create_import(name="Test Dataset")
                page = MainPage(self, use_url=True)
                page.find_element_by_id('sidebar-data').click()
                datasets = DataSetsList(self)

                # Make sure there's a row in the table
                datasets.find_element_by_css_selector('td.name')
                table = datasets.ensure_table_is_loaded()
                data_set_name = table.first_row['DATA SET NAME']
                data_set_files = table.first_row['# OF FILES']
                assert data_set_name.text == "Test Dataset"
                assert data_set_files.text == "1"

            def test_dataset_detail(self):
                """
                Make sure you can click dataset name on dataset list page
                and load dataset.
                """
                mock_file = mock_file_factory("test.csv")
                datasets = DataSetsList(
                    self, create_import=True,
                    import_file={'mock_file': mock_file}
                )
                # Click a dataset.
                datasets.find_element_by_css_selector(
                    'td a.import_name').click()

                # ensure page is loaded
                dataset = DataSetInfo(self)

                # Make sure import file is there.
                table = dataset.ensure_table_is_loaded()
                row = table.first_row
                data_file_cell = row['DATA FILES']
                assert data_file_cell.text == mock_file.base_name

            def test_mapping_page(self):
                """
                Make sure you can click mapping button on dataset page and
                mapping loads.
                """
                # Create records and navigate to dataset detail view.
                mock_file = mock_file_factory("test.csv")
                import_record = {'name': 'Test Dataset'}
                import_file = {
                    'cached_first_row': ROW_DELIMITER.join(
                        [u'name', u'address']
                    ),
                    'cached_second_to_fifth_row': ROW_DELIMITER.join(
                        ['name', 'address.']
                    ),
                    'mock_file': mock_file
                }
                dataset = DataSetInfo(
                    self, import_record=import_record, import_file=import_file
                )

                # Click mapping button.
                dataset.find_element_by_id('data-mapping-0').click()

                # Make sure mapping table is shown.
                data_mapping = DataMapping(self)
                table = data_mapping.ensure_table_is_loaded()
                row = table.find_row_by_field('DATA FILE HEADER', 'address')
                address = row['ROW 1']
                assert address.text == 'address.'

            def test_building_list(self):
                """
                Make sure you can click from the menu to the building list
                page and it loads.
                """
                # load main page and create building snapshot
                main_page = MainPage(self, use_url=True)
                main_page.create_record(create_building=True)

                # click on building in sidebar
                main_page.find_element_by_id('sidebar-buildings').click()
                self.wait_for_element_by_css('#building-list')

                # Make sure a building is present.
                self.browser.find_element_by_css_selector(
                    '#building-list-table td')
                buildings_list = BuildingsList(self)
                table = buildings_list.ensure_table_is_loaded()
                address = table.first_row['ADDRESS LINE 1']
                assert address.text == 'address'

            def test_building_list_tab_settings(self):
                """Make sure building list settings tab loads."""
                # load buildings list and create records
                buildings_list = BuildingsList(self, url=True)
                # locate setting link and click on it
                settings_link = buildings_list.find_element_by_id(
                    'list-settings'
                )
                settings_link.click()

                # ensure settings page has loaded correctly.
                settings_page = BuildingListSettings(self)
                table = settings_page.ensure_table_is_loaded()
                assert table.first_row['COLUMN NAME'].text == 'Address Line 1'

            def test_building_list_tab_reports(self):
                """Make sure building list reports tab loads."""
                # load buildings list and create records
                buildings_list = BuildingsList(self, url=True)
                reports_link = buildings_list.find_element_by_id('reports')
                reports_link.click()

                reports_page = BuildingReports(self)
                form = reports_page.wait_for_element_by_class_name('chart-inputs')
                form_groups = form.find_elements_by_class_name('form-group')
                button = form_groups[-1].find_element_by_tag_name('button')
                assert button.text == 'Update Charts'

            def test_building_list_tab_labels(self):
                """Make sure building list labels tab loads."""
                buildings_list = BuildingsList(self, url=True)
                labels_link = buildings_list.find_element_by_id('labels')
                labels_link.click()

                labels_page = BuildingLabels(self)
                button = labels_page.find_element_by_id('btnCreateLabel')
                assert button.text == 'Create label'

            def test_building_detail(self):
                """Make sure building detail page loads."""
                # load Buildings List
                buildings_list = BuildingsList(self, url=True)
                # Click a building.
                buildings_link = buildings_list.wait_for_element(
                    'CSS_SELECTOR', 'td a')
                buildings_link.click()

                # Wait for details page
                details_page = BuildingInfo(self)
                table = details_page.ensure_table_is_loaded()
                assert table.first_row['FIELD'].text == 'Address Line 1'

            def test_building_detail_tab_projects(self):
                """Make sure building detail projects tab shows project."""
                details_page = BuildingInfo(
                    self,
                    create_building=True,
                    create_project=True
                )
                projects_link = details_page.find_element_by_id('projects')
                projects_link.click()
                project_list = BuildingProjects(self)
                table = project_list.ensure_table_is_loaded()
                project = table.last_row['PROJECT']
                assert project.text == 'test'

            def test_building_detail_edit_year_end_save(self):
                """Make sure changes to Year Ending date propagate."""
                # make sure Year Ending column will show
                self.set_buildings_list_columns('year_ending')

                # load Buildings List
                buildings_list = BuildingsList(self, url=True)
                # Click a building.
                buildings_link = buildings_list.wait_for_element(
                    'CSS_SELECTOR', 'td a')
                buildings_link.click()

                # Wait for details page and click the edit button
                details_page = BuildingInfo(self)
                details_page.find_element_by_partial_link_text('Edit').click()

                # Wait for form to load
                details_page.wait_for_element('LINK_TEXT', 'Save Changes')

                # Find Year Ending and set new value
                details_table = details_page.ensure_table_is_loaded()
                new_year_ending = date(2015, 12, 31)
                row = details_table.find_row_by_field('FIELD', 'Year Ending')
                year_ending = row['MASTER'].find_element_by_id('edit_tax_lot_id')
                year_ending.clear()
                year_ending.send_keys(str(new_year_ending))
                details_page.find_element_by_link_text('Save Changes').click()

                # Return to Buildings List
                details_page.wait_for_element('PARTIAL_LINK_TEXT', 'Buildings')
                details_page.find_element_by_partial_link_text(
                    'Buildings').click()
                buildings_list.reload()

                # Assert new year ending values correctly set
                table = buildings_list.ensure_table_is_loaded()
                year_ending = table.last_row['YEAR ENDING']
                assert year_ending.text == new_year_ending.strftime('%D')

            def test_building_detail_th_resize(self):
                """Make sure building detail table headers are resizable."""
                # This test was created for an issue that primarily
                # affected Firefox & IE, however the current Firefox
                # webdriver is limited in its capacities (in beta) so can't
                # use action chains.
                # See WARNING! HACK ALERT in base.py.
                # At somepoint (Firefox version  >= 48.0?) the new webriver
                # will land in the main branch and hopefully will be able to
                # run the test, so this guard condition can be removed.
                # Note the tests tests all functionality so its still
                # useful to run it against Chrome.
                # Its currently failing with Travis and Firefox as well
                # (where it was passing, presumable because Sauce Labs
                # browser version has updated.
                # if (os.getenv('TRAVIS') == 'true') or (
                if ((os.getenv('TRAVIS') == 'true') and
                        (self.browser_type.name != 'Firefox')) or (
                        self.browser_type.name == 'Chrome'):
                    # load Building Details
                    building_details = BuildingInfo(self, create_building=True)

                    # test to make sure we can resize table header
                    fields = building_details.find_element_by_id(
                        'building-fields')
                    assert fields is not None
                    size = fields.size['width']
                    xoffset = fields.size['width']
                    yoffset = 0

                    # move to right hand edge and click and drag
                    building_details.action.move_to_element_with_offset(
                        fields, xoffset, yoffset)
                    building_details.action.click_and_hold()
                    building_details.action.move_to_element_with_offset(
                        fields, fields.location['x'] + 180, yoffset
                    )
                    building_details.action.release()
                    building_details.perform_stored_actions()

                    # assert it has been resized
                    assert size > fields.size['width']
                    # crude test to test against #982
                    assert fields.size['width'] > 80
        # ================= TESTS GO ABOVE THIS LINE ======================

        # Leave this at the end
        Test = LoggedInTests()
        for test in get_tsts(Test):
            yield test


# you can't use test in a name or Nose will try and run it.
def get_tsts(Test):
    """
    Return a list of test_methods wrapped up in test functions.

    These functions can be safely yielded by a test_generator.

    :param Test: an instance of a Test Class

    :returns a list of test functions
    """
    # Nose will use a generator to create tests on the fly. However
    # unittest expects the generator to yield a function, not a class.
    # To make this work with TestClasses we can instiate the Class
    # ourselves and return a reference to the the individual methods.

    # Becuase the TestClass is called directly, not by the test runner,
    # setUp etc won't run automatically.

    # This function, therefore, invokes the setUpClass method directly.
    # Then it iterates over the methods in the class. When in finds one
    # that starts with test_ it wraps it in a function that invokes the
    # setUp and tearDown method alongside the test, and adds it to the
    # return values.
    if hasattr(Test, 'setUpClass'):
        Test.setUpClass()
    tests = []

    def test_func_factory(TestClass, test, tname):
        def test_func():
            try:
                # include setUp in try, to ensure tearDown happens
                # if it fails. This was causing issues with tests when
                # login() failed. This should be ok as super gets
                # called first then login
                if hasattr(TestClass, 'setUp'):
                    TestClass.setUp()
                test()
            except:
                msg = "test: {} failed with browser {}".format(
                    tname, TestClass.browser_type.name
                )
                eprint(msg)
                raise
            finally:
                if hasattr(TestClass, 'tearDown'):
                    TestClass.tearDown()
        test_func.__name__ = tname
        return test_func

    for method in inspect.getmembers(Test, inspect.ismethod):
        if method[0].startswith('test_'):
            test = method[1]
            tname = method[0]

            tests.append(test_func_factory(Test, test, tname))
    return tests

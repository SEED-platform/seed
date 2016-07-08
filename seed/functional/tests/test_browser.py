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

from seed.data_importer.models import ROW_DELIMITER
from seed.models import Project, ProjectBuilding, StatusLabel


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
                self.browser.get(self.live_server_url)
                username_input = self.browser.find_element_by_id("id_email")
                username_input.send_keys('test@example.com')
                password_input = self.browser.find_element_by_id("id_password")
                password_input.send_keys('password')
                self.browser.find_element_by_css_selector('input[value="Log In"]').click()
                self.wait_for_element_by_css('.menu')

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

            def test_building_detail_edit_year_end_save(self):
                """Make sure changes to Year Ending date propagate."""
                # make sure Year Ending column will show
                self.set_buildings_list_columns('year_ending')

                import_file, _ = self.create_import()
                self.create_building(import_file, year_ending='2014-12-31')
                url = "{}/app/#/buildings".format(self.live_server_url)
                self.browser.get(url)
                self.wait_for_element_by_css('#building-list')

                # Click a building.
                self.browser.find_element_by_css_selector('td a').click()

                # Wait for details page and click the edit button
                self.wait_for_element('PARTIAL_LINK_TEXT', 'Edit')
                self.browser.find_element_by_partial_link_text('Edit').click()

                # Wait for form to load
                self.wait_for_element('LINK_TEXT', 'Save Changes')

                # Find Year Ending and set new value
                new_year_ending = date(2015, 12, 31)
                year_ending = self.browser.find_element_by_xpath(
                    "//table/tbody/tr[last()]/td[2]/div[1]/input[@id='edit_tax_lot_id']"
                )
                year_ending.clear()
                year_ending.send_keys(str(new_year_ending))
                self.browser.find_element_by_link_text('Save Changes').click()

                # Return to Buildings List
                self.wait_for_element('PARTIAL_LINK_TEXT', 'Buildings')
                self.browser.find_element_by_partial_link_text(
                    'Buildings').click()

                # Find Year Ending field
                self.wait_for_element_by_css('#building-list')
                year_ending = self.browser.find_element_by_xpath(
                    "//table/tbody/tr[1]/td[2]/span"
                )

                # Assert new year ending values correctly set
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
                if (os.getenv('TRAVIS') == 'true') or (
                        self.browser_type.name == 'Chrome'):
                    import_file, _ = self.create_import()
                    canonical_building = self.create_building(import_file)
                    live_server_url = "{}/app/#/buildings/{}".format(
                        self.live_server_url,
                        canonical_building.pk
                    )
                    self.browser.get(live_server_url)

                    # test to make sure we can resize table header
                    fields = self.browser.find_element_by_id(
                        'building-fields')
                    assert fields is not None
                    size = fields.size['width']
                    xoffset = fields.size['width']
                    yoffset = 0
                    actions = self.get_action_chains()
                    # move to right hand edge and click and drag
                    actions.move_to_element_with_offset(
                        fields, xoffset, yoffset)
                    actions.click_and_hold()
                    actions.move_to_element_with_offset(
                        fields, fields.location['x'] + 180, yoffset
                    )
                    actions.release()
                    actions.perform()
                    # assert it has been resized
                    assert size > fields.size['width']
                    # crude test to test against #982
                    assert fields.size['width'] > 80

            def test_dataset_list(self):
                """Make sure dataset list works."""
                self.create_import()
                self.browser.get(self.live_server_url)
                self.wait_for_element_by_css('.menu')
                self.browser.find_element_by_id('sidebar-data').click()
                self.wait_for_element_by_css('.dataset_list')

                # Make sure there's a row in the table
                self.browser.find_element_by_css_selector('td.name')

            def test_dataset_detail(self):
                """
                Make sure you can click dataset name on dataset list page
                and load dataset.
                """
                self.create_import()

                # Navigate to dataset list view.
                self.browser.get(self.live_server_url + '/app/#/data')
                self.wait_for_element_by_css('.dataset_list')

                # Click a dataset.
                self.browser.find_element_by_css_selector(
                    'td a.import_name').click()

                # Make sure import file is there.
                self.wait_for_element_by_css('td.data_file_name')

            def test_mapping_page(self):
                """
                Make sure you can click mapping button on dataset page and
                mapping loads.
                """
                import_file, import_record = self.create_import(
                    cached_first_row=ROW_DELIMITER.join(
                        [u'name', u'address']
                    ),
                    cached_second_to_fifth_row=ROW_DELIMITER.join(
                        ['name', 'address.']
                    )
                )

                # Navigate to dataset detail view.
                url = "{}/app/#/data/{}".format(
                    self.live_server_url, import_record.pk)
                self.browser.get(url)

                # Wait for load.
                self.wait_for_element_by_css('td.data_file_name')

                # Click mapping button.
                self.browser.find_element_by_id('data-mapping-0').click()

                # Make sure mapping table is shown.
                self.wait_for_element_by_css('div.mapping')

            def test_building_list(self):
                """
                Make sure you can click from the menu to the building list
                page and it loads.
                """
                import_file, _ = self.create_import()
                self.create_building(import_file)
                self.browser.get(self.live_server_url)

                self.wait_for_element_by_css('.menu')
                self.browser.find_element_by_id('sidebar-buildings').click()
                self.wait_for_element_by_css('#building-list')

                # Make sure a building is present.
                self.browser.find_element_by_css_selector(
                    '#building-list-table td')

            def test_building_list_tab_settings(self):
                """Make sure building list settings tab loads."""
                import_file, _ = self.create_import()
                self.create_building(import_file)
                url = "{}/app/#/buildings/settings".format(
                    self.live_server_url)
                self.browser.get(url)

                self.wait_for_element_by_css('#building-settings')

            def test_building_list_tab_reports(self):
                """Make sure building list reports tab loads."""
                import_file, _ = self.create_import()
                self.create_building(import_file)
                url = "{}/app/#/buildings/reports".format(
                    self.live_server_url)
                self.browser.get(url)

                self.wait_for_element_by_css('.building-reports')

            def test_building_list_tab_labels(self):
                """Make sure building list labels tab loads."""
                import_file, _ = self.create_import()
                self.create_building(import_file)
                StatusLabel.objects.create(
                    name='test',
                    super_organization=self.org
                )
                url = "{}/app/#/buildings/labels".format(self.live_server_url)
                self.browser.get(url)

                # Make sure a label is in the list.
                self.wait_for_element_by_css('tbody tr td span.label')

            def test_building_detail(self):
                """Make sure building detail page loads."""
                import_file, _ = self.create_import()
                self.create_building(import_file)
                url = "{}/app/#/buildings".format(self.live_server_url)
                self.browser.get(url)
                self.wait_for_element_by_css('#building-list')

                # Click a building.
                self.browser.find_element_by_css_selector('td a').click()

                # We know detail page is loaded when projects tab is there.
                self.wait_for_element_by_css('#projects')

            def test_building_detail_tab_projects(self):
                """Make sure building detail projects tab shows project."""
                import_file, _ = self.create_import()
                canonical_building = self.create_building(import_file)
                project = Project.objects.create(
                    name='test', owner=self.user,
                    super_organization=self.org
                )
                ProjectBuilding.objects.create(
                    project=project,
                    building_snapshot=canonical_building.canonical_snapshot
                )
                url = "{}/app/#/buildings/{}/projects".format(
                    self.live_server_url,
                    canonical_building.pk
                )
                self.browser.get(url)

                # Make sure project is in list.
                self.wait_for_element_by_css('tbody tr td a')

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

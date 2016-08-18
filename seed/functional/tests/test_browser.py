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

from selenium.webdriver.support.select import Select

from seed.functional.tests.browser_definitions import BROWSERS
from seed.functional.tests.base import eprint
from seed.functional.tests.base import LOGGED_IN_CLASSES
from seed.functional.tests.base import LOGGED_OUT_CLASSES
from seed.functional.tests.base import mock_file_factory
from seed.functional.tests.pages import AccountsPage
from seed.functional.tests.pages import BuildingInfo, BuildingLabels
from seed.functional.tests.pages import BuildingsList, BuildingListSettings
from seed.functional.tests.pages import BuildingProjects, BuildingReports
from seed.functional.tests.pages import DataMapping, DataSetInfo, DataSetsList
from seed.functional.tests.pages import LandingPage, MainPage
from seed.functional.tests.pages import ProfilePage, ProjectBuildingInfo
from seed.functional.tests.pages import ProjectsList, ProjectPage

from seed.data_importer.models import ROW_DELIMITER


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
                page.find_element_by_css_selector(
                    'input[value="Log In"]'
                ).click()
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

            def test_accounts_page(self):
                """Make sure accounts//organinizations works."""
                # load imports
                import_file, _ = self.create_import(name="Test Dataset")
                self.create_building(import_file=import_file)

                # create sub_org
                self.create_sub_org(name="Sub Org")
                other_user_details = {
                    'username': 'johnh@example.com',
                    'password': 'password',
                    'email': 'johnh@example.com',
                    'first_name': 'John',
                    'last_name': 'Henry'
                }
                # Add another org self.user is member of (not owner)
                other_user = self.create_user(**other_user_details)
                other_org, _ = self.create_org(
                    name='Other Org', user=other_user
                )
                self.create_org_user(
                    user=self.user, org=other_org, role='member'
                )

                page = MainPage(self, use_url=True)
                page.find_element_by_id('sidebar-accounts').click()

                accounts = AccountsPage(self)
                title = accounts.wait_for_element_by_class_name('page_title')
                assert title.text == 'Organizations'

                managed_orgs = accounts.get_managed_org_tables()
                # sanity check should have parent and child
                assert len(managed_orgs) == 2
                parents = []
                children = []
                for org in managed_orgs:
                    # is parent org
                    if org.sub_orgs:
                        parents.append(org)
                    else:
                        children.append(org)

                # assert 1 parent/1 child
                assert len(parents) == len(children) == 1

                parent = parents[0]
                child = children[0]
                sub_orgs = parent.sub_orgs

                # assert number of children equal, accounting for header
                assert len(sub_orgs[1:]) == len(children) == 1

                # check names
                assert parent.org['ORGANIZATION'].text == 'Org'
                assert child.org['ORGANIZATION'].text == 'Sub Org'

                # check for Sub-Organizations header
                assert sub_orgs[0]['ORGANIZATION'].text == 'Sub-Organizations'

                # check sub org and child are the same
                assert sub_orgs[1]['ORGANIZATION'].text == child.org[
                    'ORGANIZATION'].text

                # Test ' Organizations I Belong To' table
                member_orgs = accounts.get_member_orgs_table()

                # check num and name of orgs
                assert len(member_orgs) == 3
                org_names = [
                    org['ORGANIZATION NAME'].text for org in member_orgs
                ]
                assert 'Org' in org_names
                assert 'Sub Org' in org_names
                assert 'Other Org' in org_names

                # Check details
                org = member_orgs.find_row_by_field(
                    'ORGANIZATION NAME', 'Org'
                )
                sub_org = member_orgs.find_row_by_field(
                    'ORGANIZATION NAME', 'Sub Org'
                )
                other = member_orgs.find_row_by_field(
                    'ORGANIZATION NAME', 'Other Org'
                )
                assert org['NUMBER OF BUILDINGS'].text == '1'
                assert org['YOUR ROLE'].text == 'owner'
                assert org['ORGANIZATION OWNER(S)'].text == 'Jane Doe'

                assert sub_org['NUMBER OF BUILDINGS'].text == '0'
                assert sub_org['YOUR ROLE'].text == 'owner'
                assert sub_org['ORGANIZATION OWNER(S)'].text == 'Jane Doe'

                assert sub_org['NUMBER OF BUILDINGS'].text == '0'
                assert other['YOUR ROLE'].text == 'member'
                assert other['ORGANIZATION OWNER(S)'].text == 'John Henry'

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
                make sure you can click dataset name on dataset list page
                and load dataset.
                """
                mock_file = mock_file_factory("test.csv")
                datasets = DataSetsList(
                    self, create_import=True,
                    import_file={'mock_file': mock_file}
                )
                # click a dataset.
                datasets.find_element_by_css_selector(
                    'td a.import_name').click()

                # ensure page is loaded
                dataset = DataSetInfo(self)

                # make sure import file is there.
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

                # Make sure a building is present.
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
                form = reports_page.wait_for_element_by_class_name(
                    'chart-inputs'
                )
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

            def test_building_list_buildings_display(self):
                """
                Test to make sure user can set number of buildings to display.

                Ensure page loads and settings stick to project.
                See github issue #1005 pull request#1006
                """
                # This is used to check the number of pages to display
                # we also test what shows up on the page.
                # This is used to show skip the test is sessionStore
                # goes missing, as this happens, intermittently,
                # with  Firefox in this test
                script = "return window.sessionStorage.getItem('{}')".format(
                    '/buildings:seedBuildingNumberPerPage'
                )

                browser_name = self.browser_type.name
                buildings_list = BuildingsList(self, url=True)

                # set up project
                buildings_list.create_project(name='test')

                # select 100 in dropdown
                display_count = buildings_list.wait_for_element_by_id(
                    'number_per_page_select'
                )
                drop_down = Select(display_count)
                # firefox doesn't want to select anything
                # so send it 1 to select 100
                if self.browser_type.name == 'Firefox':
                    display_count.send_keys('1')
                else:
                    drop_down.select_by_visible_text('100')
                assert drop_down.first_selected_option.text == '100'

                # check value persists and page loads
                buildings_list.reload()
                display_count = buildings_list.wait_for_element_by_id(
                    'number_per_page_select'
                )
                drop_down = Select(display_count)
                assert drop_down.first_selected_option.text == '100'

                # click through to last record
                last_record = buildings_list.wait_for_element_by_class_name(
                    'pager'
                ).find_elements_by_tag_name('a')[-1]
                last_record.click()
                # check value persists and page loads
                buildings_list.reload()
                display_count = buildings_list.wait_for_element_by_id(
                    'number_per_page_select'
                )
                drop_down = Select(display_count)
                # skip test if browser "loses" session store
                result = self.browser.execute_script(script)
                if not result:
                    eprint('SessionStore missing from', browser_name)
                    eprint('This is not the bug you are looking for')
                    eprint('skipping assert...')
                else:
                    assert result == '100'
                    assert drop_down.first_selected_option.text == '100'

                # Navigate to projects page
                projects_link = buildings_list.find_element_by_id(
                    'sidebar-projects'
                )
                projects_link.click()
                projects_list = ProjectsList(self)

                # locate project link and navigate to project page
                table = projects_list.ensure_table_is_loaded()
                project = table.find_row_by_field('PROJECT NAME', 'test')
                project_cell = project['PROJECT NAME']
                project_link = project_cell.find_element_by_class_name(
                    'table_name_link'
                )
                project_link.click()

                # Navigate to project page
                project_page = ProjectPage(self)

                # select 50 in dropdown
                display_count = project_page.wait_for_element_by_id(
                    'number_per_page_select'
                )
                drop_down = Select(display_count)
                # firefox doesn't want to select anything
                # so send it 1 to select 100
                if self.browser_type.name == 'Firefox':
                    display_count.send_keys('5')
                else:
                    drop_down.select_by_visible_text('50')
                assert drop_down.first_selected_option.text == '50'
                # navigate back to building list
                buildings_link = project_page.find_element_by_id(
                    'sidebar-buildings'
                )
                buildings_link.click()

                # check value persists and page loads
                buildings_list.reload()
                display_count = buildings_list.wait_for_element_by_id(
                    'number_per_page_select'
                )
                drop_down = Select(display_count)
                # skip test if browser "loses" session store
                result = self.browser.execute_script(script)
                if not result:
                    eprint('SessionStore missing from ', browser_name)
                    eprint('This is not the bug you are looking for')
                    eprint('skipping assert...')
                else:
                    assert result == '100'
                    assert drop_down.first_selected_option.text == '100'

                # navigate to building details page
                buildings_link = buildings_list.wait_for_element(
                    'CSS_SELECTOR', 'td a')
                buildings_link.click()

                # Wait for details page
                details_page = BuildingInfo(self)

                # Return to Buildings List
                details_page.wait_for_element('PARTIAL_LINK_TEXT', 'Buildings')
                details_page.find_element_by_partial_link_text(
                    'Buildings').click()

                # check value persists and page loads
                buildings_list.reload()
                display_count = buildings_list.wait_for_element_by_id(
                    'number_per_page_select'
                )
                drop_down = Select(display_count)
                result = self.browser.execute_script(script)
                # skip test if browser "loses" session store
                if not result:
                    eprint('SessionStore missing from ', browser_name)
                    eprint('This is not the bug you are looking for')
                    eprint('skipping assert...')
                else:
                    assert result == '100'
                    assert drop_down.first_selected_option.text == '100'

            def test_building_list_buildings_retain_paging(self):
                """
                Test to make sure user ends up back in the same place
                when clicking away and back.

                See github issue #836
                """
                buildings_list = BuildingsList(
                    self, url=True, num_buildings=99
                )
                count = buildings_list.find_element_by_class_name('counts')
                assert count.text == 'Showing 1 to 10 of 100 buildings'

                # click through to next  record
                next_record = buildings_list.wait_for_element_by_class_name(
                    'pager'
                ).find_elements_by_tag_name('a')[-2]
                next_record.click()
                buildings_list.reload()

                # click through to next  record
                next_record = buildings_list.wait_for_element_by_class_name(
                    'pager'
                ).find_elements_by_tag_name('a')[-2]
                next_record.click()
                buildings_list.reload()

                # click through to next  record
                next_record = buildings_list.wait_for_element_by_class_name(
                    'pager'
                ).find_elements_by_tag_name('a')[-2]
                next_record.click()

                buildings_list.reload()
                count = buildings_list.wait_for_element_by_class_name(
                    'counts')
                table = buildings_list.ensure_table_is_loaded()
                address = table.first_row['ADDRESS LINE 1']
                address_text = address.text
                assert count.text == 'Showing 31 to 40 of 100 buildings'

                # Click a building.
                buildings_link = buildings_list.wait_for_element(
                    'CSS_SELECTOR', 'td a')
                buildings_link.click()

                # Wait for details page
                details_page = BuildingInfo(self)
                table = details_page.ensure_table_is_loaded()
                assert table.first_row['FIELD'].text == 'Address Line 1'

                # Return to Buildings List
                details_page.wait_for_element('PARTIAL_LINK_TEXT', 'Buildings')
                details_page.find_element_by_partial_link_text(
                    'Buildings').click()
                buildings_list.reload()
                count = buildings_list.wait_for_element_by_class_name(
                    'counts')

                table = buildings_list.ensure_table_is_loaded()
                address = table.first_row['ADDRESS LINE 1']
                assert count.text == 'Showing 31 to 40 of 100 buildings'
                assert address.text == address_text

                # click through to last record
                last_record = buildings_list.wait_for_element_by_class_name(
                    'pager'
                ).find_elements_by_tag_name('a')[-1]
                last_record.click()

                buildings_list.reload()
                count = buildings_list.wait_for_element_by_class_name(
                    'counts')
                table = buildings_list.ensure_table_is_loaded()
                address = table.first_row['ADDRESS LINE 1']
                address_text = address.text
                assert count.text == 'Showing 91 to 100 of 100 buildings'

                # Click a building.
                buildings_link = buildings_list.wait_for_element(
                    'CSS_SELECTOR', 'td a')
                buildings_link.click()

                # Wait for details page
                details_page = BuildingInfo(self)
                table = details_page.ensure_table_is_loaded()
                assert table.first_row['FIELD'].text == 'Address Line 1'

                # Return to Buildings List
                details_page.wait_for_element('PARTIAL_LINK_TEXT', 'Buildings')
                details_page.find_element_by_partial_link_text(
                    'Buildings').click()
                buildings_list.reload()
                count = buildings_list.wait_for_element_by_class_name(
                    'counts')

                table = buildings_list.ensure_table_is_loaded()
                address = table.first_row['ADDRESS LINE 1']
                assert count.text == 'Showing 91 to 100 of 100 buildings'
                assert address.text == address_text

                # click through to first record
                first_record = buildings_list.wait_for_element_by_class_name(
                    'pager'
                ).find_elements_by_tag_name('a')[0]
                first_record.click()

                buildings_list.reload()
                count = buildings_list.wait_for_element_by_class_name(
                    'counts')
                table = buildings_list.ensure_table_is_loaded()
                address = table.first_row['ADDRESS LINE 1']
                address_text = address.text
                assert count.text == 'Showing 1 to 10 of 100 buildings'

                # Click a building.
                buildings_link = buildings_list.wait_for_element(
                    'CSS_SELECTOR', 'td a')
                buildings_link.click()

                # Wait for details page
                details_page = BuildingInfo(self)
                table = details_page.ensure_table_is_loaded()
                assert table.first_row['FIELD'].text == 'Address Line 1'

                # Return to Buildings List
                details_page.wait_for_element('PARTIAL_LINK_TEXT', 'Buildings')
                details_page.find_element_by_partial_link_text(
                    'Buildings').click()
                buildings_list.reload()
                count = buildings_list.wait_for_element_by_class_name(
                    'counts')

                table = buildings_list.ensure_table_is_loaded()
                address = table.first_row['ADDRESS LINE 1']
                assert count.text == 'Showing 1 to 10 of 100 buildings'
                assert address.text == address_text

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
                year_ending = row['MASTER'].find_element_by_id(
                    'edit_tax_lot_id'
                )
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

            def test_profile_page(self):
                """
                Make sure you can click from the menu to the building list
                page and it loads, as well as the sub tabs.
                """
                # Firefox intermittenly ignores its profile settings
                # so the test will intermittently fail to the Reader
                # first view pop up.
                if ((os.getenv('TRAVIS') != 'true') and
                        (self.browser_type.name != 'Firefox')):
                    main_page = MainPage(self, use_url=True)
                    link = main_page.wait_for_element_by_id(
                        'sidebar-profile'
                    )
                    link.click()

                    # Load Profile page
                    profile_page = ProfilePage(self)
                    page_title = profile_page.wait_for_element_by_class_name(
                        'page_title'
                    )
                    assert page_title.text == 'Jane Doe'
                    section_title = profile_page.find_element_by_class_name(
                        'section_header'
                    )
                    assert section_title.text == 'Profile Information'
                    # Load security tab
                    link = profile_page.wait_for_element_by_link_text(
                        'Security'
                    )
                    link.click()
                    profile_page.reload(section='security')
                    section_title =\
                        profile_page.wait_for_element_by_class_name(
                            'section_header'
                        )
                    assert section_title.text == 'Change Password'

                    # Load developer tab
                    link = profile_page.wait_for_element_by_link_text(
                        'Developer'
                    )
                    link.click()
                    profile_page.reload(section='developer')
                    section_title = profile_page.find_element_by_class_name(
                        'section_header'
                    )
                    assert section_title.text == 'API Key'

                    # Reload Profile Info tab
                    link = profile_page.wait_for_element_by_link_text(
                        'Profile Info'
                    )
                    link.click()
                    profile_page.reload(section='profile')
                    section_title = profile_page.find_element_by_class_name(
                        'section_header'
                    )
                    assert section_title.text == 'Profile Information'

            def test_profile_information_actions(self):
                """Test the profile page form actions work."""
                # Firefox intermittenly ignores its profile settings
                # so the test will intermittently fail to the Reader
                # first view pop up.
                if ((os.getenv('TRAVIS') != 'true') and
                        (self.browser_type.name != 'Firefox')):
                    profile_page = ProfilePage(self, use_url=True)
                    first_name = profile_page.wait_for_element_by_id(
                        'first-name-text'
                    )
                    last_name = profile_page.wait_for_element_by_id(
                        'last-name-text'
                    )
                    save_changes = profile_page.wait_for_element_by_id(
                        'update_profile'
                    )
                    assert first_name.get_attribute('value') == 'Jane'
                    assert last_name.get_attribute('value') == 'Doe'

                    last_name.clear()
                    last_name.send_keys('Ray')
                    save_changes.click()

                    profile_page.reload()
                    page_title = profile_page.wait_for_element_by_class_name(
                        'page_title'
                    )
                    first_name = profile_page.find_element_by_id(
                        'first-name-text'
                    )
                    last_name = profile_page.find_element_by_id(
                        'last-name-text'
                    )
                    buttons = profile_page.find_elements_by_class_name(
                        'btn-default'
                    )
                    for button in buttons:
                        if button.text == 'Cancel':
                            cancel = button
                            break

                    assert page_title.text == 'Jane Ray'
                    assert first_name.get_attribute('value') == 'Jane'
                    assert last_name.get_attribute('value') == 'Ray'
                    # check mark appeared
                    save_changes.find_element_by_class_name('fa-check')

                    last_name.send_keys('Mee')
                    cancel.click()

                    profile_page.reload()
                    page_title = profile_page.wait_for_element_by_class_name(
                        'page_title'
                    )
                    first_name = profile_page.find_element_by_id(
                        'first-name-text'
                    )
                    last_name = profile_page.find_element_by_id(
                        'last-name-text'
                    )
                    assert page_title.text == 'Jane Ray'
                    assert first_name.get_attribute('value') == 'Jane'
                    assert last_name.get_attribute('value') == 'Ray'

            def test_profile_security_actions(self):
                """test the profile page form actions work."""
                # Firefox intermittenly ignores its profile settings
                # so the test will intermittently fail to the Reader
                # first view pop up.
                if ((os.getenv('TRAVIS') != 'true') and
                        (self.browser_type.name != 'Firefox')):
                    profile_page = ProfilePage(
                        self, use_url=True, section='security'
                    )

                    new_password = profile_page.wait_for_element_by_id(
                        'editNewPassword'
                    )
                    confirm_new_password =\
                        profile_page.wait_for_element_by_id(
                            'editConfirmNewPassword'
                        )
                    buttons = profile_page.find_elements_by_class_name('btn')
                    for button in buttons:
                        if button.text == 'Cancel':
                            cancel = button
                            break

                    new_password.send_keys('asasdfG123')
                    confirm_new_password.send_keys('asasdfG123')
                    cancel.click()

                    menu_toggle = profile_page.find_element_by_class_name(
                        'menu_toggle'
                    )
                    menu_toggle.click()
                    log_out = profile_page.find_element_by_class_name(
                        'badge_menu'
                    )
                    log_out.click()

                    # load landing page and verify we can log in
                    page = LandingPage(self)
                    username_input = page.find_element_by_id("id_email")
                    username_input.send_keys('test@example.com')
                    password_input = page.find_element_by_id("id_password")
                    password_input.send_keys('password')
                    page.find_element_by_css_selector(
                        'input[value="Log In"]'
                    ).click()
                    # should now be on main page
                    main_page = MainPage(self)
                    title_container = main_page.wait_for_element(
                        'CLASS_NAME', 'home_hero_content_container'
                    )
                    title = title_container.find_element_by_tag_name('h1')
                    assert title.text == 'Getting Started'

                    # go back to Change Password and change password this time
                    link = main_page.wait_for_element_by_id(
                        'sidebar-profile'
                    )
                    link.click()
                    profile_page.reload(section='profile')

                    # Load security tab
                    link = profile_page.wait_for_element_by_link_text(
                        'Security'
                    )
                    link.click()
                    profile_page.reload(section='security')
                    current_password = profile_page.wait_for_element_by_id(
                        'editCurrentPawword'              # sic
                    )
                    new_password = profile_page.wait_for_element_by_id(
                        'editNewPassword'
                    )
                    confirm_new_password =\
                        profile_page.wait_for_element_by_id(
                            'editConfirmNewPassword'
                        )
                    buttons = profile_page.find_elements_by_class_name('btn')
                    for button in buttons:
                        if button.text == 'Change Password':
                            change_password = button
                            break
                    current_password.clear()
                    current_password.send_keys('password')
                    new_password.clear()
                    new_password.send_keys('asasdfG123')
                    confirm_new_password.clear()
                    confirm_new_password.send_keys('asasdfG123')
                    change_password.click()

                    profile_page.reload()
                    menu_toggle = profile_page.find_element_by_class_name(
                        'menu_toggle'
                    )
                    menu_toggle.click()
                    log_out = profile_page.find_element_by_class_name(
                        'badge_menu'
                    )
                    log_out.click()

                    # load landing page and verify we can log in
                    page = LandingPage(self)
                    username_input = page.find_element_by_id("id_email")
                    username_input.send_keys('test@example.com')
                    password_input = page.find_element_by_id("id_password")
                    password_input.send_keys('asasdfG123')
                    page.find_element_by_css_selector(
                        'input[value="Log In"]'
                    ).click()
                    # should now be on main page
                    main_page = MainPage(self)
                    title_container = main_page.wait_for_element(
                        'CLASS_NAME', 'home_hero_content_container'
                    )
                    title = title_container.find_element_by_tag_name('h1')
                    assert title.text == 'Getting Started'

                    # go back to Profile Page
                    link = main_page.wait_for_element_by_id(
                        'sidebar-profile'
                    )
                    link.click()
                    profile_page.reload(section='profile')

            def test_profile_developer_actions(self):
                """test the profile page form actions work."""
                # Firefox intermittenly ignores it profile settings
                # so the test will intermittently fail to the Reader
                # first view pop up.
                if ((os.getenv('TRAVIS') != 'true') and
                        (self.browser_type.name != 'Firefox')):
                    profile_page = ProfilePage(
                        self, use_url=True, section='security'
                    )
                    # load developer tag
                    link = profile_page.wait_for_element_by_link_text(
                        'Developer'
                    )
                    link.click()

                    # check for api key
                    profile_page.reload(section='developer')
                    api_key_table = profile_page.get_api_key_table()
                    api_key = api_key_table.first_row['API KEY'].text
                    assert api_key is not None

                    # generate a new api key
                    form = profile_page.find_element_by_class_name(
                        'section_form_container'
                    )
                    form_button = form.find_element_by_tag_name(
                        'button'
                    )
                    assert form_button.text == 'Get a New API Key'
                    form_button.click()

                    # check for api key
                    profile_page.reload(section='developer')
                    api_key_table = profile_page.get_api_key_table()
                    new_api_key = api_key_table.first_row['API KEY'].text
                    assert new_api_key is not None

                    # check regenerated
                    assert new_api_key != api_key

                    # check check mark appears
                    form = profile_page.find_element_by_class_name(
                        'section_form_container'
                    )
                    form_button = form.find_element_by_tag_name(
                        'button'
                    )
                    check_mark = form_button.find_element_by_class_name('fa')
                    check_mark_class = check_mark.get_attribute('class')
                    assert "fa-check" in check_mark_class
                    assert "ng-hide" not in check_mark_class

            def test_project_list(self):
                """
                Make sure you can click from the menu to the building list
                page and it loads.
                """
                # load main page and create building snapshot
                main_page = MainPage(self, use_url=True)
                main_page.create_record(create_building=True)
                main_page.create_project()

                # click on projects in sidebar
                main_page.wait_for_element_by_id('sidebar-projects').click()
                projects_list = ProjectsList(self)

                # Ensure project is visible
                table = projects_list.ensure_table_is_loaded()
                project = table.first_row['PROJECT NAME']
                assert project.text == 'test'

            def test_project_page(self):
                """Make sure the project page loads"""
                projects_list = ProjectsList(
                    self, use_url=True,
                    create_building=True, create_project='test'
                )
                canonical_building = projects_list.canonical_building
                building_snapshot = canonical_building.canonical_snapshot

                # locate project link and navigate to project page
                table = projects_list.ensure_table_is_loaded()
                project = table.first_row['PROJECT NAME']

                project_link = project.find_element_by_class_name(
                    'table_name_link'
                )
                project_link.click()

                project_page = ProjectPage(self)

                # inspect table to see if building is present
                table = project_page.ensure_table_is_loaded()
                address_cell = table[0]['ADDRESS LINE 1']
                address = building_snapshot.address_line_1
                assert address_cell.text == address

            def test_project_building_info(self):
                """Make sure the project bulding info page loads"""
                project_page = ProjectPage(
                    self, name='test',
                    create_building=True, create_project=True
                )
                canonical_building = project_page.canonical_building
                canonical_snapshot = canonical_building.canonical_snapshot

                # locate building and click on link
                table = project_page.ensure_table_is_loaded()
                address_cell = table[0]['ADDRESS LINE 1']
                link = address_cell.find_element_by_tag_name('a')
                link.click()

                # ensure Building Info page is loaded and building is there
                building_info = ProjectBuildingInfo(self, name='test')
                table = building_info.ensure_table_is_loaded()
                row = table.find_row_by_field('FIELD', 'Address Line 1')
                assert row[1].text == canonical_snapshot.address_line_1

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
            except:                                                 # noqa
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

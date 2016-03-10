# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nlong
"""
from seed.data_importer.models import ImportFile, ImportRecord, ROW_DELIMITER
from seed.models import BuildingSnapshot, CanonicalBuilding, Project, ProjectBuilding, StatusLabel
from seed.functional.tests.base import LoggedInFunctionalTestCase, LoggedOutFunctionalTestCase


class LoginTests(LoggedOutFunctionalTestCase):

    def test_login(self):
        self.browser.get(self.live_server_url)
        username_input = self.browser.find_element_by_id("id_email")
        username_input.send_keys('test@example.com')
        password_input = self.browser.find_element_by_id("id_password")
        password_input.send_keys('password')
        self.browser.find_element_by_css_selector('input[value="Log In"]').click()
        self.wait_for_element_by_css('.menu')


class SmokeTests(LoggedInFunctionalTestCase):
    def test_dataset_list(self):
        """Make sure dataset list works."""
        import_record = ImportRecord.objects.create(
            owner=self.user,
            super_organization=self.org
        )
        ImportFile.objects.create(
            import_record=import_record
        )
        self.browser.get(self.live_server_url)
        self.wait_for_element_by_css('.menu')
        self.browser.find_element_by_id('sidebar-data').click()
        self.wait_for_element_by_css('.dataset_list')

        # Make sure there's a row in the table
        self.browser.find_element_by_css_selector('td.name')

    def test_dataset_detail(self):
        """
        Make sure you can click dataset name on dataset list page and load
        dataset.
        """
        import_record = ImportRecord.objects.create(
            owner=self.user,
            super_organization=self.org
        )
        ImportFile.objects.create(
            import_record=import_record
        )

        # Navigate to dataset list view.
        self.browser.get(self.live_server_url + '/app/#/data')
        self.wait_for_element_by_css('.dataset_list')

        # Click a dataset.
        self.browser.find_element_by_css_selector('td a.import_name').click()

        # Make sure import file is there.
        self.wait_for_element_by_css('td.data_file_name')

    def test_mapping_page(self):
        """
        Make sure you can click mapping button on dataset page and mapping
        loads.
        """
        import_record = ImportRecord.objects.create(
            owner=self.user,
            super_organization=self.org
        )
        ImportFile.objects.create(
            import_record=import_record,
            cached_first_row=ROW_DELIMITER.join(
                [u'name', u'address']
            ),
            cached_second_to_fifth_row=ROW_DELIMITER.join(
                ['name', 'address.']
            )
        )

        # Navigate to dataset detail view.
        self.browser.get(self.live_server_url + '/app/#/data/%s' % import_record.pk)

        # Wait for load.
        self.wait_for_element_by_css('td.data_file_name')

        # Click mapping button.
        self.browser.find_element_by_id('data-mapping-0').click()

        # Make sure mapping table is shown.
        self.wait_for_element_by_css('div.mapping')

    def test_building_list(self):
        """
        Make sure you can click from the menu to the building list page and it
        loads.
        """
        import_record = ImportRecord.objects.create(
            owner=self.user,
            super_organization=self.org
        )
        import_file = ImportFile.objects.create(
            import_record=import_record
        )

        canonical_building = CanonicalBuilding.objects.create()
        building = BuildingSnapshot.objects.create(
            super_organization=self.org,
            import_file=import_file, canonical_building=canonical_building,
            address_line_1='address'
        )
        canonical_building.canonical_snapshot = building
        canonical_building.save()

        self.browser.get(self.live_server_url)
        self.wait_for_element_by_css('.menu')
        self.browser.find_element_by_id('sidebar-buildings').click()
        self.wait_for_element_by_css('#building-list')

        # Make sure a building is present.
        self.browser.find_element_by_css_selector('#building-list-table td')

    def test_building_list_tab_settings(self):
        """Make sure building list settings tab loads."""
        import_record = ImportRecord.objects.create(
            owner=self.user,
            super_organization=self.org
        )
        import_file = ImportFile.objects.create(
            import_record=import_record
        )

        canonical_building = CanonicalBuilding.objects.create()
        building = BuildingSnapshot.objects.create(
            super_organization=self.org,
            import_file=import_file, canonical_building=canonical_building,
            address_line_1='address'
        )
        canonical_building.canonical_snapshot = building
        canonical_building.save()

        self.browser.get(self.live_server_url + '/app/#/buildings/settings')
        self.wait_for_element_by_css('#building-settings')

    def test_building_list_tab_reports(self):
        """Make sure building list reports tab loads."""
        import_record = ImportRecord.objects.create(
            owner=self.user,
            super_organization=self.org
        )
        import_file = ImportFile.objects.create(
            import_record=import_record
        )

        canonical_building = CanonicalBuilding.objects.create()
        building = BuildingSnapshot.objects.create(
            super_organization=self.org,
            import_file=import_file, canonical_building=canonical_building,
            address_line_1='address'
        )
        canonical_building.canonical_snapshot = building
        canonical_building.save()

        self.browser.get(self.live_server_url + '/app/#/buildings/reports')
        self.wait_for_element_by_css('.building-reports')

    def test_building_list_tab_labels(self):
        """Make sure building list labels tab loads."""
        import_record = ImportRecord.objects.create(
            owner=self.user,
            super_organization=self.org
        )
        import_file = ImportFile.objects.create(
            import_record=import_record
        )

        canonical_building = CanonicalBuilding.objects.create()
        building = BuildingSnapshot.objects.create(
            super_organization=self.org,
            import_file=import_file, canonical_building=canonical_building,
            address_line_1='address'
        )
        canonical_building.canonical_snapshot = building
        canonical_building.save()

        StatusLabel.objects.create(name='test', super_organization=self.org)

        self.browser.get(self.live_server_url + '/app/#/buildings/labels')

        # Make sure a label is in the list.
        self.wait_for_element_by_css('tbody tr td span.label')

    def test_building_detail(self):
        """Make sure building detail page loads."""
        import_record = ImportRecord.objects.create(
            owner=self.user,
            super_organization=self.org
        )
        import_file = ImportFile.objects.create(
            import_record=import_record
        )

        canonical_building = CanonicalBuilding.objects.create()
        building = BuildingSnapshot.objects.create(
            super_organization=self.org,
            import_file=import_file, canonical_building=canonical_building,
            address_line_1='address'
        )
        canonical_building.canonical_snapshot = building
        canonical_building.save()

        self.browser.get(self.live_server_url + '/app/#/buildings')
        self.wait_for_element_by_css('#building-list')

        # Click a builing.
        self.browser.find_element_by_css_selector('td a').click()

        # We know detail page is loaded when projects tab is there.
        self.wait_for_element_by_css('#projects')

    def test_building_detail_tab_projects(self):
        """Make sure building detail projects tab shows project."""
        import_record = ImportRecord.objects.create(
            owner=self.user,
            super_organization=self.org
        )
        import_file = ImportFile.objects.create(
            import_record=import_record
        )

        canonical_building = CanonicalBuilding.objects.create()
        building = BuildingSnapshot.objects.create(
            super_organization=self.org,
            import_file=import_file, canonical_building=canonical_building,
            address_line_1='address'
        )
        canonical_building.canonical_snapshot = building
        canonical_building.save()

        project = Project.objects.create(name='test', owner=self.user, super_organization=self.org)
        ProjectBuilding.objects.create(project=project, building_snapshot=building)

        self.browser.get(self.live_server_url + '/app/#/buildings/%s/projects' % canonical_building.pk)

        # Make sure project is in list.
        self.wait_for_element_by_css('tbody tr td a')

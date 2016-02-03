# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nlong
"""
import time
import json
import os
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.common.exceptions import NoSuchAttributeException, StaleElementReferenceException, NoSuchElementException
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.landing.models import SEEDUser as User

class ElementNotVisibleException(Exception):
    pass

class LogIn(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(self):
        super(LogIn, self).setUpClass()
        self.selenium = webdriver.Firefox()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(LogIn, cls).tearDownClass()

    @unittest.skipIf(os.environ.get("TRAVIS") == "true", "https://github.com/SEED-platform/seed/issues/531")
    def test_login(self):

        # Test LogIn Process

        # Generate User and Selenium Resources
        user_details = {
            'username': 'test_user@demo.com', # the username needs to be in the form of an email.
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'testsAre',
            'last_name': 'superAwesome'
        }
        self.user = User.objects.create_user(**user_details)
        self.user.generate_key()
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)
        self.headers = {'HTTP_AUTHORIZATION': '%s:%s' % (self.user.username, self.user.api_key)}
        self.selenium.get('%s' % self.live_server_url)

        # Send User Data
        username_input = self.selenium.find_element_by_id("id_email")
        username_input.send_keys('test_user@demo.com')
        password_input = self.selenium.find_element_by_id("id_password")
        password_input.send_keys('test_pass')
        self.selenium.find_element_by_xpath('//input[@value="Log In"]').click()

        # Add Sample Data to Database

        # Generate Resources for Data Entry Creation
        r = self.client.get('/app/accounts/get_organizations/', follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)
        raw_building_file = os.path.relpath(os.path.join('seed/tests/data', 'covered-buildings-sample.csv'))
        self.assertTrue(os.path.isfile(raw_building_file), 'could not find file')
        payload = {'organization_id': organization_id, 'name': 'Sample'}

        # Create Data Set Entry
        r = self.client.post('/app/create_dataset/', data=json.dumps(payload), content_type='application/json',
                             **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        #time.sleep(10)
        self.assertEqual(r['status'], 'success')
        data_set_id = r['id']

        # Retrieve and Verify Upload Details
        upload_details = self.client.get('/data/get_upload_details/', follow=True, **self.headers)
        self.assertEqual(upload_details.status_code, 200)
        upload_details = json.loads(upload_details.content)
        self.assertEqual(upload_details['upload_mode'], 'filesystem')

        # Generate Dictionary for Data Upload
        fsysparams = {
            'qqfile': raw_building_file,
            'import_record': data_set_id,
            'source_type': 'Assessed Raw',
            'filename': open(raw_building_file, 'rb')
        }

        # Upload Data and Check Response
        r = self.client.post(upload_details['upload_path'], fsysparams, follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['success'], True)

        # Save Raw Data Upload
        payload = {
            'file_id': r['import_file_id'],
            'organization_id': str(organization_id)
        }
        r = self.client.post('/app/save_raw_data/', data=json.dumps(payload), content_type='application/json',
                             follow=True, **self.headers)

        # Navigate to Data Mapping Page

        self.wait_for_visibility('nav-data')

        # Access Dataset_list Webpage
        self.selenium.find_element_by_link_text("Data").click()
        self.wait_for_visibility('data-link-0')

        # Access Dataset_details Webpage
        self.selenium.find_element_by_link_text('Sample').click()
        self.wait_for_visibility('data-mapping-0')

        # Access Mapping Webpage
        self.selenium.find_element_by_id('data-mapping-0').click()
        self.wait_for_visibility('mapped-header-0')

        # Map Data

        # Generate Mapping Dictionary
        mapping_dict = {
            'UBI': 'Tax Lot Id',
            'GBA': 'Gross Floor Area',
            'BLDGS': 'Buildings',
            'Address': 'Address Line 1',
            'Owner': 'Owner',
            'City': 'City',
            'State': 'State Province',
            'Zip': 'Postal Code',
            'Property Type': 'Use Description',
            'AYB_YearBuilt': 'Year Built'
        }

        # Map 'Mapped' Data Fields
        for i in range(5):
            request_id = "mapped-header-%s" % i
            dict_key = self.selenium.find_element_by_id(request_id).text
            self.selenium.find_element_by_css_selector("#mapped-row-input-%s > #mapped-row-input-box-%s" % (i, i)).clear()
            self.selenium.find_element_by_css_selector("#mapped-row-input-%s > #mapped-row-input-box-%s" % (i, i)).send_keys(mapping_dict[dict_key])

        # Map 'Duplicate' Data Fields
        for i in range(4):
            request_id = "duplicate-header-%s" % i
            dict_key = self.selenium.find_element_by_id(request_id).text
            self.selenium.find_element_by_css_selector("#duplicate-row-input-%s > #duplicate-row-input-box-%s" % (i, i)).clear()
            self.selenium.find_element_by_css_selector("#duplicate-row-input-%s > #duplicate-row-input-box-%s" % (i, i)).send_keys(mapping_dict[dict_key])

        # Navigate through Data Saving/Matching
        self.selenium.find_element_by_id('map-data-button').click()
        self.wait_for_visibility('verify-mapping-table',30)
        self.selenium.find_element_by_id('save-mapping').click()
        self.wait_for_visibility('confirm-mapping')
        self.selenium.find_element_by_id('confirm-mapping').click()
        self.wait_for_visibility('view-buildings',120)
        self.selenium.find_element_by_id('view-buildings').click()
        self.wait_for_visibility('verify-mapping-table')
        self.selenium.find_element_by_id('list-settings').click()

        # Retrieve and Verify Upload Details
        upload_details = self.client.get('/data/get_upload_details/', follow=True, **self.headers)
        self.assertEqual(upload_details.status_code, 200)
        upload_details = json.loads(upload_details.content)
        self.assertEqual(upload_details['upload_mode'], 'filesystem')

        raw_portfolio_file = os.path.relpath(os.path.join('seed/tests/data', 'portfolio-manager-sample.csv'))
        self.assertTrue(os.path.isfile(raw_portfolio_file), 'could not find file')

        # Generate Dictionary for Data Upload
        fsysparams = {
            'qqfile': raw_portfolio_file,
            'import_record': data_set_id,
            'source_type': 'Portfolio Raw',
            'filename': open(raw_portfolio_file, 'rb')
        }

        # Upload Data and Check Response
        r = self.client.post(upload_details['upload_path'], fsysparams, follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r['success'], True)

        # Save Raw Data Upload
        payload = {
            'file_id': r['import_file_id'],
            'organization_id': str(organization_id)
        }
        r = self.client.post('/app/save_raw_data/', data=json.dumps(payload), content_type='application/json',
                             follow=True, **self.headers)

        # Navigate to Data Mapping Page
        self.wait_for_visibility('sidebar-data')
        self.selenium.find_element_by_id('sidebar-data').click()
        self.wait_for_visibility('data-link-0')
        self.selenium.find_element_by_link_text('Sample').click()
        self.wait_for_visibility('data-mapping-1')

        # Access Mapping Webpage
        self.selenium.find_element_by_id('data-mapping-1').click()
        self.wait_for_visibility('duplicate-table')

        # Define Mapping dictonary
        mapping_dict = {
            'Property Id': 'Pm Property Id',
            'Property Name': 'Premises Name Identifier',
            'Year Ending': 'Year Ending',
            'Property Floor Area (Buildings and Parking) (ft2)': 'Gross Floor Area',
            'Address 1': 'Address Line 1',
            'Address 2': 'Address Line 2',
            'City': 'City',
            'State/Province': 'State Province',
            'Postal Code': 'Postal Code',
            'Year Built': 'Year Built',
            'ENERGY STAR Score': 'Energy Score',
            'Site EUI (kBtu/ft2)': 'Site Eui',
            'Weather Normalized Site EUI (kBtu/ft2)': 'Site Eui Weather Normalized',
            'Source EUI (kBtu/ft2)': 'Source Eui',
            'Weather Normalized Source EUI (kBtu/ft2)': 'Source Eui Weather Normalized',
            'National Median Source EUI (kBtu/ft2)': 'Source Eui National Median',
            'Organization': 'Building Certification',
            'Release Date': 'Release Date',
            'National Median Site EUI (kBtu/ft2)': 'Site Eui National Median',
            'Generation Date': 'Generation Date',
            'Total GHG Emissions (MtCO2e)': 'GHG Emissions',
            'Parking - Gross Floor Area (ft2)': 'Parking Floor Area'
        }

        # Map 'Mapped' Data Fields
        for i in range(16):
            request_id = "mapped-header-%s" % i
            dict_key = self.selenium.find_element_by_id(request_id).text
            self.selenium.find_element_by_css_selector("#mapped-row-input-%s > #mapped-row-input-box-%s" % (i, i)).clear()
            self.selenium.find_element_by_css_selector("#mapped-row-input-%s > #mapped-row-input-box-%s" % (i, i)).send_keys(mapping_dict[dict_key])

        # Map 'Duplicate' Data Fields
        for i in range(6):
            request_id = "duplicate-header-%s" % i
            dict_key = self.selenium.find_element_by_id(request_id).text
            self.selenium.find_element_by_css_selector("#duplicate-row-input-%s > #duplicate-row-input-box-%s" % (i, i)).clear()
            self.selenium.find_element_by_css_selector("#duplicate-row-input-%s > #duplicate-row-input-box-%s" % (i, i)).send_keys(mapping_dict[dict_key])

        self.selenium.find_element_by_id('map-data-button').click()
        self.wait_for_visibility('verify-mapping-table',15)
        self.selenium.find_element_by_id('save-mapping').click()
        self.wait_for_visibility('confirm-mapping')
        self.selenium.find_element_by_id('confirm-mapping').click()
        self.wait_for_visibility('review-mapping',60)
        self.selenium.find_element_by_id('review-mapping').click()
        self.wait_for_visibility('sidebar-profile')
        self.selenium.find_element_by_id('sidebar-profile').click()
        self.wait_for_visibility('first-name-text')
        self.selenium.find_element_by_id('first-name-text').clear()
        self.selenium.find_element_by_id('first-name-text').send_keys('thisTestIs')
        self.selenium.find_element_by_id('last-name-text').clear()
        self.selenium.find_element_by_id('last-name-text').send_keys('goingQuiteWell')
        self.wait_for_visibility('update_profile')
        self.selenium.find_element_by_id('update_profile').click()
        self.selenium.find_element_by_id('sidebar-projects').click()
        self.wait_for_visibility('project-table')
        self.selenium.find_element_by_id('sidebar-buildings').click()
        self.wait_for_visibility('building-list-table')
        self.selenium.find_element_by_id('neg-neg-2')
        self.selenium.find_element_by_id('neg-neg-2').click()
        self.wait_for_visibility('sidebar-accounts')
        self.selenium.find_element_by_id('sidebar-accounts').click()
        self.wait_for_visibility('org-owned-tables')
        self.selenium.find_element_by_id('sidebar-feedback').click()
        self.wait_for_visibility('text-block')
        self.selenium.find_element_by_id('sidebar-about').click()
        self.wait_for_visibility('text-block')



    def get_org_id(self, dict, username):
        '''Return the org id from the passed dictionary and username'''
        id = None
        for ctr in range(len(dict['organizations'])):
            if dict['organizations'][ctr]['owners'][0]['email'] == username:
                id = dict['organizations'][ctr]['org_id']
                break

        return id

    def wait_for_visibility(self, selector, timeout_seconds=10):
        '''
        :param selector: angularjs rendered id to wait for in 'id' format
        :param timeout_seconds: time to wait for angularjs to render the selector id
        :return: returns control to the script, or throws ElementNotVisibleException
        '''
        retries = timeout_seconds*2
        while retries:
            try:
                element = self.selenium.find_element_by_id(selector)
                if element.is_displayed():
                    time.sleep(0)      # Enable this to be able to see what's going on
                    return element
            except (NoSuchAttributeException,
                    NoSuchElementException,
                    StaleElementReferenceException):
                if retries <= 0:
                    raise
                else:
                    pass

            retries = retries - 1
            time.sleep(0.5)
        raise ElementNotVisibleException(
            "Element %s not visible despite waiting for %s seconds" % (selector, timeout_seconds)
        )


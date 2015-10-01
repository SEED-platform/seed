import time
import json
import os
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.common.exceptions import NoSuchAttributeException, StaleElementReferenceException, NoSuchElementException
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.landing.models import SEEDUser as User

class ElementNotVisibleException(Exception):
    pass

class LogIn(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(self):
        super(LogIn, self).setUpClass()
        self.selenium = WebDriver()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(LogIn, cls).tearDownClass()

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
        print "Mark One"
        print r
        time.sleep(10)
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
        print "Mark Two"
        print r
        time.sleep(10)
        self.assertEqual(r['success'], True)

        # Save Raw Data Upload
        payload = {
            'file_id': r['import_file_id'],
            'organization_id': organization_id
        }
        r = self.client.post('/app/save_raw_data/', data=json.dumps(payload), content_type='application/json',
                             follow=True, **self.headers)

        print "Mark Three"
        print json.loads(r.content)
        time.sleep(10)

        # Navigate to Data Mapping Page

        # Access Dataset_list Webpage
        self.selenium.find_element_by_link_text("Data").click()
        self.wait_for_visibility('data-link-0')

        # Access Dataset_details Webpage
        self.selenium.find_element_by_link_text('Sample\"').click()
        self.wait_for_visibility('data-mapping-0')

        # Access Mapping Webpage
        self.selenium.find_element_by_link_text('Data Mapping').click()
        self.wait_for_visibility('mapped-header-0', 30)

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

        print "Beginning Column Mapping"

        self.selenium.find_element_by_id('map-data-button').click()
        time.sleep(6)

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
# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
from os import path
from django.core.cache import cache
from django.core.files import File
from django.test import TestCase
from django.core.urlresolvers import reverse

from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.tests import util
from seed import tasks
from seed.cleansing.models import Cleansing

from seed.models import (
    ASSESSED_BS,
    PORTFOLIO_BS,
    BuildingSnapshot,
)


class CleansingDataTestCoveredBuilding(TestCase):
    def setUp(self):
        self.user_details = {
            'username': 'testuser@example.com',
            'email': 'testuser@example.com',
            'password': 'test_password'
        }
        self.user = User.objects.create_user(**self.user_details)
        self.login_url = reverse('landing:login')

        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        self.import_record = ImportRecord.objects.create(owner=self.user)
        self.import_record.super_organization = self.org
        self.import_record.save()
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record
        )

        self.import_file.is_espm = False
        self.import_file.source_type = 'ASSESSED_RAW'
        self.import_file.file = File(
            open(path.join(path.dirname(__file__), 'test_data', 'covered-buildings-sample-with-errors.csv'))
        )

        self.import_file.save()

        # tasks.save_raw_data(self.import_file.pk)

    def test_simple_login(self):
        self.client.post(self.login_url, self.user_details, secure=True)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_cleanse(self):
        # Import the file and run mapping

        # This is silly, the mappings are backwards from what you would expect. The key is the BS field, and the
        # value is the value in the CSV
        fake_mappings = {
            'city': 'city',
            'postal_code': 'Zip',
            'gross_floor_area': 'GBA',
            'building_count': 'BLDGS',
            'year_built': 'AYB_YearBuilt',
            'state_province': 'State',
            'address_line_1': 'Address',
            'owner': 'Owner',
            'property_notes': 'Property Type',
            'tax_lot_id': 'UBI',
            'custom_id_1': 'Custom ID',
            'pm_property_id': 'PM Property ID'
        }

        tasks.save_raw_data(self.import_file.id)
        util.make_fake_mappings(fake_mappings, self.org)
        tasks.map_data(self.import_file.id)

        qs = BuildingSnapshot.objects.filter(
            import_file=self.import_file,
            source_type=ASSESSED_BS,
        ).iterator()

        c = Cleansing(self.org)
        c.cleanse(qs)

        self.assertEqual(len(c.results), 2)

        result = [v for v in c.results.values() if v['address_line_1'] == '95373 E Peach Avenue']
        if len(result) == 1:
            result = result[0]
        else:
            raise RuntimeError('Non unity results')

        self.assertTrue(result['address_line_1'], '95373 E Peach Avenue')
        self.assertTrue(result['tax_lot_id'], '10107/c6596')
        res = [{
            'field': u'pm_property_id',
            'formatted_field': u'PM Property ID',
            'value': u'',
            'message': u'PM Property ID is missing',
            'detailed_message': u'PM Property ID is missing',
            'severity': u'error'
        }]
        self.assertEqual(res, result['cleansing_results'])

        result = [v for v in c.results.values() if v['address_line_1'] == '120243 E True Lane']
        if len(result) == 1:
            result = result[0]
        else:
            raise RuntimeError('Non unity results')

        res = [{
            'field': u'year_built',
            'formatted_field': u'Year Built',
            'value': 0,
            'message': u'Year Built out of range',
            'detailed_message': u'Year Built [0] < 1700',
            'severity': u'error'
        }, {
            'field': u'gross_floor_area',
            'formatted_field': u'Gross Floor Area',
            'value': 10000000000.0,
            'message': u'Gross Floor Area out of range',
            'detailed_message': u'Gross Floor Area [10000000000.0] > 7000000.0',
            'severity': u'error'
        }, {
            'field': u'custom_id_1',
            'formatted_field': u'Custom ID 1',
            'value': u'',
            'message': u'Custom ID 1 is missing',
            'detailed_message': u'Custom ID 1 is missing',
            'severity': u'error'
        }, {
            'field': u'pm_property_id',
            'formatted_field': u'PM Property ID',
            'value': u'',
            'message': u'PM Property ID is missing',
            'detailed_message': u'PM Property ID is missing',
            'severity': u'error'
        }]
        self.assertItemsEqual(res, result['cleansing_results'])

        result = [v for v in c.results.values() if v['address_line_1'] == '1234 Peach Tree Avenue']
        self.assertEqual(len(result), 0)
        self.assertEqual(result, [])


class CleansingDataTestPM(TestCase):
    def setUp(self):
        self.user_details = {
            'username': 'testuser@example.com',
            'email': 'testuser@example.com',
            'password': 'test_password'
        }
        self.user = User.objects.create_user(**self.user_details)
        self.login_url = reverse('landing:login')

        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        self.import_record = ImportRecord.objects.create(owner=self.user)
        self.import_record.super_organization = self.org
        self.import_record.save()
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record
        )

        self.import_file.is_espm = True
        self.import_file.source_type = 'Portfolio Raw'
        self.import_file.file = File(
            open(path.join(path.dirname(__file__), 'test_data', 'portfolio-manager-sample-with-errors.csv'))
        )

        self.import_file.save()

        # tasks.save_raw_data(self.import_file.pk)

    def test_cleanse(self):
        # Import the file and run mapping

        # Year Ending,ENERGY STAR Score,Total GHG Emissions (MtCO2e),Weather Normalized Site EUI (kBtu/ft2),
        # National Median Site EUI (kBtu/ft2),Source EUI (kBtu/ft2),Weather Normalized Source EUI (kBtu/ft2),
        # National Median Source EUI (kBtu/ft2),Parking - Gross Floor Area (ft2),Organization
        # Release Date
        fake_mappings = {
            'pm_property_id': u'Property Id',
            'property_name': u'Property Name',
            'address_line_1': u'Address 1',
            'address_line_2': u'Address 2',
            'city': u'City',
            'state_province': u'State/Province',
            'postal_code': u'Postal Code',
            'year_built': u'Year Built',
            'gross_floor_area': u'Property Floor Area (Buildings and Parking) (ft2)',
            'site_eui': u'Site EUI (kBtu/ft2)',
            'generation_date': u'Generation Date'
        }

        tasks.save_raw_data(self.import_file.id)
        util.make_fake_mappings(fake_mappings, self.org)
        tasks.map_data(self.import_file.id)

        qs = BuildingSnapshot.objects.filter(
            import_file=self.import_file,
            source_type=PORTFOLIO_BS,
        ).iterator()

        c = Cleansing(self.org)
        c.cleanse(qs)

        self.assertEqual(len(c.results), 2)

        result = [v for v in c.results.values() if v['address_line_1'] == '120243 E True Lane']
        if len(result) == 1:
            result = result[0]
        else:
            raise RuntimeError('Non unity results')

        res = [{
            'field': u'pm_property_id',
            'formatted_field': u'PM Property ID',
            'value': u'',
            'message': u'PM Property ID is missing',
            'detailed_message': u'PM Property ID is missing',
            'severity': u'error'
        }]
        self.assertEqual(res, result['cleansing_results'])

        result = [v for v in c.results.values() if v['address_line_1'] == '95373 E Peach Avenue']
        if len(result) == 1:
            result = result[0]
        else:
            raise RuntimeError('Non unity results')

        res = [{
            'field': u'site_eui',
            'formatted_field': u'Site EUI',
            'value': 0.1,
            'message': u'Site EUI out of range',
            'detailed_message': u'Site EUI [0.1] < 10.0',
            'severity': u'warning'
        }]
        self.assertEqual(res, result['cleansing_results'])


class CleansingDataSample(TestCase):
    def setUp(self):
        self.user_details = {
            'username': 'testuser@example.com',
            'email': 'testuser@example.com',
            'password': 'test_password'
        }
        self.user = User.objects.create_user(**self.user_details)
        self.login_url = reverse('landing:login')

        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        self.import_record = ImportRecord.objects.create(owner=self.user)
        self.import_record.super_organization = self.org
        self.import_record.save()
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record
        )

        self.import_file.is_espm = False
        self.import_file.source_type = 'ASSESSED_RAW'
        self.import_file.file = File(
            open(path.join(path.dirname(__file__), 'test_data', 'data-cleansing-sample.csv'))
        )

        self.import_file.save()

        # tasks.save_raw_data(self.import_file.pk)

    def test_cleanse(self):
        # Import the file and run mapping

        # This is silly, the mappings are backwards from what you would expect. The key is the BS field, and the
        # value is the value in the CSV
        fake_mappings = {
            'block_number': 'block_number',
            'error_type': 'error type',
            'building_count': 'building_count',
            'conditioned_floor_area': 'conditioned_floor_area',
            'energy_score': 'energy_score',
            'gross_floor_area': 'gross_floor_area',
            'lot_number': 'lot_number',
            'occupied_floor_area': 'occupied_floor_area',
            'postal_code': 'postal_code',
            'site_eui': 'site_eui',
            'site_eui_weather_normalized': 'site_eui_weather_normalized',
            'source_eui': 'source_eui',
            'source_eui_weather_normalized': 'source_eui_weather_normalized',
            'address_line_1': 'address_line_1',
            'address_line_2': 'address_line_2',
            'building_certification': 'building_certification',
            'city': 'city',
            'custom_id_1': 'custom_id_1',
            'district': 'district',
            'energy_alerts': 'energy_alerts',
            'owner': 'owner',
            'owner_address': 'owner_address',
            'owner_city_state': 'owner_city_state',
            'owner_email': 'owner_email',
            'owner_postal_code': 'owner_postal_code',
            'owner_telephone': 'owner_telephone',
            'pm_property_id': 'pm_property_id',
            'property_name': 'property_name',
            'property_notes': 'property_notes',
            'space_alerts': 'space_alerts',
            'state_province': 'state_province',
            'tax_lot_id': 'tax_lot_id',
            'use_description': 'use_description',
            'generation_date': 'generation_date',
            'recent_sale_date': 'recent_sale_date',
            'release_date': 'release_date',
            'year_built': 'year_built',
            'year_ending': 'year_ending',
        }

        tasks.save_raw_data(self.import_file.id)
        util.make_fake_mappings(fake_mappings, self.org)
        tasks.map_data(self.import_file.id)

        qs = BuildingSnapshot.objects.filter(
            import_file=self.import_file,
            source_type=ASSESSED_BS,
        ).iterator()

        c = Cleansing(self.org)
        c.cleanse(qs)

        # print data
        # This only checks to make sure the 35 errors have occurred.
        self.assertEqual(len(c.results), 35)


class CleansingViewTests(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details)
        self.client.login(**user_details)

    def test_get_cleansing_results(self):
        data = {'test': 'test'}
        cache.set('cleansing_results__1', data)
        response = self.client.get(reverse('cleansing:get_cleansing_results'), {'import_file_id': 1})
        self.assertEqual(json.loads(response.content)['data'], data)

    def test_get_progress(self):
        data = {'status': 'success', 'progress': 85}
        cache.set(':1:SEED:get_progress:PROG:1', data)
        response = self.client.get(reverse('cleansing:get_progress'), {'import_file_id': 1})
        self.assertEqual(json.loads(response.content), 85)

    def test_get_csv(self):
        data = [{
            'address_line_1': '',
            'pm_property_id': '',
            'tax_lot_id': '',
            'custom_id_1': '',
            'cleansing_results': [{
                'formatted_field': '',
                'detailed_message': '',
                'severity': '',
            }]
        }]
        cache.set('cleansing_results__1', data)
        response = self.client.get(reverse('cleansing:get_csv'), {'import_file_id': 1})
        self.assertEqual(200, response.status_code)

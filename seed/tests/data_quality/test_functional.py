# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
from os import path

from django.core.files import File
from django.core.urlresolvers import reverse
from django.test import TestCase

from seed.data_importer import tasks
from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import (
    ASSESSED_BS,
    PORTFOLIO_BS,
    PropertyState,
    TaxLotState,
    Column,
    StatusLabel,
)
from seed.models.data_quality import (
    DataQualityCheck,
    TYPE_NUMBER,
    RULE_TYPE_CUSTOM,
    SEVERITY_ERROR,
)

_log = logging.getLogger(__name__)


class DataQualityTestCoveredBuilding(TestCase):

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
            open(path.join(
                path.dirname(__file__),
                '../data/covered-buildings-sample-with-errors.csv')
            )
        )
        self.import_file.save()
        self.import_file_mapping = path.join(
            path.dirname(__file__),
            "../data/covered-buildings-sample-with-errors-mappings.csv"
        )

        tasks.save_raw_data(self.import_file.id)
        Column.create_mappings_from_file(self.import_file_mapping, self.org, self.user)
        tasks.map_data(self.import_file.id)

    def test_simple_login(self):
        self.client.post(self.login_url, self.user_details, secure=True)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_property_state_quality(self):
        # Import the file and run mapping
        qs = PropertyState.objects.filter(
            import_file=self.import_file,
        ).iterator()

        d = DataQualityCheck.retrieve(self.org)
        d.check_data('PropertyState', qs)
        self.assertEqual(len(d.results), 7)

        result = d.retrieve_result_by_address('95373 E Peach Avenue')
        self.assertTrue(result['address_line_1'], '95373 E Peach Avenue')
        res = [{
            "severity": "error",
            "value": "",
            "field": "pm_property_id",
            "table_name": "PropertyState",
            "message": "PM Property ID is null",
            "detailed_message": "PM Property ID is null",
            "formatted_field": "PM Property ID"
        }]
        self.assertEqual(res, result['data_quality_results'])

        result = d.retrieve_result_by_address('120243 E True Lane')
        res = [
            {
                "severity": "error",
                "value": "10000000000.0",
                "field": "gross_floor_area",
                "table_name": "PropertyState",
                "message": "Gross Floor Area out of range",
                "detailed_message": "Gross Floor Area [10000000000.0] > 7000000.0",
                "formatted_field": "Gross Floor Area"
            },
            {
                "severity": "error",
                "value": "0",
                "field": "year_built",
                "table_name": "PropertyState",
                "message": "Year Built out of range",
                "detailed_message": "Year Built [0] < 1700",
                "formatted_field": "Year Built"
            },
            {
                "severity": "error",
                "value": "",
                "field": "custom_id_1",
                "table_name": "PropertyState",
                "message": "Custom ID 1 (Property) is null",
                "detailed_message": "Custom ID 1 (Property) is null",
                "formatted_field": "Custom ID 1 (Property)"
            },
            {
                "severity": "error",
                "value": "",
                "field": "pm_property_id",
                "table_name": "PropertyState",
                "message": "PM Property ID is null",
                "detailed_message": "PM Property ID is null",
                "formatted_field": "PM Property ID"
            }
        ]
        self.assertItemsEqual(res, result['data_quality_results'])

        result = d.retrieve_result_by_address('1234 Peach Tree Avenue')
        self.assertEqual(result, None)

    def test_tax_lot_state_quality(self):
        # Import the file and run mapping
        qs = TaxLotState.objects.filter(
            import_file=self.import_file
        ).iterator()

        d = DataQualityCheck.retrieve(self.org)
        d.check_data('TaxLotState', qs)
        # import json
        # print json.dumps(d.results, indent=2)
        self.assertEqual(len(d.results), 4)


class DataQualityTestPM(TestCase):

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
            open(path.join(path.dirname(__file__),
                           '../data/portfolio-manager-sample-with-errors.csv'))
        )
        self.import_file.save()

    def test_check(self):
        # Import the file and run mapping

        # Year Ending,Energy Score,Total GHG Emissions (MtCO2e),Weather Normalized Site EUI (kBtu/ft2),
        # National Median Site EUI (kBtu/ft2),Source EUI (kBtu/ft2),Weather Normalized Source EUI (kBtu/ft2),
        # National Median Source EUI (kBtu/ft2),Parking - Gross Floor Area (ft2),Organization
        # Release Date
        fake_mappings = [
            {
                "from_field": u'Property Id',
                "to_table_name": u'PropertyState',
                "to_field": u'pm_property_id',
            }, {
                "from_field": u'Property Name',
                "to_table_name": u'PropertyState',
                "to_field": u'property_name',
            }, {
                "from_field": u'Address 1',
                "to_table_name": u'PropertyState',
                "to_field": u'address_line_1',
            }, {
                "from_field": u'Address 2',
                "to_table_name": u'PropertyState',
                "to_field": u'address_line_2',
            }, {
                "from_field": u'City',
                "to_table_name": u'PropertyState',
                "to_field": u'city',
            }, {
                "from_field": u'State/Province',
                "to_table_name": u'PropertyState',
                "to_field": u'state_province',
            }, {
                "from_field": u'Postal Code',
                "to_table_name": u'PropertyState',
                "to_field": u'postal_code',
            }, {
                "from_field": u'Year Built',
                "to_table_name": u'PropertyState',
                "to_field": u'year_built',
            }, {
                "from_field": u'Property Floor Area (Buildings and Parking) (ft2)',
                "to_table_name": u'PropertyState',
                "to_field": u'gross_floor_area',
            }, {
                "from_field": u'Site EUI (kBtu/ft2)',
                "to_table_name": u'PropertyState',
                "to_field": u'site_eui',
            }, {
                "from_field": u'Generation Date',
                "to_table_name": u'PropertyState',
                "to_field": u'generation_date',
            }
        ]

        tasks.save_raw_data(self.import_file.id)
        Column.create_mappings(fake_mappings, self.org, self.user)
        tasks.map_data(self.import_file.id)

        qs = PropertyState.objects.filter(
            import_file=self.import_file,
            source_type=PORTFOLIO_BS,
        ).iterator()

        d = DataQualityCheck.retrieve(self.org)
        d.check_data('PropertyState', qs)

        _log.debug(d.results)

        self.assertEqual(len(d.results), 2)

        result = d.retrieve_result_by_address('120243 E True Lane')
        res = [
            {
                'severity': 'error',
                'value': None,
                'field': u'custom_id_1',
                'table_name': u'PropertyState',
                'message': 'Custom ID 1 (Property) is null',
                'detailed_message': 'Custom ID 1 (Property) is null',
                'formatted_field': 'Custom ID 1 (Property)'},
            {
                'severity': 'error',
                'value': u'',
                'field': u'pm_property_id',
                'table_name': u'PropertyState',
                'message': 'PM Property ID is null',
                'detailed_message': 'PM Property ID is null',
                'formatted_field': 'PM Property ID'
            }
        ]
        self.assertEqual(res, result['data_quality_results'])

        result = d.retrieve_result_by_address('95373 E Peach Avenue')
        res = [
            {
                'field': u'site_eui',
                'formatted_field': u'Site EUI',
                'value': '0.1',
                'table_name': u'PropertyState',
                'message': u'Site EUI out of range',
                'detailed_message': u'Site EUI [0.1] < 10.0',
                'severity': u'warning'
            },
            {
                'severity': 'error',
                'value': None,
                'field': u'custom_id_1',
                'table_name': u'PropertyState',
                'message': 'Custom ID 1 (Property) is null',
                'detailed_message': 'Custom ID 1 (Property) is null',
                'formatted_field': 'Custom ID 1 (Property)'
            }
        ]
        self.assertEqual(res, result['data_quality_results'])


class DataQualitySample(TestCase):

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
            open(path.join(path.dirname(__file__),
                           '../data/data-quality-check-sample.csv')))

        self.import_file.save()

    def test_check(self):
        # Import the file and run mapping

        # This is silly, the mappings are backwards from what you would expect.
        # The key is the BS field, and the value is the value in the CSV

        fake_mappings = [
            {
                "from_field": u'block_number',
                "to_table_name": u'PropertyState',
                "to_field": u'block_number',
            }, {
                "from_field": u'error_type',
                "to_table_name": u'PropertyState',
                "to_field": u'error_type',
            }, {
                "from_field": u'building_count',
                "to_table_name": u'PropertyState',
                "to_field": u'building_count',
            }, {
                "from_field": u'conditioned_floor_area',
                "to_table_name": u'PropertyState',
                "to_field": u'conditioned_floor_area',
            }, {
                "from_field": u'energy_score',
                "to_table_name": u'PropertyState',
                "to_field": u'energy_score',
            }, {
                "from_field": u'gross_floor_area',
                "to_table_name": u'PropertyState',
                "to_field": u'gross_floor_area',
            }, {
                "from_field": u'lot_number',
                "to_table_name": u'PropertyState',
                "to_field": u'lot_number',
            }, {
                "from_field": u'occupied_floor_area',
                "to_table_name": u'PropertyState',
                "to_field": u'occupied_floor_area',
            }, {
                "from_field": u'conditioned_floor_area',
                "to_table_name": u'PropertyState',
                "to_field": u'conditioned_floor_area',
            }, {
                "from_field": u'postal_code',
                "to_table_name": u'PropertyState',
                "to_field": u'postal_code',
            }, {
                "from_field": u'site_eui',
                "to_table_name": u'PropertyState',
                "to_field": u'site_eui',
            }, {
                "from_field": u'site_eui_weather_normalized',
                "to_table_name": u'PropertyState',
                "to_field": u'site_eui_weather_normalized',
            }, {
                "from_field": u'source_eui',
                "to_table_name": u'PropertyState',
                "to_field": u'source_eui',
            }, {
                "from_field": u'source_eui_weather_normalized',
                "to_table_name": u'PropertyState',
                "to_field": u'source_eui_weather_normalized',
            }, {
                "from_field": u'address_line_1',
                "to_table_name": u'PropertyState',
                "to_field": u'address_line_1',
            }, {
                "from_field": u'address_line_2',
                "to_table_name": u'PropertyState',
                "to_field": u'address_line_2',
            }, {
                "from_field": u'building_certification',
                "to_table_name": u'PropertyState',
                "to_field": u'building_certification',
            }, {
                "from_field": u'city',
                "to_table_name": u'PropertyState',
                "to_field": u'city',
            }, {
                "from_field": u'custom_id_1',
                "to_table_name": u'PropertyState',
                "to_field": u'custom_id_1',
            }, {
                "from_field": u'district',
                "to_table_name": u'PropertyState',
                "to_field": u'district',
            }, {
                "from_field": u'energy_alerts',
                "to_table_name": u'PropertyState',
                "to_field": u'energy_alerts',
            }, {
                "from_field": u'owner_address',
                "to_table_name": u'PropertyState',
                "to_field": u'owner_address',
            }, {
                "from_field": u'owner_city_state',
                "to_table_name": u'PropertyState',
                "to_field": u'owner_city_state',
            }, {
                "from_field": u'owner_email',
                "to_table_name": u'PropertyState',
                "to_field": u'owner_email',
            }, {
                "from_field": u'owner_postal_code',
                "to_table_name": u'PropertyState',
                "to_field": u'owner_postal_code',
            }, {
                "from_field": u'owner_telephone',
                "to_table_name": u'PropertyState',
                "to_field": u'owner_telephone',
            }, {
                "from_field": u'pm_property_id',
                "to_table_name": u'PropertyState',
                "to_field": u'pm_property_id',
            }, {
                "from_field": u'property_name',
                "to_table_name": u'PropertyState',
                "to_field": u'property_name',
            }, {
                "from_field": u'property_notes',
                "to_table_name": u'PropertyState',
                "to_field": u'property_notes',
            }, {
                "from_field": u'space_alerts',
                "to_table_name": u'PropertyState',
                "to_field": u'space_alerts',
            }, {
                "from_field": u'state_province',
                "to_table_name": u'PropertyState',
                "to_field": u'state_province',
            }, {
                "from_field": u'tax_lot_id',
                "to_table_name": u'PropertyState',
                "to_field": u'tax_lot_id',
            }, {
                "from_field": u'use_description',
                "to_table_name": u'PropertyState',
                "to_field": u'use_description',
            }, {
                "from_field": u'generation_date',
                "to_table_name": u'PropertyState',
                "to_field": u'generation_date',
            }, {
                "from_field": u'recent_sale_date',
                "to_table_name": u'PropertyState',
                "to_field": u'recent_sale_date',
            }, {
                "from_field": u'generation_date',
                "to_table_name": u'PropertyState',
                "to_field": u'generation_date',
            }, {
                "from_field": u'release_date',
                "to_table_name": u'PropertyState',
                "to_field": u'release_date',
            }, {
                "from_field": u'year_built',
                "to_table_name": u'PropertyState',
                "to_field": u'year_built',
            }, {
                "from_field": u'year_ending',
                "to_table_name": u'PropertyState',
                "to_field": u'year_ending',
            }, {
                "from_field": u'extra_data_ps_alpha',
                "to_table_name": u'PropertyState',
                "to_field": u'extra_data_ps_alpha'
            }, {
                "from_field": u'extra_data_ps_float',
                "to_table_name": u'PropertyState',
                "to_field": u'extra_data_ps_float'
            }
        ]

        tasks.save_raw_data(self.import_file.id)

        Column.create_mappings(fake_mappings, self.org, self.user)
        tasks.map_data(self.import_file.id)

        qs = PropertyState.objects.filter(
            import_file=self.import_file,
            source_type=ASSESSED_BS,
        ).iterator()

        # data quality check
        d = DataQualityCheck.retrieve(self.org)

        # create some status labels for testing
        sl_data = {'name': 'year - old or future', 'super_organization': self.org}
        status_label, _ = StatusLabel.objects.get_or_create(**sl_data)
        rule = d.rules.filter(field='year_built').first()
        rule.status_label = status_label
        rule.save()

        sl_data = {'name': 'extra data pa float error', 'super_organization': self.org}
        status_label, _ = StatusLabel.objects.get_or_create(**sl_data)
        new_rule = {
            'table_name': 'PropertyState',
            'field': 'extra_data_ps_float',
            'data_type': TYPE_NUMBER,
            'rule_type': RULE_TYPE_CUSTOM,
            'min': 9999,
            'max': 10001,
            'severity': SEVERITY_ERROR,
            'units': 'square feet',
            'status_label': status_label
        }
        d.add_rule(new_rule)

        d.check_data('PropertyState', qs)

        result = d.retrieve_result_by_address('4 Myrtle Parkway')
        res = [
            {
                "severity": "error",
                "value": "27.0",
                "field": "extra_data_ps_float",
                "table_name": "PropertyState",
                "message": "Extra Data Ps Float out of range",
                "detailed_message": "Extra Data Ps Float [27.0] < 9999.0",
                "formatted_field": "Extra Data Ps Float"
            }, {
                "severity": "error",
                "value": "5.0",
                "field": "gross_floor_area",
                "table_name": "PropertyState",
                "message": "Gross Floor Area out of range",
                "detailed_message": "Gross Floor Area [5.0] < 100.0",
                "formatted_field": "Gross Floor Area"
            }
        ]
        self.assertListEqual(result['data_quality_results'], res)

        result = d.retrieve_result_by_address('94 Oxford Hill')
        res = [
            {
                "severity": "error",
                "value": "20000.0",
                "field": "extra_data_ps_float",
                "table_name": "PropertyState",
                "message": "Extra Data Ps Float out of range",
                "detailed_message": "Extra Data Ps Float [20000.0] > 10001.0",
                "formatted_field": "Extra Data Ps Float"
            },
            {
                "severity": "error",
                "value": "1888-01-01 08:00:00",
                "field": "recent_sale_date",
                "table_name": "PropertyState",
                "message": "Recent Sale Date out of range",
                "detailed_message": "Recent Sale Date [1888-01-01 08:00:00] < 1889-01-01 00:00:00",
                "formatted_field": "Recent Sale Date"
            }
        ]
        self.assertListEqual(result['data_quality_results'], res)

        # import json
        # from seed.utils.generic import json_serializer
        # print json.dumps(result, default=json_serializer, indent=2)

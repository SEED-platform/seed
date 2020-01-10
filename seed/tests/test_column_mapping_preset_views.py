# !/usr/bin/env python
# encoding: utf-8

from django.urls import reverse

from json import loads, dumps

from seed.tests.util import DataMappingBaseTestCase
from seed.models import (
    ASSESSED_RAW,
    Column,
    ColumnMappingPreset,
)


class ColumnMappingPresetViewsCore(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, _import_file, _import_record, _cycle = selfvars

        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.client.login(**user_details)

    def test_list_preset_endpoint(self):
        preset_info = {
            "name": 'test_preset_1',
            "mappings": [
                {"from_field": "Property Id", "from_units": None, "to_field": "PM Property ID", "to_table_name": "PropertyState"},
                {"from_field": "Property Name", "from_units": None, "to_field": "Property Name", "to_table_name": "PropertyState"},
            ],
        }

        self.org.columnmappingpreset_set.create(**preset_info)

        url = reverse('api:v2:column_mapping_presets-list') + '?organization_id=' + str(self.org.id)

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        data = loads(response.content)['data']
        names = [d['name'] for d in data]

        self.assertCountEqual(['Portfolio Manager Defaults', 'test_preset_1'], names)

    def test_update_preset_endpoint(self):
        preset_info = {
            "name": 'test_preset_1',
            "mappings": [
                {"from_field": "Property Id", "from_units": None, "to_field": "PM Property ID", "to_table_name": "PropertyState"},
                {"from_field": "Property Name", "from_units": None, "to_field": "Property Name", "to_table_name": "PropertyState"},
            ],
        }

        preset = self.org.columnmappingpreset_set.create(**preset_info)

        url = reverse('api:v2:column_mapping_presets-detail', args=[preset.id]) + '?organization_id=' + str(self.org.id)
        post_params = dumps({
            "name": 'changed_preset_name',
            "mappings": [
                {"from_field": "Property Name", "from_units": None, "to_field": "Property Name", "to_table_name": "PropertyState"},
            ],
        })

        response = self.client.put(url, post_params, content_type='application/json')
        self.assertEqual(200, response.status_code)

        datum = loads(response.content)['data']

        self.assertEqual('changed_preset_name', datum['name'])
        self.assertEqual(1, ColumnMappingPreset.objects.filter(name='changed_preset_name').count())

        # Spot check error case
        url = reverse('api:v2:column_mapping_presets-detail', args=[preset.id]) + '?organization_id=' + str(self.org.id)
        post_params = dumps({
            "some_wrong_field_name": 'changed_preset_name',
        })

        response = self.client.put(url, post_params, content_type='application/json')
        self.assertEqual(400, response.status_code)

    def test_create_preset_endpoint(self):
        url = reverse('api:v2:column_mapping_presets-list') + '?organization_id=' + str(self.org.id)

        preset_info = dumps({
            "name": 'test_preset_1',
            "mappings": [
                {"from_field": "Property Id", "from_units": None, "to_field": "PM Property ID", "to_table_name": "PropertyState"},
                {"from_field": "Property Name", "from_units": None, "to_field": "Property Name", "to_table_name": "PropertyState"},
            ],
        })

        response = self.client.post(url, preset_info, content_type='application/json')
        self.assertEqual(200, response.status_code)

        datum = loads(response.content)['data']

        self.assertEqual('test_preset_1', datum['name'])
        self.assertEqual(1, ColumnMappingPreset.objects.filter(name='test_preset_1').count())

    def test_delete_preset_endpoint(self):
        preset = self.org.columnmappingpreset_set.get()

        url = reverse('api:v2:column_mapping_presets-detail', args=[preset.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.delete(url)

        self.assertEqual(200, response.status_code)
        self.assertFalse(ColumnMappingPreset.objects.exists())


class ColumnMappingPresetViewsNonCrud(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, _import_file, _import_record, _cycle = selfvars

        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.client.login(**user_details)

    def test_get_suggestion_given_raw_column_headers(self):
        # Create ED col to test
        Column.objects.create(
            column_name='extra_data_test',
            table_name='PropertyState',
            organization=self.org,
            is_extra_data=True
        )

        # Create a list of similarly named cols
        mock_incoming_headers = dumps({
            'headers': [
                'Jurisdiction Tax Lot ID',
                'PM Property ID',
                'Zip',
                'Extra Data',
            ],
        })

        # hit new endpoint with this list
        url = reverse('api:v2:column_mapping_presets-suggestions') + '?organization_id=' + str(self.org.id)

        response = self.client.post(url, mock_incoming_headers, content_type='application/json')
        results = loads(response.content)['data']

        expected = {
            'Extra Data': ['PropertyState', 'extra_data_test', 94],
            'Jurisdiction Tax Lot ID': ['TaxLotState', 'jurisdiction_tax_lot_id', 100],
            'PM Property ID': ['PropertyState', 'pm_property_id', 100],
            'Zip': ['PropertyState', 'postal_code', 100]
        }

        for header in results:
            self.assertEqual(expected[header], results[header])

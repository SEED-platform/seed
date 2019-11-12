# !/usr/bin/env python
# encoding: utf-8

from django.core.urlresolvers import reverse

from json import loads, dumps

from seed.tests.util import DataMappingBaseTestCase
from seed.models import (
    ASSESSED_RAW,
    ColumnMappingPreset,
)


class ColumnMappingPresetViews(DataMappingBaseTestCase):
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

        datum = loads(response.content)['data'][0]
        self.assertEqual('test_preset_1', datum['name'])

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
        self.assertEqual('changed_preset_name', ColumnMappingPreset.objects.get().name)

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
        self.assertEqual('test_preset_1', ColumnMappingPreset.objects.get().name)

    def test_delete_preset_endpoint(self):
        preset_info = {
            "name": 'test_preset_1',
            "mappings": [
                {"from_field": "Property Id", "from_units": None, "to_field": "PM Property ID", "to_table_name": "PropertyState"},
                {"from_field": "Property Name", "from_units": None, "to_field": "Property Name", "to_table_name": "PropertyState"},
            ],
        }

        preset = self.org.columnmappingpreset_set.create(**preset_info)

        url = reverse('api:v2:column_mapping_presets-detail', args=[preset.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.delete(url)

        self.assertEqual(200, response.status_code)
        self.assertFalse(ColumnMappingPreset.objects.exists())

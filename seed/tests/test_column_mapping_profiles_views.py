# !/usr/bin/env python
# encoding: utf-8

from django.urls import reverse

from json import loads, dumps

from seed.tests.util import DataMappingBaseTestCase
from seed.models import (
    ASSESSED_RAW,
    Column,
    ColumnMappingProfile,
)
from seed.lib.xml_mapping.mapper import default_buildingsync_profile_mappings


class ColumnMappingProfileViewsCore(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, _import_file, _import_record, _cycle = selfvars

        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.client.login(**user_details)

    def test_filter_profile_endpoint(self):
        profile_info = {
            "name": 'test_profile_1',
            "mappings": [
                {"from_field": "Property Id", "from_units": None, "to_field": "PM Property ID", "to_table_name": "PropertyState"},
                {"from_field": "Property Name", "from_units": None, "to_field": "Property Name", "to_table_name": "PropertyState"},
            ],
        }

        self.org.columnmappingprofile_set.create(**profile_info)

        url = reverse('api:v3:column_mapping_profiles-filter') + '?organization_id=' + str(self.org.id)

        response = self.client.post(url)
        self.assertEqual(200, response.status_code)

        data = loads(response.content)['data']
        names = [d['name'] for d in data]

        self.assertCountEqual(['Portfolio Manager Defaults', 'BuildingSync v2.0 Defaults', 'test_profile_1'], names)

    def test_filter_profile_endpoint_by_type(self):
        profile_info = {
            "name": 'test_profile_1',
            "mappings": [
                {"from_field": "Property Id", "from_units": None, "to_field": "PM Property ID", "to_table_name": "PropertyState"},
                {"from_field": "Property Name", "from_units": None, "to_field": "Property Name", "to_table_name": "PropertyState"},
            ],
            "profile_type": ColumnMappingProfile.NORMAL
        }
        args = {"profile_type": ['Normal']}
        self.org.columnmappingprofile_set.create(**profile_info)

        url = reverse('api:v3:column_mapping_profiles-filter') + '?organization_id=' + str(self.org.id)

        response = self.client.post(url, args, content_type='application/json')
        self.assertEqual(200, response.status_code, response.content)

        data = loads(response.content)['data']
        names = [d['name'] for d in data]

        self.assertCountEqual(['Portfolio Manager Defaults', 'test_profile_1'], names)

    def test_filter_profile_endpoint_by_multiple_types(self):
        profile_info = {
            "name": 'test_profile_1',
            "mappings": [
                {"from_field": "Property Id", "from_units": None, "to_field": "PM Property ID", "to_table_name": "PropertyState"},
                {"from_field": "Property Name", "from_units": None, "to_field": "Property Name", "to_table_name": "PropertyState"},
            ],
            "profile_type": ColumnMappingProfile.BUILDINGSYNC_CUSTOM
        }
        args = {"profile_type": ['BuildingSync Default', 'BuildingSync Custom']}
        self.org.columnmappingprofile_set.create(**profile_info)

        url = (reverse('api:v3:column_mapping_profiles-filter') + '?organization_id=' + str(self.org.id))

        response = self.client.post(url, args, content_type='application/json')
        self.assertEqual(200, response.status_code, response.content)

        data = loads(response.content)['data']
        names = [d['name'] for d in data]

        self.assertCountEqual(['BuildingSync v2.0 Defaults', 'test_profile_1'], names)

    def test_update_profile_endpoint(self):
        profile_info = {
            "name": 'test_profile_1',
            "mappings": [
                {"from_field": "Property Id", "from_units": None, "to_field": "PM Property ID", "to_table_name": "PropertyState"},
                {"from_field": "Property Name", "from_units": None, "to_field": "Property Name", "to_table_name": "PropertyState"},
            ],
        }

        profile = self.org.columnmappingprofile_set.create(**profile_info)

        url = reverse('api:v3:column_mapping_profiles-detail', args=[profile.id]) + '?organization_id=' + str(self.org.id)
        post_params = dumps({
            "name": 'changed_profile_name',
            "mappings": [
                {"from_field": "Property Name", "from_units": None, "to_field": "Property Name", "to_table_name": "PropertyState"},
            ],
        })

        response = self.client.put(url, post_params, content_type='application/json')
        self.assertEqual(200, response.status_code)

        datum = loads(response.content)['data']

        self.assertEqual('changed_profile_name', datum['name'])
        self.assertEqual(1, ColumnMappingProfile.objects.filter(name='changed_profile_name').count())

    def test_create_profile_endpoint(self):
        url = reverse('api:v3:column_mapping_profiles-list') + '?organization_id=' + str(self.org.id)

        profile_info = dumps({
            "name": 'test_profile_1',
            "mappings": [
                {"from_field": "Property Id", "from_units": None, "to_field": "PM Property ID", "to_table_name": "PropertyState"},
                {"from_field": "Property Name", "from_units": None, "to_field": "Property Name", "to_table_name": "PropertyState"},
            ],
        })

        response = self.client.post(url, profile_info, content_type='application/json')
        self.assertEqual(200, response.status_code)

        datum = loads(response.content)['data']

        self.assertEqual('test_profile_1', datum['name'])
        self.assertEqual(1, ColumnMappingProfile.objects.filter(name='test_profile_1').count())

    def test_delete_profile_endpoint(self):
        profile = self.org.columnmappingprofile_set.get(profile_type=ColumnMappingProfile.NORMAL)

        url = reverse('api:v3:column_mapping_profiles-detail', args=[profile.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.delete(url)

        self.assertEqual(200, response.status_code)
        self.assertFalse(ColumnMappingProfile.objects.filter(profile_type=ColumnMappingProfile.NORMAL).exists())


class ColumnMappingProfilesViewsNonCrud(DataMappingBaseTestCase):
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
        url = reverse('api:v3:column_mapping_profiles-suggestions') + '?organization_id=' + str(self.org.id)

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


class ColumnMappingProfilesViewsBuildingSync(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, _import_file, _import_record, _cycle = selfvars

        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.client.login(**user_details)

    def test_update_default_bsync_profile_fails(self):
        profile = self.org.columnmappingprofile_set.get(profile_type=ColumnMappingProfile.BUILDINGSYNC_DEFAULT)

        url = reverse('api:v3:column_mapping_profiles-detail', args=[profile.id]) + '?organization_id=' + str(self.org.id)
        update_vals = {
            "name": 'changed_profile_name',
            "mappings": [
                {"from_field": "Updated Property Name", "from_units": None, "to_field": "Property Name", "to_table_name": "PropertyState"},
            ],
        }

        response = self.client.put(url, dumps(update_vals), content_type='application/json')
        self.assertEqual(400, response.status_code)

        profile_after = self.org.columnmappingprofile_set.get(profile_type=ColumnMappingProfile.BUILDINGSYNC_DEFAULT)
        self.assertNotEqual(profile.name, update_vals['name'])
        updated_mapping = [m for m in profile_after.mappings if m['from_field'] == 'Updated Property Name']
        self.assertEqual([], updated_mapping)

    def test_delete_default_bsync_profile_fails(self):
        profile = self.org.columnmappingprofile_set.get(profile_type=ColumnMappingProfile.BUILDINGSYNC_DEFAULT)

        url = reverse('api:v3:column_mapping_profiles-detail', args=[profile.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.delete(url)

        self.assertEqual(400, response.status_code)
        self.assertTrue(ColumnMappingProfile.objects.filter(id=profile.id).exists())

    def test_delete_custom_bsync_profile_succeeds(self):
        profile = self.org.columnmappingprofile_set.create(
            name='Custom BSync Profile',
            mappings=[],
            profile_type=ColumnMappingProfile.BUILDINGSYNC_CUSTOM
        )

        url = reverse('api:v3:column_mapping_profiles-detail', args=[profile.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.delete(url)

        self.assertEqual(200, response.status_code)
        self.assertFalse(ColumnMappingProfile.objects.filter(id=profile.id).exists())

    def test_update_custom_bsync_profile_successfully_changes_to_fields(self):
        # -- Setup
        # create the custom profile
        profile_mappings = default_buildingsync_profile_mappings()
        profile_name = 'Custom BSync Profile'
        profile = self.org.columnmappingprofile_set.create(
            name=profile_name,
            mappings=profile_mappings,
            profile_type=ColumnMappingProfile.BUILDINGSYNC_CUSTOM)

        # -- Act
        # change one of the mapping's to_field
        url = reverse('api:v3:column_mapping_profiles-detail', args=[profile.id]) + '?organization_id=' + str(self.org.id)
        updated_mappings = [mapping.copy() for mapping in profile_mappings]
        updated_mappings[0]['to_field'] = 'my_new_to_field'
        update_vals = {
            'name': 'New Profile Name',
            'mappings': updated_mappings,
        }

        response = self.client.put(url, dumps(update_vals), content_type='application/json')

        # -- Assert
        self.assertEqual(200, response.status_code)

        # get the updated profile using the updated name
        updated_profile = self.org.columnmappingprofile_set.filter(name='New Profile Name')
        self.assertTrue(updated_profile.exists())
        updated_profile = updated_profile[0]
        # look for the mapping that was changed
        changed_mapping = [m for m in updated_profile.mappings if m['to_field'] == 'my_new_to_field']
        self.assertNotEqual([], changed_mapping)

    def test_update_custom_bsync_profile_successfully_removes_mappings(self):
        # -- Setup
        # create the custom profile
        profile_mappings = default_buildingsync_profile_mappings()
        profile_name = 'Custom BSync Profile'
        profile = self.org.columnmappingprofile_set.create(
            name=profile_name,
            mappings=profile_mappings,
            profile_type=ColumnMappingProfile.BUILDINGSYNC_CUSTOM)

        # -- Act
        # remove one of the mappings and update it
        url = reverse('api:v3:column_mapping_profiles-detail', args=[profile.id]) + '?organization_id=' + str(self.org.id)
        updated_mappings = [mapping.copy() for mapping in profile_mappings]
        removed_mapping = updated_mappings.pop()
        update_vals = {
            'name': 'New Profile Name',
            'mappings': updated_mappings,
        }

        response = self.client.put(url, dumps(update_vals), content_type='application/json')

        # -- Assert
        self.assertEqual(200, response.status_code)

        # get the updated profile using the updated name
        updated_profile = self.org.columnmappingprofile_set.filter(name='New Profile Name')
        self.assertTrue(updated_profile.exists())
        updated_profile = updated_profile[0]
        # look for the mapping that was supposed to be removed (should not be found)
        filtered_mappings = [m for m in updated_profile.mappings if m['from_field'] == removed_mapping['from_field']]
        self.assertFalse(filtered_mappings)

    def test_update_custom_bsync_profile_does_NOT_change_from_fields(self):
        # -- Setup
        # create the custom profile
        profile_mappings = default_buildingsync_profile_mappings()
        profile_name = 'Custom BSync Profile'
        profile = self.org.columnmappingprofile_set.create(
            name=profile_name,
            mappings=profile_mappings,
            profile_type=ColumnMappingProfile.BUILDINGSYNC_CUSTOM)

        # -- Act
        # change one of the mappings in an acceptable way
        url = reverse('api:v3:column_mapping_profiles-detail', args=[profile.id]) + '?organization_id=' + str(self.org.id)
        updated_mappings = [mapping.copy() for mapping in profile_mappings]
        updated_mappings[0]['from_field'] = 'my_new_from_field'
        update_vals = {
            'name': 'New Profile Name',
            'mappings': updated_mappings,
        }

        response = self.client.put(url, dumps(update_vals), content_type='application/json')

        # -- Assert
        self.assertEqual(200, response.status_code)

        updated_profile = self.org.columnmappingprofile_set.filter(name='New Profile Name')
        self.assertTrue(updated_profile.exists())
        updated_profile = updated_profile[0]
        # try to find a mapping with the new from_field (it should not exist)
        changed_mapping = [m for m in updated_profile.mappings if m['from_field'] == 'my_new_from_field']
        self.assertFalse(changed_mapping)

    def test_create_custom_bsync_profile_succeeds(self):
        url = reverse('api:v3:column_mapping_profiles-list') + '?organization_id=' + str(self.org.id)

        profile_info = dumps({
            "name": 'BSync Profile',
            "mappings": [
                {
                    "from_field": "Property Id",
                    "from_field_value": "text",
                    "from_units": None,
                    "to_field": "PM Property ID",
                    "to_table_name": "PropertyState"
                }, {
                    "from_field": "Property Name",
                    "from_field_value": "@ID",
                    "from_units": None,
                    "to_field": "Property Name",
                    "to_table_name": "PropertyState"
                }
            ],
            "profile_type": "BuildingSync Custom"
        })

        response = self.client.post(url, profile_info, content_type='application/json')
        self.assertEqual(200, response.status_code, response.content)

        datum = loads(response.content)['data']

        self.assertEqual('BSync Profile', datum.get('name'))
        self.assertEqual(1, ColumnMappingProfile.objects.filter(name='BSync Profile', profile_type=ColumnMappingProfile.BUILDINGSYNC_CUSTOM).count())

    def test_create_custom_bsync_profile_fails_when_missing_from_field_value(self):
        url = reverse('api:v3:column_mapping_profiles-list') + '?organization_id=' + str(self.org.id)

        profile_info = dumps({
            "name": 'BSync Profile',
            "mappings": [
                {
                    "from_field": "Property Id",
                    # NOTE: no from_field_value
                    "from_units": None,
                    "to_field": "PM Property ID",
                    "to_table_name": "PropertyState"
                }, {
                    "from_field": "Property Name",
                    # NOTE: no from_field_value
                    "from_units": None,
                    "to_field": "Property Name",
                    "to_table_name": "PropertyState"
                }
            ],
            "profile_type": "BuildingSync Custom"
        })

        response = self.client.post(url, profile_info, content_type='application/json')
        self.assertEqual(400, response.status_code, response.content)

        self.assertFalse(ColumnMappingProfile.objects.filter(name='BSync Profile').exists())

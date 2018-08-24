# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import os.path

from django.core.exceptions import ValidationError
from django.test import TestCase

from seed import models as seed_models
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    PropertyState,
    Column,
    ColumnMapping,
)
from seed.utils.organizations import create_organization


class TestColumns(TestCase):
    """Test the clean methods on BuildingSnapshotModel."""

    def setUp(self):
        self.fake_user = User.objects.create(username='test')
        self.fake_org, _, _ = create_organization(self.fake_user)

    def test_get_column_mapping(self):
        """Honor organizational bounds, get mapping data."""

        # Calling organization create like this will not generate the default
        # columns, which is okay for this test.
        org1 = Organization.objects.create()
        org2 = Organization.objects.create()

        # Raw columns don't have a table name!
        raw_column = seed_models.Column.objects.create(
            column_name=u'Some Weird City ID',
            organization=org2
        )
        mapped_column = seed_models.Column.objects.create(
            table_name=u'PropertyState',
            column_name=u'custom_id_1',
            organization=org2
        )
        column_mapping1 = seed_models.ColumnMapping.objects.create(
            super_organization=org2,
        )
        column_mapping1.column_raw.add(raw_column)
        column_mapping1.column_mapped.add(mapped_column)

        # Test that it Doesn't give us a mapping from another org.
        self.assertEqual(
            seed_models.get_column_mapping(raw_column, org1, 'column_mapped'),
            None
        )

        # Correct org, but incorrect destination column.
        self.assertEqual(
            seed_models.get_column_mapping('random', org2, 'column_mapped'),
            None
        )

        # Fully correct example
        self.assertEqual(
            seed_models.get_column_mapping(raw_column.column_name, org2, 'column_mapped'),
            (u'PropertyState', u'custom_id_1', 100)
        )

    def test_get_column_mappings(self):
        """We produce appropriate data structure for mapping"""
        raw_data = [
            {
                "from_field": "raw_data_0",
                "to_field": "destination_0",
                "to_table_name": "PropertyState"
            }, {
                "from_field": "raw_data_1",
                "to_field": "destination_1",
                "to_table_name": "PropertyState"
            }, {
                "from_field": "raw_data_2",
                "to_field": "destination_0",
                "to_table_name": "TaxLotState"
            },
        ]

        Column.create_mappings(raw_data, self.fake_org, self.fake_user)

        expected = {
            u'raw_data_0': (u'PropertyState', u'destination_0', u'', True),
            u'raw_data_1': (u'PropertyState', u'destination_1', u'', True),
            u'raw_data_2': (u'TaxLotState', u'destination_0', u'', True),
        }

        test_mapping, no_concat = ColumnMapping.get_column_mappings(self.fake_org)
        self.assertDictEqual(test_mapping, expected)
        self.assertEqual(no_concat, [])

    def test_save_mappings_dict(self):
        """
        Test the way of saving mappings, which is dict-based instead of list of list of list.
        """

        test_map = [
            {
                'from_field': 'eui',
                'to_field': 'site_eui',
                'to_table_name': 'PropertyState',
            },
            {
                'from_field': 'address',
                'to_field': 'address',
                'to_table_name': 'TaxLotState'
            },
            {
                'from_field': 'Wookiee',
                'to_field': 'Dothraki',
                'to_table_name': 'PropertyState',
            },
            {
                'from_field': 'Ewok',
                'to_field': 'Merovingian',
                'to_table_name': 'TaxLotState',
            },
            {
                'from_field': 'Ewok',
                'to_field': 'Hattin',
                'to_table_name': 'TaxLotState',
            },
        ]

        seed_models.Column.create_mappings(test_map, self.fake_org, self.fake_user)
        test_mapping, _ = ColumnMapping.get_column_mappings(self.fake_org)
        expected = {
            u'Wookiee': (u'PropertyState', u'Dothraki', u'', True),
            u'address': (u'TaxLotState', u'address', u'', True),
            u'eui': (u'PropertyState', u'site_eui', u'Site EUI', False),
            # u'Ewok': (u'TaxLotState', u'Merovingian'), # this does not show up because it was set before the last one
            u'Ewok': (u'TaxLotState', u'Hattin', u'', True),
        }
        self.assertDictEqual(expected, test_mapping)
        self.assertTrue(test_mapping['Ewok'], 'Hattin')

        c_wookiee = Column.objects.filter(column_name='Wookiee')[0]
        # Since the raw column is wookiee, then it should NOT be extra data
        self.assertEqual(c_wookiee.is_extra_data, False)
        self.assertEqual(c_wookiee.table_name, '')
        c_merovingian = Column.objects.filter(column_name='Merovingian')[0]
        self.assertEqual(c_merovingian.is_extra_data, True)
        self.assertEqual(c_merovingian.table_name, 'TaxLotState')

        # Check the database for the mapped columns since create_mappings does not return anything!
        cm = ColumnMapping.objects.filter(super_organization=self.fake_org,
                                          column_raw__in=[c_wookiee]).first()

        column = cm.column_mapped.first()
        self.assertEqual(column.is_extra_data, True)
        self.assertEqual(column.table_name, "PropertyState")
        self.assertEqual(column.column_name, "Dothraki")

        # test by table name sorting
        test_mapping = ColumnMapping.get_column_mappings_by_table_name(self.fake_org)
        expected = {
            u'PropertyState': {
                u'Wookiee': (u'PropertyState', u'Dothraki', u'', True),
                u'eui': (u'PropertyState', u'site_eui', u'Site EUI', False),
            },
            u'TaxLotState': {
                u'address': (u'TaxLotState', u'address', u'', True),
                u'Ewok': (u'TaxLotState', u'Hattin', u'', True),
            }
        }
        self.assertDictEqual(test_mapping, expected)

    def test_save_columns(self):
        # create

        ps = PropertyState.objects.create(
            organization=self.fake_org,
            extra_data={'a': 123, 'lab': 'hawkins national laboratory'}
        )
        Column.save_column_names(ps)

        c = Column.objects.filter(column_name='lab')[0]

        self.assertEqual(c.is_extra_data, True)
        self.assertEqual(c.table_name, 'PropertyState')
        self.assertEqual(ps.extra_data['lab'], 'hawkins national laboratory')

    def test_save_column_mapping_by_file_exception(self):
        self.mapping_import_file = os.path.abspath("./no-file.csv")
        with self.assertRaisesRegexp(Exception, "Mapping file does not exist: .*/no-file.csv"):
            Column.create_mappings_from_file(self.mapping_import_file, self.fake_org,
                                             self.fake_user)

    def test_save_column_mapping_by_file(self):
        self.mapping_import_file = os.path.abspath("./seed/tests/data/test_mapping.csv")
        Column.create_mappings_from_file(self.mapping_import_file, self.fake_org, self.fake_user)

        expected = {
            u'City': (u'PropertyState', u'city'),
            u'Custom ID': (u'PropertyState', u'custom_id_1'),
            u'Zip': (u'PropertyState', u'postal_code'),
            u'GBA': (u'PropertyState', u'gross_floor_area'),
            u'PM Property ID': (u'PropertyState', u'pm_property_id'),
            u'BLDGS': (u'PropertyState', u'building_count'),
            u'AYB_YearBuilt': (u'PropertyState', u'year_build'),
            u'State': (u'PropertyState', u'state'),
            u'Address': (u'PropertyState', u'address_line_1'),
            u'Owner': (u'PropertyState', u'owner'),
            u'Raw Column': (u'Table Name', u'Field Name'),
            u'Property Type': (u'PropertyState', u'property_type'),
            u'UBI': (u'TaxLotState', u'jurisdiction_tax_lot_id')
        }

        test_mapping, _ = ColumnMapping.get_column_mappings(self.fake_org)
        self.assertItemsEqual(expected, test_mapping)


class TestColumnMapping(TestCase):
    """Test ColumnMapping utility methods."""

    def setUp(self):
        foo_col = seed_models.Column.objects.create(column_name="foo")
        bar_col = seed_models.Column.objects.create(column_name="bar")
        baz_col = seed_models.Column.objects.create(column_name="baz")

        dm = seed_models.ColumnMapping.objects.create()
        dm.column_raw.add(foo_col)
        dm.column_mapped.add(baz_col)

        cm = seed_models.ColumnMapping.objects.create()
        cm.column_raw.add(foo_col, bar_col)
        cm.column_mapped.add(baz_col)

        self.directMapping = dm
        self.concatenatedMapping = cm

    def test_is_direct(self):
        self.assertEqual(self.directMapping.is_direct(), True)
        self.assertEqual(self.concatenatedMapping.is_direct(), False)

    def test_is_concatenated(self):
        self.assertEqual(self.directMapping.is_concatenated(), False)
        self.assertEqual(self.concatenatedMapping.is_concatenated(), True)


class TestColumnsByInventory(TestCase):

    def setUp(self):
        self.fake_user = User.objects.create(username='test')
        self.fake_org, _org_user, _user_created = create_organization(
            self.fake_user, name='Existing Org'
        )
        column_a = seed_models.Column.objects.create(
            column_name=u'Column A',
            table_name=u'PropertyState',
            organization=self.fake_org,
            is_extra_data=True,
            shared_field_type=Column.SHARED_PUBLIC,
        )
        # field that is in the import, but not mapped to
        raw_column = seed_models.Column.objects.create(
            column_name=u'not mapped data',
            organization=self.fake_org,
        )
        dm = seed_models.ColumnMapping.objects.create()
        dm.column_raw.add(raw_column)
        dm.column_mapped.add(column_a)
        dm.save()
        seed_models.Column.objects.create(
            column_name=u"Apostrophe's Field",
            table_name=u'PropertyState',
            organization=self.fake_org,
            is_extra_data=True
        )
        seed_models.Column.objects.create(
            column_name=u'id',
            table_name=u'PropertyState',
            organization=self.fake_org,
            is_extra_data=True
        )
        seed_models.Column.objects.create(
            column_name=u'tax_lot_id_not_used',
            table_name=u'TaxLotState',
            organization=self.fake_org,
            is_extra_data=True
        )
        seed_models.Column.objects.create(
            column_name=u'Gross Floor Area',
            table_name=u'TaxLotState',
            organization=self.fake_org,
            is_extra_data=True
        )

    def test_is_extra_data_validation(self):
        # This is an invalid column. It is not a db field but is not marked as extra data
        with self.assertRaises(ValidationError):
            seed_models.Column.objects.create(
                column_name=u'not extra data',
                table_name=u'PropertyState',
                organization=self.fake_org,
                is_extra_data=False
            )

        # verify that creating columns from CSV's will not raise ValidationErrors
        column = seed_models.Column.objects.create(
            column_name=u'column from csv file',
            # table_name=u'PropertyState',
            organization=self.fake_org,
            # is_extra_data=False
        )
        column.delete()

        column = seed_models.Column.objects.create(
            column_name=u'column from csv file empty table',
            table_name='',
            organization=self.fake_org,
            # is_extra_data=False
        )
        column.delete()

        column = seed_models.Column.objects.create(
            column_name=u'column from csv file empty table false extra_data',
            table_name='',
            organization=self.fake_org,
            is_extra_data=False
        )
        column.delete()

    def test_column_name(self):
        # verify that the column name is in the form of <column_name>_<id>.
        # Note that most of the tests remove the name and id field from the column listings to make it easier,
        # so this test is really important!
        columns = Column.retrieve_all(self.fake_org.pk, 'property', False)
        for c in columns:
            if c['column_name'] == 'PropertyState':
                self.assertEqual(c['name'], "%s_%s" % (c['column_name'], c['id']))

    def test_column_retrieve_all(self):
        columns = Column.retrieve_all(self.fake_org.pk, 'property', False)
        # go through and delete all the results.ids so that it is easy to do a compare
        for result in columns:
            del result['id']
            del result['name']

        # Check for columns
        c = {
            'table_name': u'PropertyState',
            'column_name': u'Column A',
            'display_name': u'Column A',
            'is_extra_data': True,
            'merge_protection': 0,
            'data_type': 'None',
            'related': False,
            'sharedFieldType': 'Public',
        }
        self.assertIn(c, columns)

        # Check that display_name doesn't capitalize after apostrophe
        c = {
            'table_name': u'PropertyState',
            'column_name': u"Apostrophe's Field",
            'display_name': u"Apostrophe's Field",
            'is_extra_data': True,
            'merge_protection': 0,
            'data_type': 'None',
            'related': False,
            'sharedFieldType': 'None',
        }
        self.assertIn(c, columns)

        # Check 'id' field if extra_data
        c = {
            'table_name': 'PropertyState',
            'column_name': 'id',
            'display_name': 'id',
            'is_extra_data': True,
            'merge_protection': 0,
            'data_type': 'None',
            'related': False,
            'sharedFieldType': 'None',
        }
        self.assertIn(c, columns)

        # check the 'pinIfNative' argument
        c = {
            'table_name': 'PropertyState',
            'column_name': 'pm_property_id',
            'display_name': 'PM Property ID',
            'is_extra_data': False,
            'merge_protection': 0,
            'data_type': 'string',
            'pinnedLeft': True,
            'related': False,
            'sharedFieldType': 'None',
        }
        self.assertIn(c, columns)

        # verity that the 'duplicateNameInOtherTable' is working
        c = {
            'table_name': 'TaxLotState',
            'column_name': 'state',
            'display_name': 'State (Tax Lot)',
            'data_type': 'string',
            'is_extra_data': False,
            'merge_protection': 0,
            'sharedFieldType': 'None',
            'related': True,
        }
        self.assertIn(c, columns)

        c = {
            'table_name': 'TaxLotState',
            'column_name': 'Gross Floor Area',
            'display_name': 'Gross Floor Area (Tax Lot)',
            'data_type': 'None',
            'is_extra_data': True,
            'merge_protection': 0,
            'sharedFieldType': 'None',
            'related': True,
        }
        self.assertIn(c, columns)

        # TODO: 4/25/2018 Need to decide how to check for bad columns and not return them in the request
        self.assertNotIn('not mapped data', [d['column_name'] for d in columns])

    def test_columns_extra_tag(self):
        columns = Column.retrieve_all(self.fake_org.pk, 'taxlot', False)
        # go through and delete all the results.ids so that it is easy to do a compare
        for result in columns:
            del result['id']
            del result['name']

        c = {
            'table_name': 'TaxLotState',
            'column_name': 'Gross Floor Area',
            'display_name': 'Gross Floor Area',
            'data_type': 'None',
            'is_extra_data': True,
            'merge_protection': 0,
            'sharedFieldType': 'None',
            'related': False,
        }
        self.assertIn(c, columns)

    def test_column_retrieve_only_used(self):
        columns = Column.retrieve_all(self.fake_org.pk, 'property', True)
        self.assertEqual(len(columns), 1)
        for c in columns:
            if c['name'] == 'Column A':
                self.assertEqual(c['sharedFieldType'], 'Public')

    def test_column_retrieve_all_duplicate_error(self):
        seed_models.Column.objects.create(
            column_name=u'custom_id_1',
            table_name=u'PropertyState',
            organization=self.fake_org,
            is_extra_data=True
        )

        with self.assertRaisesRegexp(Exception, 'Duplicate name'):
            Column.retrieve_all(self.fake_org.pk, 'property', False)

    def test_column_retrieve_schema(self):
        schema = {
            "types": {
                "address_line_1": "string",
                "address_line_2": "string",
                "analysis_end_time": "datetime",
                "analysis_start_time": "datetime",
                "analysis_state": "string",
                "analysis_state_message": "string",
                "block_number": "string",
                "building_certification": "string",
                "building_count": "integer",
                "campus": "boolean",
                "city": "string",
                "conditioned_floor_area": "float",
                "created": "datetime",
                "custom_id_1": "string",
                "district": "string",
                "energy_alerts": "string",
                "energy_score": "integer",
                "generation_date": "datetime",
                "gross_floor_area": "float",
                "home_energy_score_id": "string",
                "jurisdiction_property_id": "string",
                "jurisdiction_tax_lot_id": "string",
                "latitude": "float",
                "longitude": "float",
                "lot_number": "string",
                "normalized_address": "string",
                "number_properties": "integer",
                "occupied_floor_area": "float",
                "owner": "string",
                "owner_address": "string",
                "owner_city_state": "string",
                "owner_email": "string",
                "owner_postal_code": "string",
                "owner_telephone": "string",
                "pm_parent_property_id": "string",
                "pm_property_id": "string",
                "postal_code": "string",
                "property_name": "string",
                "property_notes": "string",
                "property_type": "string",
                "recent_sale_date": "datetime",
                "release_date": "datetime",
                "site_eui": "float",
                "site_eui_modeled": "float",
                "site_eui_weather_normalized": "float",
                "source_eui": "float",
                "source_eui_modeled": "float",
                "source_eui_weather_normalized": "float",
                "space_alerts": "string",
                "state": "string",
                "ubid": "string",
                "updated": "datetime",
                "use_description": "string",
                "year_ending": "date",
                "year_built": "integer",
            }
        }

        columns = Column.retrieve_db_types()
        self.assertDictEqual(schema, columns)

    def test_column_retrieve_db_fields(self):
        c = Column.retrieve_db_fields(self.fake_org.pk)

        data = ['address_line_1', 'address_line_2', 'analysis_end_time', 'analysis_start_time',
                'analysis_state', 'analysis_state_message', 'block_number',
                'building_certification', 'building_count', 'campus', 'city',
                'conditioned_floor_area', 'created', 'custom_id_1', 'district', 'energy_alerts',
                'energy_score', 'generation_date', 'gross_floor_area', 'home_energy_score_id',
                'jurisdiction_property_id', 'jurisdiction_tax_lot_id', 'latitude', 'longitude',
                'lot_number', 'normalized_address', 'number_properties', 'occupied_floor_area',
                'owner', 'owner_address', 'owner_city_state', 'owner_email', 'owner_postal_code',
                'owner_telephone', 'pm_parent_property_id', 'pm_property_id', 'postal_code',
                'property_name', 'property_notes', 'property_type', 'recent_sale_date',
                'release_date', 'site_eui', 'site_eui_modeled', 'site_eui_weather_normalized',
                'source_eui', 'source_eui_modeled', 'source_eui_weather_normalized', 'space_alerts',
                'state', 'ubid', 'updated', 'use_description', 'year_built', 'year_ending']

        self.assertItemsEqual(c, data)

    def test_retrieve_db_field_name_from_db_tables(self):
        """These values are the fields that can be used for hashing a property to check if it is the same record."""
        expected = ['address_line_1', 'address_line_2', 'analysis_end_time', 'analysis_start_time',
                    'analysis_state_message', 'block_number', 'building_certification',
                    'building_count', 'campus', 'city', 'conditioned_floor_area', 'created',
                    'custom_id_1', 'district', 'energy_alerts', 'energy_score', 'generation_date',
                    'gross_floor_area', 'home_energy_score_id', 'jurisdiction_property_id',
                    'jurisdiction_tax_lot_id', 'latitude', 'longitude', 'lot_number',
                    'number_properties', 'occupied_floor_area', 'owner', 'owner_address',
                    'owner_city_state', 'owner_email', 'owner_postal_code', 'owner_telephone',
                    'pm_parent_property_id', 'pm_property_id', 'postal_code', 'property_name',
                    'property_notes', 'property_type', 'recent_sale_date', 'release_date',
                    'site_eui', 'site_eui_modeled', 'site_eui_weather_normalized', 'source_eui',
                    'source_eui_modeled', 'source_eui_weather_normalized', 'space_alerts', 'state',
                    'ubid', 'updated', 'use_description', 'year_built', 'year_ending']

        method_columns = Column.retrieve_db_field_name_for_hash_comparison()
        self.assertListEqual(method_columns, expected)

    def test_retrieve_db_field_table_and_names_from_db_tables(self):
        names = Column.retrieve_db_field_table_and_names_from_db_tables()
        self.assertIn(('Property', 'campus'), names)
        self.assertIn(('PropertyState', 'gross_floor_area'), names)
        self.assertIn(('TaxLotState', 'address_line_1'), names)
        self.assertNotIn(('PropertyState', 'gross_floor_area_orig'), names)

    def test_retrieve_all_as_tuple(self):
        list_result = Column.retrieve_all_by_tuple(self.fake_org)
        self.assertIn((u'PropertyState', u'site_eui_modeled'), list_result)
        self.assertIn((u'TaxLotState', u'tax_lot_id_not_used'), list_result)
        self.assertIn((u'PropertyState', u'gross_floor_area'),
                      list_result)  # extra field in taxlot, but not in property
        self.assertIn((u'TaxLotState', u'Gross Floor Area'),
                      list_result)  # extra field in taxlot, but not in property

    def test_db_columns_in_default_columns(self):
        """
        This test ensures that all the columns in the database are defined in the Column.DEFAULT_COLUMNS

        If a user add a new database column then this test will fail until the column is defined in
        Column.DEFAULT_COLUMNS
        """

        all_columns = Column.retrieve_db_fields_from_db_tables()
        # print json.dumps(all_columns, indent=2)

        # {
        #     "table_name": "PropertyState",
        #     "data_type": "CharField",
        #     "column_name": "jurisdiction_property_id"
        # }
        #
        errors = []
        for column in all_columns:
            found = False
            for def_column in Column.DATABASE_COLUMNS:
                if column['table_name'] == def_column['table_name'] and \
                        column['column_name'] == def_column['column_name']:
                    found = True
                    continue

            if found:
                continue
            else:
                errors.append(
                    'Could not find column_name/table_name/data_type in Column.DATABASE_COLUMNS: %s' % column)

        self.assertEqual(errors, [])

    def test_get_priorities(self):
        priors = Column.retrieve_priorities(self.fake_org.id)
        self.assertEqual(priors['PropertyState']['lot_number'], 'Favor New')
        self.assertEqual(priors['PropertyState']['extra_data']["Apostrophe's Field"], 'Favor New')
        self.assertEqual(priors['TaxLotState']['custom_id_1'], 'Favor New')
        self.assertEqual(priors['TaxLotState']['extra_data']['Gross Floor Area'], 'Favor New')

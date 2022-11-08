# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

import os.path

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from quantityfield.units import ureg

from seed import models as seed_models
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    DATA_STATE_MATCHING,
    Column,
    ColumnMapping,
    PropertyState
)
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakeTaxLotStateFactory
)
from seed.utils.organizations import create_organization


class TestColumns(TestCase):

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
            column_name='Some Weird City ID',
            organization=org2
        )
        mapped_column = seed_models.Column.objects.create(
            table_name='PropertyState',
            column_name='custom_id_1',
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
            ('PropertyState', 'custom_id_1', 100)
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
            'raw_data_0': ('PropertyState', 'destination_0', '', True),
            'raw_data_1': ('PropertyState', 'destination_1', '', True),
            'raw_data_2': ('TaxLotState', 'destination_0', '', True),
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
            'Wookiee': ('PropertyState', 'Dothraki', '', True),
            'address': ('TaxLotState', 'address', '', True),
            'eui': ('PropertyState', 'site_eui', 'Site EUI', False),
            # 'Ewok': ('TaxLotState', 'Merovingian'), # this does not show up because it was set before the last one
            'Ewok': ('TaxLotState', 'Hattin', '', True),
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
            'PropertyState': {
                'Wookiee': ('PropertyState', 'Dothraki', '', True),
                'eui': ('PropertyState', 'site_eui', 'Site EUI', False),
            },
            'TaxLotState': {
                'address': ('TaxLotState', 'address', '', True),
                'Ewok': ('TaxLotState', 'Hattin', '', True),
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
        with self.assertRaisesRegex(Exception, "Mapping file does not exist: .*/no-file.csv"):
            Column.create_mappings_from_file(self.mapping_import_file, self.fake_org,
                                             self.fake_user)

    def test_save_column_mapping_by_file(self):
        self.mapping_import_file = os.path.abspath("./seed/tests/data/test_mapping.csv")
        Column.create_mappings_from_file(self.mapping_import_file, self.fake_org, self.fake_user)

        expected = {
            'City': ('PropertyState', 'city'),
            'Custom ID': ('PropertyState', 'custom_id_1'),
            'Zip': ('PropertyState', 'postal_code'),
            'GBA': ('PropertyState', 'gross_floor_area'),
            'PM Property ID': ('PropertyState', 'pm_property_id'),
            'BLDGS': ('PropertyState', 'building_count'),
            'AYB_YearBuilt': ('PropertyState', 'year_build'),
            'State': ('PropertyState', 'state'),
            'Address': ('PropertyState', 'address_line_1'),
            'Owner': ('PropertyState', 'owner'),
            'Raw Column': ('Table Name', 'Field Name'),
            'Property Type': ('PropertyState', 'property_type'),
            'UBI': ('TaxLotState', 'jurisdiction_tax_lot_id')
        }

        test_mapping, _ = ColumnMapping.get_column_mappings(self.fake_org)
        self.assertCountEqual(expected, test_mapping)

    def test_column_cant_be_both_extra_data_and_matching_criteria(self):
        extra_data_column = Column.objects.create(
            table_name='PropertyState',
            column_name='test_column',
            organization=self.fake_org,
            is_extra_data=True,
        )

        extra_data_column.is_matching_criteria = True
        with self.assertRaises(IntegrityError):
            extra_data_column.save()

        rextra_data_column = Column.objects.get(pk=extra_data_column.id)
        self.assertTrue(rextra_data_column.is_extra_data)
        self.assertFalse(rextra_data_column.is_matching_criteria)

    def test_column_has_description(self):
        org1 = Organization.objects.create()
        # Raw columns don't have a table name!
        raw_column = seed_models.Column.objects.create(
            column_name='site_eui',
            organization=org1
        )
        self.assertEqual(raw_column.column_name, raw_column.column_description)


class TestRenameColumns(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.client.login(**user_details)

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.tax_lot_state_factory = FakeTaxLotStateFactory(organization=self.org)

        self.extra_data_column = Column.objects.create(
            table_name='PropertyState',
            column_name='test_column',
            organization=self.org,
            is_extra_data=True,
        )

    def test_rename_column_no_data(self):
        address_column = Column.objects.filter(column_name='address_line_1').first()

        # verify that the column has to be new
        self.assertFalse(address_column.rename_column('custom_id_1')[0])

    def test_rename_column_no_data_and_force(self):
        orig_address_column = Column.objects.filter(column_name='address_line_1').first()

        # verify that the column has to be new
        self.assertTrue(orig_address_column.rename_column('custom_id_1', True)[0])

        # get the address column and check the fields
        address_column = Column.objects.filter(column_name='address_line_1').first()
        self.assertEqual(address_column.is_extra_data, False)
        self.assertEqual(address_column.display_name, orig_address_column.display_name)

    def test_rename_column_field_to_field(self):
        address_column = Column.objects.filter(column_name='address_line_1').first()

        # create the test data and assemble the expected data result
        expected_data = []
        for i in range(0, 20):
            state = self.property_state_factory.get_property_state(data_state=DATA_STATE_MATCHING)
            expected_data.append(state.address_line_1)

        result = address_column.rename_column('property_type', force=True)
        self.assertTrue(result)

        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'property_type', flat=True)
        )
        self.assertListEqual(results, expected_data)

        # verify that the original field is now empty
        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'address_line_1', flat=True)
        )
        self.assertListEqual(results, [None for _x in range(20)])

    def test_rename_column_field_to_extra_data(self):
        address_column = Column.objects.filter(column_name='address_line_1').first()

        # create the test data and assemble the expected data result
        expected_data = []
        for i in range(0, 20):
            state = self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                extra_data={'string': 'abc %s' % i})
            expected_data.append({'string': state.extra_data['string'],
                                  'new_address_line_1': state.address_line_1})

        result = address_column.rename_column('new_address_line_1')
        self.assertTrue(result)

        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'extra_data', flat=True)
        )
        self.assertListEqual(results, expected_data)

        # verify that the original field is now empty
        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'address_line_1', flat=True)
        )
        self.assertListEqual(results, [None for _x in range(20)])

    def test_rename_column_extra_data_to_field(self):
        # create the test data and assemble the expected data result
        expected_data = []
        for i in range(0, 20):
            state = self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                extra_data={self.extra_data_column.column_name: 'abc %s' % i, 'skip': 'value'}
            )
            expected_data.append(state.extra_data[self.extra_data_column.column_name])

        result = self.extra_data_column.rename_column('address_line_1', force=True)
        self.assertTrue(result)

        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'address_line_1', flat=True)
        )
        self.assertListEqual(results, expected_data)

        # verify that the original field is now empty
        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'extra_data', flat=True)
        )
        self.assertListEqual(results, [{'skip': 'value'} for _x in range(20)])

    def test_rename_column_extra_data_to_extra_data(self):
        # create the test data and assemble the expected data result
        expected_data = []
        for i in range(0, 20):
            state = self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                extra_data={self.extra_data_column.column_name: 'abc %s' % i, 'skip': 'value'}
            )
            expected_data.append(state.extra_data[self.extra_data_column.column_name])

        result = self.extra_data_column.rename_column('new_extra', force=True)
        self.assertTrue(result)

        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'extra_data', flat=True)
        )
        results = [x['new_extra'] for x in results]
        self.assertListEqual(results, expected_data)

        # verify that the original field is now empty
        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'extra_data', flat=True)
        )
        results = [x.get(self.extra_data_column.column_name, None) for x in results]
        self.assertListEqual(results, [None for _x in range(20)])

    def test_rename_column_extra_data_to_field_int_to_int(self):
        # create the test data and assemble the expected data result
        expected_data = []
        for i in range(0, 20):
            state = self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                extra_data={self.extra_data_column.column_name: i}
            )
            expected_data.append(state.extra_data[self.extra_data_column.column_name])

        result = self.extra_data_column.rename_column('building_count', force=True)
        self.assertTrue(result)

        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'building_count', flat=True)
        )
        self.assertListEqual(results, expected_data)

    def test_rename_datetime_field_to_extra_data(self):
        expected_data = []

        new_col_name = 'recent_sale_date_renamed'

        for i in range(0, 5):
            date = "2018-04-02T19:53:0{}+00:00".format(i)
            state = self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                recent_sale_date=date
            )
            expected_data.append({new_col_name: state.recent_sale_date})

        old_column = Column.objects.filter(column_name='recent_sale_date').first()
        result = old_column.rename_column(new_col_name)
        self.assertTrue(result)

        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'extra_data', flat=True)
        )

        self.assertListEqual(results, expected_data)

    def test_rename_datetime_field_to_another_datetime_field(self):
        expected_data = []

        new_col_name = 'recent_sale_date'

        for i in range(0, 5):
            date = "2018-04-02T19:53:0{}+00:00".format(i)
            self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                generation_date=date
            )
            expected_data.append(date)

        old_column = Column.objects.filter(column_name='generation_date').first()
        result = old_column.rename_column(new_col_name, force=True)
        self.assertTrue(result)

        new_col_results_raw = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                new_col_name, flat=True)
        )
        new_col_results = [dt.isoformat() for dt in new_col_results_raw]
        self.assertListEqual(new_col_results, expected_data)

        # Check that generation_dates were cleared
        for p in PropertyState.objects.all():
            self.assertIsNone(p.generation_date)

    def test_rename_extra_data_field_to_datetime_field_success(self):
        expected_data = []

        new_col_name = 'recent_sale_date'

        for i in range(0, 5):
            date = "2018-04-02T19:53:0{}+00:00".format(i)
            self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                extra_data={self.extra_data_column.column_name: date}
            )
            expected_data.append(date)

        result = self.extra_data_column.rename_column(new_col_name, force=True)
        self.assertTrue(result)

        raw_results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                new_col_name, flat=True)
        )

        results = [dt.isoformat() for dt in raw_results]

        self.assertListEqual(results, expected_data)

    def test_rename_extra_data_field_to_datetime_field_unsuccessful(self):
        expected_data = []
        original_column_count = Column.objects.count()

        new_col_name = 'recent_sale_date'

        for i in range(9, 11):  # range is purposely set to cause errors in the date format but not immediately
            date = "2018-04-02T19:53:0{}+00:00".format(i)
            self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                extra_data={self.extra_data_column.column_name: date}
            )
            expected_data.append(date)

        result = self.extra_data_column.rename_column(new_col_name, force=True)
        self.assertEqual(result, [False, "The column data aren't formatted properly for the new column due to type constraints (e.g., Datatime, Quantities, etc.)."])

        new_column_count = Column.objects.count()
        self.assertEqual(original_column_count, new_column_count)

        # Check that none of the PropertyStates were updated.
        for p in PropertyState.objects.all():
            self.assertIsNone(p.recent_sale_date)

    def test_rename_date_field_to_extra_data(self):
        expected_data = []

        new_col_name = 'year_ending_renamed'

        for i in range(1, 5):
            date = "2018-04-0{}".format(i)
            state = self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                year_ending=date
            )
            expected_data.append({new_col_name: state.year_ending})

        old_column = Column.objects.filter(column_name='year_ending').first()
        result = old_column.rename_column(new_col_name)
        self.assertTrue(result)

        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'extra_data', flat=True)
        )

        self.assertListEqual(results, expected_data)

    def test_rename_extra_data_field_to_date_field_success(self):
        expected_data = []

        new_col_name = 'year_ending'

        for i in range(1, 5):
            date = "2018-04-0{}".format(i)
            self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                extra_data={self.extra_data_column.column_name: date}
            )
            expected_data.append(date)

        result = self.extra_data_column.rename_column(new_col_name, force=True)
        self.assertTrue(result)

        raw_results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                new_col_name, flat=True)
        )

        results = [dt.isoformat() for dt in raw_results]

        self.assertListEqual(results, expected_data)

    def test_rename_extra_data_field_to_date_field_unsuccessful(self):
        expected_data = []
        original_column_count = Column.objects.count()

        new_col_name = 'year_ending'

        for i in range(9, 11):  # range is purposely set to cause errors in the date format but not immediately
            date = "2018-04-0{}".format(i)
            self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                extra_data={self.extra_data_column.column_name: date}
            )
            expected_data.append(date)

        result = self.extra_data_column.rename_column(new_col_name, force=True)
        self.assertEqual(result, [False, "The column data aren't formatted properly for the new column due to type constraints (e.g., Datatime, Quantities, etc.)."])

        new_column_count = Column.objects.count()
        self.assertEqual(original_column_count, new_column_count)

        # Check that none of the PropertyStates were updated.
        for p in PropertyState.objects.all():
            self.assertIsNone(p.recent_sale_date)

    def test_rename_quantity_field_to_extra_data(self):
        expected_data = []

        new_col_name = 'gross_floor_area_renamed'

        for i in range(1, 5):
            area = i * 100.5
            self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                gross_floor_area=area
            )
            expected_data.append({new_col_name: area})

        old_column = Column.objects.filter(column_name='gross_floor_area').first()
        result = old_column.rename_column(new_col_name)
        self.assertTrue(result)

        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'extra_data', flat=True)
        )

        self.assertListEqual(results, expected_data)

    def test_rename_extra_data_field_to_quantity_field_success(self):
        expected_data = []

        new_col_name = 'gross_floor_area'

        for i in range(1, 5):
            area = i * 100.5
            self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                extra_data={self.extra_data_column.column_name: area}
            )
            expected_data.append(ureg.Quantity(area, "foot ** 2"))

        result = self.extra_data_column.rename_column(new_col_name, force=True)
        self.assertTrue(result)

        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'gross_floor_area', flat=True)
        )

        self.assertListEqual(results, expected_data)

    def test_rename_extra_data_field_to_quantity_field_unsuccessful(self):
        expected_data = []
        original_column_count = Column.objects.count()

        new_col_name = 'gross_floor_area'

        for i in range(0, 2):
            # add a valid and invalid area
            area = (100 if i == 0 else "not a number")
            state = self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                extra_data={self.extra_data_column.column_name: area}
            )
            # Capture default gross_floor_areas
            expected_data.append(ureg.Quantity(state.gross_floor_area, "foot ** 2"))

        result = self.extra_data_column.rename_column(new_col_name, force=True)
        self.assertEqual(result, [False, "The column data aren't formatted properly for the new column due to type constraints (e.g., Datatime, Quantities, etc.)."])

        new_column_count = Column.objects.count()
        self.assertEqual(original_column_count, new_column_count)

        # check that the states' gross_floor_area values were unchanged
        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'gross_floor_area', flat=True)
        )

        self.assertListEqual(results, expected_data)

    def test_rename_quantity_field_to_another_quantity_field_success(self):
        expected_data = []

        new_col_name = 'occupied_floor_area'

        for i in range(1, 5):
            area = i * 100.5
            self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                gross_floor_area=area
            )
            # Capture the magnitude with default occupied_floor_area units
            expected_data.append(ureg.Quantity(area, "foot ** 2"))

        old_column = Column.objects.filter(column_name='gross_floor_area').first()
        result = old_column.rename_column(new_col_name, force=True)
        self.assertTrue(result)

        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                new_col_name, flat=True)
        )

        self.assertListEqual(results, expected_data)

        # Check that gross_floor_areas were cleared
        for p in PropertyState.objects.all():
            self.assertIsNone(p.gross_floor_area)

    def test_rename_quantity_field_to_another_quantity_field_unsuccessful(self):
        # This should be unsuccessful because conversions don't exist between certain column units
        expected_data = []
        original_column_count = Column.objects.count()

        new_col_name = 'site_eui'

        for i in range(1, 5):
            area = i * 100.5
            self.property_state_factory.get_property_state(
                data_state=DATA_STATE_MATCHING,
                gross_floor_area=area
            )
            # Capture these pre-rename-attempt values
            expected_data.append(ureg.Quantity(area, "foot ** 2"))

        old_column = Column.objects.filter(column_name='gross_floor_area').first()
        result = old_column.rename_column(new_col_name, force=True)
        self.assertEqual(result, [False, "The column data can't be converted to the new column due to conversion constraints (e.g., converting square feet to kBtu etc.)."])

        new_column_count = Column.objects.count()
        self.assertEqual(original_column_count, new_column_count)

        # check that the states' gross_floor_area values were unchanged
        results = list(
            PropertyState.objects.filter(organization=self.org).order_by('id').values_list(
                'gross_floor_area', flat=True)
        )

        self.assertListEqual(results, expected_data)

    def test_rename_property_campus_field_unsuccessful(self):
        old_column = Column.objects.filter(column_name='campus').first()
        result = old_column.rename_column("new_col_name", force=True)
        self.assertEqual(result, [False, "Can't move data out of reserved column 'campus'"])


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
            column_name='Column A',
            table_name='PropertyState',
            organization=self.fake_org,
            is_extra_data=True,
            shared_field_type=Column.SHARED_PUBLIC,
        )
        # field that is in the import, but not mapped to
        raw_column = seed_models.Column.objects.create(
            column_name='not mapped data',
            organization=self.fake_org,
        )
        dm = seed_models.ColumnMapping.objects.create()
        dm.column_raw.add(raw_column)
        dm.column_mapped.add(column_a)
        dm.save()
        seed_models.Column.objects.create(
            column_name="Apostrophe's Field",
            table_name='PropertyState',
            organization=self.fake_org,
            is_extra_data=True
        )
        seed_models.Column.objects.create(
            column_name='id',
            table_name='PropertyState',
            organization=self.fake_org,
            is_extra_data=True
        )
        seed_models.Column.objects.create(
            column_name='tax_lot_id_not_used',
            table_name='TaxLotState',
            organization=self.fake_org,
            is_extra_data=True
        )
        seed_models.Column.objects.create(
            column_name='Gross Floor Area',
            table_name='TaxLotState',
            organization=self.fake_org,
            is_extra_data=True
        )

    def test_is_extra_data_validation(self):
        # This is an invalid column. It is not a db field but is not marked as extra data
        with self.assertRaises(ValidationError):
            seed_models.Column.objects.create(
                column_name='not extra data',
                table_name='PropertyState',
                organization=self.fake_org,
                is_extra_data=False
            )

        # verify that creating columns from CSV's will not raise ValidationErrors
        column = seed_models.Column.objects.create(
            column_name='column from csv file',
            # table_name='PropertyState',
            organization=self.fake_org,
            # is_extra_data=False
        )
        column.delete()

        column = seed_models.Column.objects.create(
            column_name='column from csv file empty table',
            table_name='',
            organization=self.fake_org,
            # is_extra_data=False
        )
        column.delete()

        column = seed_models.Column.objects.create(
            column_name='column from csv file empty table false extra_data',
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
            del result['organization_id']  # org changes based on test

        # Check for columns
        c = {
            'table_name': 'PropertyState',
            'column_name': 'Column A',
            'display_name': 'Column A',
            'column_description': 'Column A',
            'is_extra_data': True,
            'merge_protection': 'Favor New',
            'data_type': 'None',
            'geocoding_order': 0,
            'related': False,
            'sharedFieldType': 'Public',
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': False,
            'recognize_empty': False,
            'comstock_mapping': None,
            'derived_column': None,
        }
        self.assertIn(c, columns)

        # Check that display_name doesn't capitalize after apostrophe
        c = {
            'table_name': 'PropertyState',
            'column_name': "Apostrophe's Field",
            'display_name': "Apostrophe's Field",
            'column_description': "Apostrophe's Field",
            'is_extra_data': True,
            'merge_protection': 'Favor New',
            'data_type': 'None',
            'geocoding_order': 0,
            'related': False,
            'sharedFieldType': 'None',
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': False,
            'recognize_empty': False,
            'comstock_mapping': None,
            'derived_column': None,
        }
        self.assertIn(c, columns)

        # Check 'id' field if extra_data
        c = {
            'table_name': 'PropertyState',
            'column_name': 'id',
            'display_name': 'id',
            'column_description': 'id',
            'is_extra_data': True,
            'merge_protection': 'Favor New',
            'data_type': 'None',
            'geocoding_order': 0,
            'related': False,
            'sharedFieldType': 'None',
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': False,
            'recognize_empty': False,
            'comstock_mapping': None,
            'derived_column': None,
        }
        self.assertIn(c, columns)

        # check the 'pinIfNative' argument
        c = {
            'table_name': 'PropertyState',
            'column_name': 'pm_property_id',
            'display_name': 'PM Property ID',
            'column_description': 'PM Property ID',
            'is_extra_data': False,
            'merge_protection': 'Favor New',
            'data_type': 'string',
            'geocoding_order': 0,
            'pinnedLeft': True,
            'related': False,
            'sharedFieldType': 'None',
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': True,
            'recognize_empty': False,
            'comstock_mapping': None,
            'derived_column': None,
        }
        self.assertIn(c, columns)

        # verity that the 'duplicateNameInOtherTable' is working
        c = {
            'table_name': 'TaxLotState',
            'column_name': 'state',
            'display_name': 'State (Tax Lot)',
            'column_description': 'State',
            'data_type': 'string',
            'geocoding_order': 4,
            'is_extra_data': False,
            'merge_protection': 'Favor New',
            'sharedFieldType': 'None',
            'related': True,
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': False,
            'recognize_empty': False,
            'comstock_mapping': None,
            'derived_column': None,
        }
        self.assertIn(c, columns)

        c = {
            'table_name': 'TaxLotState',
            'column_name': 'Gross Floor Area',
            'display_name': 'Gross Floor Area (Tax Lot)',
            'column_description': 'Gross Floor Area',
            'data_type': 'None',
            'geocoding_order': 0,
            'is_extra_data': True,
            'merge_protection': 'Favor New',
            'sharedFieldType': 'None',
            'related': True,
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': False,
            'recognize_empty': False,
            'comstock_mapping': None,
            'derived_column': None,
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
            del result['organization_id']

        c = {
            'table_name': 'TaxLotState',
            'column_name': 'Gross Floor Area',
            'display_name': 'Gross Floor Area',
            'column_description': 'Gross Floor Area',
            'data_type': 'None',
            'geocoding_order': 0,
            'is_extra_data': True,
            'merge_protection': 'Favor New',
            'sharedFieldType': 'None',
            'related': False,
            'unit_name': None,
            'unit_type': None,
            'is_matching_criteria': False,
            'recognize_empty': False,
            'comstock_mapping': None,
            'derived_column': None,
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
            column_name='custom_id_1',
            table_name='PropertyState',
            organization=self.fake_org,
            is_extra_data=True
        )

        with self.assertRaisesRegex(Exception, 'Duplicate name'):
            Column.retrieve_all(self.fake_org.pk, 'property', False)

    def test_column_retrieve_schema(self):
        schema = {
            "types": {
                "address_line_1": "string",
                "address_line_2": "string",
                "audit_template_building_id": "string",
                "block_number": "string",
                "building_certification": "string",
                "building_count": "integer",
                "campus": "boolean",
                "city": "string",
                "conditioned_floor_area": "float",
                "created": "datetime",
                "custom_id_1": "string",
                "district": "string",
                "egrid_subregion_code": "string",
                "energy_alerts": "string",
                "energy_score": "integer",
                "generation_date": "datetime",
                "geocoding_confidence": "string",
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
                "property_footprint": "geometry",
                "property_name": "string",
                "property_notes": "string",
                "property_type": "string",
                "property_timezone": "string",
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
                "taxlot_footprint": "geometry",
                "total_marginal_ghg_emissions": "float",
                "total_marginal_ghg_emissions_intensity": "float",
                "total_ghg_emissions": "float",
                "total_ghg_emissions_intensity": "float",
                "ubid": "string",
                "ulid": "string",
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

        data = ['address_line_1', 'address_line_2', 'audit_template_building_id', 'block_number',
                'building_certification', 'building_count', 'campus', 'city',
                'conditioned_floor_area', 'created', 'custom_id_1', 'district', 'egrid_subregion_code', 'energy_alerts',
                'energy_score', 'generation_date', 'geocoding_confidence', 'gross_floor_area',
                'home_energy_score_id', 'jurisdiction_property_id', 'jurisdiction_tax_lot_id',
                'latitude', 'longitude', 'lot_number', 'normalized_address', 'number_properties',
                'occupied_floor_area', 'owner', 'owner_address', 'owner_city_state', 'owner_email',
                'owner_postal_code', 'owner_telephone', 'pm_parent_property_id', 'pm_property_id',
                'postal_code', 'property_footprint', 'property_name', 'property_notes',
                'property_type', 'property_timezone',
                'recent_sale_date', 'release_date', 'site_eui', 'site_eui_modeled',
                'site_eui_weather_normalized', 'source_eui', 'source_eui_modeled',
                'source_eui_weather_normalized', 'space_alerts', 'state', 'taxlot_footprint',
                'total_ghg_emissions', 'total_ghg_emissions_intensity',
                'total_marginal_ghg_emissions', 'total_marginal_ghg_emissions_intensity',
                'ubid', 'ulid', 'updated',
                'use_description', 'year_built', 'year_ending']

        self.assertCountEqual(c, data)

    def test_retrieve_db_field_name_from_db_tables(self):
        """These values are the fields that can be used for hashing a property to check if it is the same record."""
        expected = ['address_line_1', 'address_line_2', 'audit_template_building_id', 'block_number', 'building_certification',
                    'building_count', 'city', 'conditioned_floor_area',
                    'custom_id_1', 'district', 'egrid_subregion_code', 'energy_alerts', 'energy_score', 'generation_date',
                    'gross_floor_area', 'home_energy_score_id', 'jurisdiction_property_id',
                    'jurisdiction_tax_lot_id', 'latitude', 'longitude', 'lot_number',
                    'number_properties', 'occupied_floor_area', 'owner', 'owner_address',
                    'owner_city_state', 'owner_email', 'owner_postal_code', 'owner_telephone',
                    'pm_parent_property_id', 'pm_property_id', 'postal_code', 'property_footprint',
                    'property_name', 'property_notes', 'property_timezone', 'property_type', 'recent_sale_date',
                    'release_date', 'site_eui', 'site_eui_modeled', 'site_eui_weather_normalized', 'source_eui',
                    'source_eui_modeled', 'source_eui_weather_normalized', 'space_alerts', 'state',
                    'taxlot_footprint', 'total_ghg_emissions', 'total_ghg_emissions_intensity',
                    'total_marginal_ghg_emissions', 'total_marginal_ghg_emissions_intensity',
                    'ubid', 'ulid', 'use_description', 'year_built', 'year_ending']

        method_columns = Column.retrieve_db_field_name_for_hash_comparison()
        self.assertListEqual(method_columns, expected)

    def test_retrieve_db_field_table_and_names_from_db_tables(self):
        names = Column.retrieve_db_field_table_and_names_from_db_tables()
        self.assertIn(('PropertyState', 'gross_floor_area'), names)
        self.assertIn(('TaxLotState', 'address_line_1'), names)
        self.assertNotIn(('PropertyState', 'gross_floor_area_orig'), names)

    def test_retrieve_all_as_tuple(self):
        list_result = Column.retrieve_all_by_tuple(self.fake_org)
        self.assertIn(('PropertyState', 'site_eui_modeled'), list_result)
        self.assertIn(('TaxLotState', 'tax_lot_id_not_used'), list_result)
        self.assertIn(('PropertyState', 'gross_floor_area'),
                      list_result)  # extra field in taxlot, but not in property
        self.assertIn(('TaxLotState', 'Gross Floor Area'),
                      list_result)  # extra field in taxlot, but not in property

    def test_db_columns_in_default_columns(self):
        """
        This test ensures that all the columns in the database are defined in the Column.DEFAULT_COLUMNS

        If a user add a new database column then this test will fail until the column is defined in
        Column.DEFAULT_COLUMNS
        """

        all_columns = Column.retrieve_db_fields_from_db_tables()

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

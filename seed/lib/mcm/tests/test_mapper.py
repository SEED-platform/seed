# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import copy
from unittest import TestCase

from seed.lib.mcm import cleaners, mapper
from seed.lib.mcm.tests.utils import FakeModel


class TestMapper(TestCase):
    # Pre-existing static mapping
    fake_mapping = {
        u'Property Id': (u'FakeModel', u'property_id'),
        u'Year Ending': (u'FakeModel', u'year_ending'),
        u'heading1': (u'FakeModel', u'heading_1'),
        u'heading2': (u'FakeModel', u'heading_2'),
        u'heading3': (u'FakeModel', u'heading_3'),
        u'heading4': (u'FakeModel', u'heading_4'),
        u'heading5': (u'FakeModel', u'heading_5'),
    }

    # Which of the fields in the model are considered extra_data fields?
    extra_data_fields = [
        u'heading3',
        u'heading4',
        u'heading5'
    ]

    # Columns we get from the user's CSV
    raw_columns = [
        u'Address',
        u'Name',
        u'City',
        u'BBL',
        u'Building ID',
    ]
    # Columns we'll try to create a mapping to dynamically
    dest_columns = [
        (u'PropertyState', u'address_line_1'),
        (u'PropertyState', u'name'),
        (u'PropertyState', u'city'),
        (u'TaxLotState', u'jurisdiction_tax_lot_id'),
        (u'PropertyState', u'custom_id_1'),
    ]

    expected = {
        u'Address': [u'PropertyState', u'address_line_1', 90],
        u'BBL': [u'PropertyState', u'custom_id_1', 0],
        u'Building ID': [u'TaxLotState', u'jurisdiction_tax_lot_id', 59],
        u'City': [u'PropertyState', u'city', 100],
        u'Name': [u'PropertyState', u'name', 100]
    }

    test_cleaning_schema = {
        'types': {
            'property_id': 'float',
        }
    }

    test_cleaner = cleaners.Cleaner(test_cleaning_schema)

    def setUp(self):
        self.maxDiff = None

    def test_map_row(self):
        """Test the mapping between csv values and python objects."""
        fake_row = {
            u'Property Id': u'234235423',
            u'Year Ending': u'2013/03/13',
            u'heading1': u'value1',
            u'heading2': u'value2',
            u'heading3': u'value3',
            u'heading4': u'',
            u'heading5': None,
        }
        fake_model_class = FakeModel

        modified_model = mapper.map_row(
            fake_row, self.fake_mapping, fake_model_class, self.extra_data_fields
        )

        # empty columns should not result in entries in extra_data
        expected_extra = {
            u'heading_3': u'value3',
            u'heading_4': u''
        }

        self.assertEqual(getattr(modified_model, u'property_id'), u'234235423')
        self.assertEqual(getattr(modified_model, u'year_ending'), u'2013/03/13')
        self.assertEqual(getattr(modified_model, u'heading_1'), u'value1')
        self.assertEqual(getattr(modified_model, u'heading_2'), u'value2')
        self.assertTrue(isinstance(getattr(modified_model, 'extra_data'), dict))
        self.assertEqual(modified_model.extra_data, expected_extra)

    def test_map_row_extra_data_empty_columns(self):
        """map_row should include empty columns in extra_data"""
        fake_row = {
            u'heading3': u'value3',
            u'heading4': u'',
        }
        fake_model_class = FakeModel

        modified_model = mapper.map_row(
            fake_row, self.fake_mapping, fake_model_class
        )

        expected_extra = {u'heading_3': u'value3', u'heading_4': u''}

        self.assertTrue(
            isinstance(getattr(modified_model, 'extra_data'), dict)
        )
        self.assertEqual(modified_model.extra_data, expected_extra)

    def test_build_column_mapping(self):
        """Create a useful set of suggestions for mappings."""
        dyn_mapping = mapper.build_column_mapping(
            self.raw_columns, self.dest_columns
        )
        self.assertDictEqual(dyn_mapping, self.expected)

    def test_build_column_mapping_w_callable(self):
        """Callable result at the begining of the list."""
        expected = {
            u'Address': [u'PropertyState', u'address_line_1', 90],
            u'BBL': [u'TaxLotState', u'jurisdiction_tax_lot_id', 0],
            u'Building ID': [u'PropertyState', u'custom_id_1', 27],
            u'City': [u'PropertyState', u'city', 100],
            u'Name': [u'PropertyState', u'name', 100]
        }

        # Here we pretend that we're doing a query and returning
        # relevant results.

        def get_mapping(raw, *args, **kwargs):
            if raw == u'Building ID':
                return [u'PropertyState', u'custom_id_1', 27]

        dyn_mapping = mapper.build_column_mapping(
            self.raw_columns,
            self.dest_columns,
            previous_mapping=get_mapping,
        )

        self.assertDictEqual(dyn_mapping, expected)

    def test_build_column_mapping_w_callable_and_ignored_column(self):
        """
        tests that an ignored column (`['', 100]`) should not return a
        suggestion.
        """
        expected = copy.deepcopy(self.expected)
        # This should be the result of our "previous_mapping" call.
        expected[u'Building ID'] = [u'', u'', 100]

        # Here we pretend that the callable `get_mapping` finds that the column
        # has been saved as '' i.e ignored.
        def get_mapping(raw, *args, **kwargs):
            if raw == u'Building ID':
                return [u'', u'', 100]

        dyn_mapping = mapper.build_column_mapping(
            self.raw_columns,
            self.dest_columns,
            previous_mapping=get_mapping,
        )

        self.assertDictEqual(dyn_mapping, expected)

    def test_build_column_mapping_w_null_saved(self):
        """We handle explicit saves of null, and return those dutifully."""
        expected = copy.deepcopy(self.expected)
        # This should be the result of our "previous_mapping" call.
        expected[u'Building ID'] = [None, None, 1]

        # Here we pretend that we're doing a query and returning
        # relevant results.
        def get_mapping(raw, *args, **kwargs):
            if raw == u'Building ID':
                return [None, None, 1]

        dyn_mapping = mapper.build_column_mapping(
            self.raw_columns,
            self.dest_columns,
            previous_mapping=get_mapping,
        )

        self.assertDictEqual(dyn_mapping, expected)

    def test_build_column_mapping_w_no_match(self):
        """We return the raw column name if there's no good match."""
        raw_columns = [
            u'Address',
            u'Name',
            u'City',
            u'BBL',
            u'Building ID',
        ]
        dest_columns = [
            (u'PropertyState', u'address_line_1'),
            (u'PropertyState', u'name'),
            (u'PropertyState', u'city'),
            (u'TaxLotState', u'jurisdiction_tax_lot_id'),
        ]
        expected = {
            u'Address': [u'PropertyState', u'address_line_1', 90],
            u'BBL': [u'PropertyState', u'BBL', 100],
            u'Building ID': [u'TaxLotState', u'jurisdiction_tax_lot_id', 59],
            u'City': [u'PropertyState', u'city', 100],
            u'Name': [u'PropertyState', u'name', 100]
        }

        mapping = mapper.build_column_mapping(raw_columns, dest_columns, thresh=50)
        self.assertDictEqual(mapping, expected)

    def test_map_row_dynamic_mapping_with_cleaner(self):
        """Type-based cleaners on dynamic fields based on reverse-mapping."""
        mapper.build_column_mapping(
            self.raw_columns, self.dest_columns
        )
        fake_row = {
            u'Property Id': u'234,235,423',
            u'heading1': u'value1',
        }
        fake_model_class = FakeModel

        modified_model = mapper.map_row(
            fake_row,
            self.fake_mapping,
            fake_model_class,
            cleaner=self.test_cleaner
        )

        self.assertEqual(modified_model.property_id, 234235423.0)

    def test_map_row_handle_unmapped_columns(self):
        """No KeyError when we check mappings for our column."""
        test_mapping = copy.deepcopy(self.fake_mapping)
        del test_mapping[u'Property Id']
        fake_row = {
            u'Property Id': u'234,235,423',
            u'heading1': u'value1',
        }
        fake_model_class = FakeModel
        modified_model = mapper.map_row(
            fake_row,
            test_mapping,
            fake_model_class,
            cleaner=self.test_cleaner
        )

        self.assertEqual(getattr(modified_model, 'property_id', None), None)
        self.assertEqual(getattr(modified_model, 'heading_1'), u'value1')

    def test_map_row_w_initial_data(self):
        """Make sure that we apply initial data before mapping."""
        test_mapping = copy.deepcopy(self.fake_mapping)
        initial_data = {'property_name': 'Example'}
        fake_row = {
            u'Property Id': u'234,235,423',
            u'heading1': u'value1',
        }
        fake_model_class = FakeModel
        modified_model = mapper.map_row(
            fake_row,
            test_mapping,
            fake_model_class,
            cleaner=self.test_cleaner,
            initial_data=initial_data
        )

        # Our data is set by initial_data
        self.assertEqual(
            getattr(modified_model, 'property_name', None), 'Example'
        )
        # Even though we have no explicit mapping for it.
        self.assertTrue('property_name' not in test_mapping)

    def test_expand_field(self):
        r = mapper.expand_and_normalize_field(None)
        self.assertEqual(r, None)
        r = mapper.expand_and_normalize_field(10000)
        self.assertEqual(r, 10000)
        r = mapper.expand_and_normalize_field("123,15543;32132:321321;1231;:,::", False)
        self.assertEqual(r, "123;15543;32132;321321;1231")
        r = mapper.expand_and_normalize_field(u"4815162342")
        self.assertEqual(r, '4815162342')
        r = mapper.expand_and_normalize_field(u"4\\//\\//\\\\-815162342")
        self.assertEqual(r, '4815162342')

        # Returning lists
        r = mapper.expand_and_normalize_field(10000, True)
        self.assertEqual(r, [10000])
        r = mapper.expand_and_normalize_field('1,2,3', True)
        self.assertEqual(r, ['1', '2', '3'])
        r = mapper.expand_and_normalize_field("123,15543;32132:321321;1231", True)
        self.assertEqual(r, ['123', '15543', '32132', '321321', '1231'])
        r = mapper.expand_and_normalize_field("123,15543;32132:321321;1231;987", True)
        self.assertEqual(r, ['123', '15543', '32132', '321321', '1231', '987'])
        r = mapper.expand_and_normalize_field(u"123,15543;32132:321321;1231;987", True)
        self.assertEqual(r, ['123', '15543', '32132', '321321', '1231', '987'])
        r = mapper.expand_and_normalize_field("33366555; 33366125; 33366148", True)
        self.assertEqual(r, ["33366555", "33366125", "33366148"])
        r = mapper.expand_and_normalize_field(
            "000064545; 0000--34-23492-0; 00///1234: //12  34\\1234", True)
        self.assertEqual(r, ['000064545', '000034234920', '001234', '12341234'])

    def test_clean_single_row(self):
        data = {
            u'city': u'Meereen',
            u'country': u'Westeros',
            u'jurisdiction_tax_lot_id': '155\\/\///2813'
        }

        expected = [
            {
                u'city': u'Meereen',
                u'country': u'Westeros',
                u'jurisdiction_tax_lot_id': '1552813'
            }
        ]

        r = mapper.expand_rows(data, ['jurisdiction_tax_lot_id'], False)
        self.assertListEqual(r, expected)

    def test_clean_single_row_no_expand(self):
        data = {
            u'city': u'Meereen',
            u'country': u'Westeros',
            u'jurisdiction_tax_lot_id': '123;234,345:456'
        }
        expected = [
            {
                u'city': u'Meereen',
                u'country': u'Westeros',
                u'jurisdiction_tax_lot_id': '123;234;345;456'
            }
        ]
        r = mapper.expand_rows(data, ['jurisdiction_tax_lot_id'], False)
        self.assertListEqual(r, expected)

    def test_expand_two_fields(self):
        data = {
            u'city': u'Meereen',
            u'country': u'Westeros',
            u'jurisdiction_tax_lot_id': '123,234',
            u'another_field': 'abc,bcd'
        }

        expected = [
            {u'jurisdiction_tax_lot_id': '123', u'city': u'Meereen', u'another_field': 'ABC',
             u'country': u'Westeros'},
            {u'jurisdiction_tax_lot_id': '123', u'city': u'Meereen', u'another_field': 'BCD',
             u'country': u'Westeros'},
            {u'jurisdiction_tax_lot_id': '234', u'city': u'Meereen', u'another_field': 'ABC',
             u'country': u'Westeros'},
            {u'jurisdiction_tax_lot_id': '234', u'city': u'Meereen', u'another_field': 'BCD',
             u'country': u'Westeros'}
        ]
        r = mapper.expand_rows(data, ['jurisdiction_tax_lot_id', 'another_field'], True)
        self.assertListEqual(r, expected)

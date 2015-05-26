"""
:copyright: (c) 2014 Building Energy Inc
"""
import copy
from unittest import TestCase

from mcm import cleaners
from mcm import mapper
from mcm.tests.utils import FakeModel


class TestMapper(TestCase):
    # Pre-existing static mapping
    fake_mapping = {
        u'Property Id': u'property_id',
        u'Year Ending': u'year_ending',
        u'heading1': u'heading_1',
        u'heading2': u'heading_2',
    }

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
        u'address_line_1',
        u'name',
        u'city',
        u'tax_lot_id',
        u'custom_id_1'
    ]

    expected = {
        u'Address': [u'address_line_1', 90],
        u'BBL': [u'tax_lot_id', 47],
        u'Building ID': [u'tax_lot_id', 52],
        u'City': [u'city', 100],
        u'Name': [u'name', 100]
    }

    test_cleaning_schema = {'types': {
        'property_id': 'float',
    }}

    test_cleaner = cleaners.Cleaner(test_cleaning_schema)

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
            fake_row, self.fake_mapping, fake_model_class
        )

        # empty columns should not result in entries in extra_data
        expected_extra = {u'heading3': u'value3'}

        self.assertEqual(getattr(modified_model, u'property_id'), u'234235423')
        self.assertEqual(
            getattr(modified_model, u'year_ending'), u'2013/03/13'
        )
        self.assertEqual(getattr(modified_model, u'heading_1'), u'value1')
        self.assertEqual(getattr(modified_model, u'heading_2'), u'value2')
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
        expected = copy.deepcopy(self.expected)
        # This should be the result of our "previous_mapping" call.
        expected[u'Building ID'] = [u'custom_id_1', 27]

        # Here we pretend that we're doing a query and returning
        # relevant results.
        def get_mapping(raw, *args, **kwargs):
            if raw == u'Building ID':
                return [u'custom_id_1', 27]

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
        expected[u'Building ID'] = [None, 1]

        # Here we pretend that we're doing a query and returning
        # relevant results.
        def get_mapping(raw, *args, **kwargs):
            if raw == u'Building ID':
                return [None, 1]

        dyn_mapping = mapper.build_column_mapping(
            self.raw_columns,
            self.dest_columns,
            previous_mapping=get_mapping,
        )

        self.assertDictEqual(dyn_mapping, expected)

    def test_build_column_mapping_w_no_match(self):
        """We return None if there's no good match."""
        expected = copy.deepcopy(self.expected)
        # This should be the result of our "previous_mapping" call.
        null_result = [None, 0]
        expected[u'BBL'] = null_result

        dyn_mapping = mapper.build_column_mapping(
            self.raw_columns,
            self.dest_columns,
            thresh=48
        )

        self.assertDictEqual(dyn_mapping, expected)

    def test_map_w_apply_func(self):
        """Make sure that our ``apply_func`` is run against specified items."""
        fake_model_class = FakeModel
        fake_row = {
            u'Property Id': u'234,235,423',
            u'heading1': u'value1',
            u'Space Warning': 'Something to do with space.',
        }

        def test_apply_func(model, item, value):
            if not getattr(model, 'mapped_extra_data', None):
                model.mapped_extra_data = {}
            model.mapped_extra_data[item] = value

        modified_model = mapper.map_row(
            fake_row,
            self.fake_mapping,
            fake_model_class,
            cleaner=self.test_cleaner,
            apply_func=test_apply_func,
            apply_columns=['Property Id', 'heading1']
        )

        # Assert that our function was called only on our specified column
        # and that its value was set as expected.
        self.assertDictEqual(
            modified_model.mapped_extra_data,
            {
                u'heading_1': u'value1',        # Saved correct column name.
                u'property_id': 234235423.0     # Also saved correct type.
            }
        )

        # Still maintain that things which aren't mapped, even by apply_func
        # go to the extra_data bucket.
        self.assertDictEqual(
            modified_model.extra_data,
            {'Space Warning': 'Something to do with space.'}
        )

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
        del(test_mapping[u'Property Id'])
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

    def test_map_row_w_concat(self):
        """Make sure that concatenation works."""
        test_mapping = copy.deepcopy(self.fake_mapping)
        concat = {
            'target': 'address_1',
            # Reconstruct in this precise order.
            'concat_columns': ['street number', 'quadrant', 'street name']
            # No need to specify a delimier here, our default is a space.
        }

        fake_row = {
            u'street number': u'1232',
            u'street name': u'Fanfare St.',
            u'quadrant': u'NE',
        }

        modified_model = mapper.map_row(
            fake_row,
            test_mapping,
            FakeModel,
            concat=concat
        )

        # Note: address_1 mapping was dynamically defined by the concat
        # config.
        self.assertEqual(modified_model.address_1, u'1232 NE Fanfare St.')

    def test_map_row_w_concat_and_delimiter(self):
        """Make sure we honor the delimiter."""
        concat = {
            'target': 'address_1',
            # Reconstruct in this precise order.
            'concat_columns': ['street number', 'quadrant', 'street name'],
            # No need to specify a delimier here, our default is a space.
            'delimiter': '/',
        }
        fake_row = {
            u'street number': u'1232',
            u'street name': u'Fanfare St.',
            u'quadrant': u'NE',
        }

        modified_model = mapper.map_row(
            fake_row,
            self.fake_mapping,
            FakeModel,
            concat=concat
        )

        self.assertEqual(modified_model.address_1, u'1232/NE/Fanfare St.')

    def test_map_row_w_bad_concat_config(self):
        """Test expected behavior with bad concat config data."""
        fake_row = {
            u'street number': u'1232',
            u'Property Id': u'23423423',
            u'street name': u'Fanfare St.',
            u'quadrant': u'NE',
        }

        # No target defined.
        bad_concat1 = {
            'concat_columns': ['street number', 'quadrant', 'street name'],
        }

        modified_model = mapper.map_row(
            fake_row,
            self.fake_mapping,
            FakeModel,
            concat=bad_concat1
        )

        expected = u'1232 NE Fanfare St.'
        # We default to saving it to an attribute that won't get serialized.
        self.assertEqual(modified_model.__broken_target__, expected)

        # Now with target, but including unknown column headers.
        bad_concat2 = {
            'concat_columns': ['face', 'thing', 'street number', 'quadrant'],
            'target': 'address_1',
        }

        modified_model = mapper.map_row(
            fake_row,
            self.fake_mapping,
            FakeModel,
            concat=bad_concat2
        )

        # All of our non-sense headers were simply ignored.
        self.assertEqual(modified_model.address_1, u'1232 NE')

        bad_concat2 = {
            'target': 'address_1'
        }

        modified_model = mapper.map_row(
            fake_row,
            self.fake_mapping,
            FakeModel,
            concat=bad_concat2
        )

        # If we don't specify any columns to concatenate, do nothing
        self.assertEqual(getattr(modified_model, 'address_1', None), None)

    def test_concat_multiple_targets(self):
        """Make sure we're able to create multiple concatenation targets."""
        fake_row = {
            u'street number': u'1232',
            u'Property Id': u'23423423',
            u'street name': u'Fanfare St.',
            u'quadrant': u'NE',
            u'sale_month': '01',
            u'sale_day': '23',
            u'sale_year': '2012',
        }

        # No target defined.
        concat = [
            # For our street data.
            {
                'target': 'address1',
                'concat_columns': ['street number', 'quadrant', 'street name'],
            },
            # For our sale data.
            {
                'target': 'sale_date',
                'concat_columns': ['sale_month', 'sale_day', 'sale_year'],
                'delimiter': '/'
            }
        ]

        modified_model = mapper.map_row(
            fake_row,
            self.fake_mapping,
            FakeModel,
            concat=concat
        )

        st_expected = u'1232 NE Fanfare St.'
        sale_expected = u'01/23/2012'
        self.assertEqual(modified_model.address1, st_expected)
        self.assertEqual(modified_model.sale_date, sale_expected)

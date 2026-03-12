"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from datetime import date, datetime
from unittest.mock import Mock

from django.test import TestCase

from seed.lib.mcm.mapper import apply_column_value


class ApplyColumnValueTest(TestCase):
    def setUp(self):
        # Create a simple mock model with extra_data support
        self.model = Mock()
        self.model.__class__.__name__ = "PropertyState"
        self.model.extra_data = {}

    def test_applies_value_to_model_attribute(self):
        mapping = {"Address": ("PropertyState", "address", "Address", False)}

        result = apply_column_value(
            raw_column_name="Address", column_value="123 Main St", model=self.model, mapping=mapping, is_extra_data=False, cleaner=None
        )

        self.assertEqual(result.address, "123 Main St")

    def test_applies_value_to_extra_data(self):
        mapping = {"Custom Field": ("PropertyState", "custom_field", "Custom Field", True)}

        result = apply_column_value(
            raw_column_name="Custom Field", column_value="Custom Value", model=self.model, mapping=mapping, is_extra_data=True, cleaner=None
        )

        self.assertEqual(result.extra_data["custom_field"], "Custom Value")

    def test_postal_code_formatting_with_dash(self):
        mapping = {"Postal Code": ("PropertyState", "postal_code", "Postal Code", False)}

        result = apply_column_value(
            raw_column_name="Postal Code", column_value="12345-6789", model=self.model, mapping=mapping, is_extra_data=False, cleaner=None
        )

        self.assertEqual(result.postal_code, "12345-6789")

    def test_postal_code_formatting_without_dash(self):
        mapping = {"Postal Code": ("PropertyState", "postal_code", "Postal Code", False)}

        result = apply_column_value(
            raw_column_name="Postal Code", column_value="123", model=self.model, mapping=mapping, is_extra_data=False, cleaner=None
        )

        self.assertEqual(result.postal_code, "00123")

    def test_blank_postal_code(self):
        """Blank values are not formatted. 0 values converted to '00000'"""
        mapping = {"Postal Code": ("PropertyState", "postal_code", "Postal Code", False)}

        def get_result(value):
            return apply_column_value(
                raw_column_name="Postal Code", column_value=value, model=self.model, mapping=mapping, is_extra_data=False, cleaner=None
            )

        result = get_result("")
        self.assertEqual(result.postal_code, None)
        result = get_result(None)
        self.assertEqual(result.postal_code, None)
        result = get_result(0)
        self.assertEqual(result.postal_code, "00000")

    def test_datetime_in_extra_data_converts_to_isoformat(self):
        mapping = {"Date Field": ("PropertyState", "date_field", "Date Field", True)}
        test_date = datetime(2024, 1, 15, 10, 30, 0)

        result = apply_column_value(
            raw_column_name="Date Field", column_value=test_date, model=self.model, mapping=mapping, is_extra_data=True, cleaner=None
        )

        self.assertEqual(result.extra_data["date_field"], "2024-01-15T10:30:00")

    def test_date_in_extra_data_converts_to_isoformat(self):
        mapping = {"Date Field": ("PropertyState", "date_field", "Date Field", True)}
        test_date = date(2024, 1, 15)

        result = apply_column_value(
            raw_column_name="Date Field", column_value=test_date, model=self.model, mapping=mapping, is_extra_data=True, cleaner=None
        )

        self.assertEqual(result.extra_data["date_field"], "2024-01-15")

    def test_ignores_mismatched_table_name_for_extra_data(self):
        mapping = {"Custom Field": ("TaxLotState", "custom_field", "Custom Field", True)}

        result = apply_column_value(
            raw_column_name="Custom Field",
            column_value="Custom Value",
            model=self.model,  # PropertyState model
            mapping=mapping,  # TaxLotState mapping
            is_extra_data=True,
            cleaner=None,
        )

        self.assertNotIn("custom_field", result.extra_data)

    def test_uses_cleaner_when_provided(self):
        mapping = {"Year Built": ("PropertyState", "year_built", "Year Built", False)}
        mock_cleaner = Mock()
        mock_cleaner.clean_value = Mock(return_value=2020)

        result = apply_column_value(
            raw_column_name="Year Built", column_value="2020", model=self.model, mapping=mapping, is_extra_data=False, cleaner=mock_cleaner
        )

        mock_cleaner.clean_value.assert_called_once_with("2020", "year_built", False)
        self.assertEqual(result.year_built, 2020)

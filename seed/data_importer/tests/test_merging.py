# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from django.test import TestCase

from seed.lib.merging.merging import PropertyState_to_PropertyState, TaxLotState_to_TaxLotState

logger = logging.getLogger(__name__)


class StateFieldsTest(TestCase):
    """Tests that our logic for constructing cleaners works."""

    def test_property_state(self):
        expected = (('address_line_1', 'address_line_1'), ('address_line_2', 'address_line_2'),
                    ('analysis_end_time', 'analysis_end_time'), ('analysis_start_time', 'analysis_start_time'),
                    ('analysis_state', 'analysis_state'), ('analysis_state_message', 'analysis_state_message'),
                    ('building_certification', 'building_certification'), ('building_count', 'building_count'),
                    ('city', 'city'), ('conditioned_floor_area', 'conditioned_floor_area'),
                    ('custom_id_1', 'custom_id_1'), ('energy_alerts', 'energy_alerts'),
                    ('energy_score', 'energy_score'), ('generation_date', 'generation_date'),
                    ('gross_floor_area', 'gross_floor_area'), ('home_energy_score_id', 'home_energy_score_id'),
                    ('import_file', 'import_file'), ('jurisdiction_property_id', 'jurisdiction_property_id'),
                    ('latitude', 'latitude'), ('longitude', 'longitude'), ('lot_number', 'lot_number'),
                    ('normalized_address', 'normalized_address'), ('occupied_floor_area', 'occupied_floor_area'),
                    ('owner', 'owner'), ('owner_address', 'owner_address'), ('owner_city_state', 'owner_city_state'),
                    ('owner_email', 'owner_email'), ('owner_postal_code', 'owner_postal_code'),
                    ('owner_telephone', 'owner_telephone'), ('pm_parent_property_id', 'pm_parent_property_id'),
                    ('pm_property_id', 'pm_property_id'), ('postal_code', 'postal_code'),
                    ('property_name', 'property_name'), ('property_notes', 'property_notes'),
                    ('property_type', 'property_type'), ('recent_sale_date', 'recent_sale_date'),
                    ('release_date', 'release_date'), ('site_eui', 'site_eui'),
                    ('site_eui_modeled', 'site_eui_modeled'),
                    ('site_eui_weather_normalized', 'site_eui_weather_normalized'), ('source_eui', 'source_eui'),
                    ('source_eui_modeled', 'source_eui_modeled'),
                    ('source_eui_weather_normalized', 'source_eui_weather_normalized'),
                    ('space_alerts', 'space_alerts'), ('state', 'state'), ('ubid', 'ubid'),
                    ('use_description', 'use_description'), ('year_built', 'year_built'),
                    ('year_ending', 'year_ending'))
        self.assertSequenceEqual(expected, PropertyState_to_PropertyState)

    def test_taxlot_state(self):
        expected = (
        ('address_line_1', 'address_line_1'), ('address_line_2', 'address_line_2'), ('block_number', 'block_number'),
        ('city', 'city'), ('custom_id_1', 'custom_id_1'), ('district', 'district'), ('import_file', 'import_file'),
        ('jurisdiction_tax_lot_id', 'jurisdiction_tax_lot_id'), ('normalized_address', 'normalized_address'),
        ('number_properties', 'number_properties'), ('postal_code', 'postal_code'), ('state', 'state'))
        self.assertSequenceEqual(expected, TaxLotState_to_TaxLotState)

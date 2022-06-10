# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import logging

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.merging import merging
from seed.lib.merging.merging import get_state_attrs, get_state_to_state_tuple
from seed.models import (
    Column,
    Measure,
    Meter,
    MeterReading,
    PropertyMeasure,
    PropertyState,
    Scenario
)
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeTaxLotViewFactory
)
from seed.utils.geocode import long_lat_wkt
from seed.utils.organizations import create_organization

logger = logging.getLogger(__name__)


class StateFieldsTest(TestCase):
    """Tests that our logic for constructing cleaners works."""

    def setUp(self):
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.taxlot_view_factory = FakeTaxLotViewFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org, user=self.user)

    def test_get_state_attrs(self):
        # create the column for data_1
        Column.objects.create(
            column_name='data_1',
            table_name='TaxLotState',
            organization=self.org,
            is_extra_data=True,
        )
        tlv1 = self.taxlot_view_factory.get_taxlot_view(extra_data={"data_1": "value_1"})
        tlv2 = self.taxlot_view_factory.get_taxlot_view(extra_data={"data_1": "value_2"})

        self.assertEqual(tlv1.state.extra_data['data_1'], 'value_1')
        self.assertEqual(tlv2.state.extra_data['data_1'], 'value_2')

        res = get_state_attrs([tlv1.state, tlv2.state])
        self.assertEqual(res['custom_id_1'], {tlv2.state: None, tlv1.state: None})
        self.assertEqual(res['postal_code'],
                         {tlv2.state: tlv2.state.postal_code, tlv1.state: tlv1.state.postal_code})
        self.assertTrue('data_1' not in res)

    def test_property_state(self):
        self.property_view_factory.get_property_view()
        self.taxlot_view_factory.get_taxlot_view()

        expected = (('address_line_1', 'address_line_1'),
                    ('address_line_2', 'address_line_2'),
                    ('building_certification', 'building_certification'),
                    ('building_count', 'building_count'),
                    ('city', 'city'),
                    ('conditioned_floor_area', 'conditioned_floor_area'),
                    ('custom_id_1', 'custom_id_1'),
                    ('egrid_subregion_code', 'egrid_subregion_code'),
                    ('energy_alerts', 'energy_alerts'),
                    ('energy_score', 'energy_score'),
                    ('generation_date', 'generation_date'),
                    ('geocoding_confidence', 'geocoding_confidence'),
                    ('gross_floor_area', 'gross_floor_area'),
                    ('home_energy_score_id', 'home_energy_score_id'),
                    ('jurisdiction_property_id', 'jurisdiction_property_id'),
                    ('latitude', 'latitude'),
                    ('long_lat', 'long_lat'),
                    ('longitude', 'longitude'),
                    ('lot_number', 'lot_number'),
                    ('occupied_floor_area', 'occupied_floor_area'),
                    ('owner', 'owner'),
                    ('owner_address', 'owner_address'),
                    ('owner_city_state', 'owner_city_state'),
                    ('owner_email', 'owner_email'),
                    ('owner_postal_code', 'owner_postal_code'),
                    ('owner_telephone', 'owner_telephone'),
                    ('pm_parent_property_id', 'pm_parent_property_id'),
                    ('pm_property_id', 'pm_property_id'),
                    ('postal_code', 'postal_code'),
                    ('property_footprint', 'property_footprint'),
                    ('property_name', 'property_name'),
                    ('property_notes', 'property_notes'),
                    ('property_timezone', 'property_timezone'),
                    ('property_type', 'property_type'),
                    ('recent_sale_date', 'recent_sale_date'),
                    ('release_date', 'release_date'),
                    ('site_eui', 'site_eui'),
                    ('site_eui_modeled', 'site_eui_modeled'),
                    ('site_eui_weather_normalized', 'site_eui_weather_normalized'),
                    ('source_eui', 'source_eui'),
                    ('source_eui_modeled', 'source_eui_modeled'),
                    ('source_eui_weather_normalized', 'source_eui_weather_normalized'),
                    ('space_alerts', 'space_alerts'),
                    ('state', 'state'),
                    ('total_ghg_emissions', 'total_ghg_emissions'),
                    ('total_ghg_emissions_intensity', 'total_ghg_emissions_intensity'),
                    ('total_marginal_ghg_emissions', 'total_marginal_ghg_emissions'),
                    ('total_marginal_ghg_emissions_intensity', 'total_marginal_ghg_emissions_intensity'),
                    ('ubid', 'ubid'),
                    ('use_description', 'use_description'),
                    ('year_built', 'year_built'),
                    ('year_ending', 'year_ending'))

        result = get_state_to_state_tuple('PropertyState')
        self.assertSequenceEqual(expected, result)

    def test_taxlot_state(self):
        expected = (
            ('address_line_1', 'address_line_1'),
            ('address_line_2', 'address_line_2'),
            ('block_number', 'block_number'),
            ('city', 'city'),
            ('custom_id_1', 'custom_id_1'),
            ('district', 'district'),
            ('geocoding_confidence', 'geocoding_confidence'),
            ('jurisdiction_tax_lot_id', 'jurisdiction_tax_lot_id'),
            ('latitude', 'latitude'),
            ('long_lat', 'long_lat'),
            ('longitude', 'longitude'),
            ('number_properties', 'number_properties'),
            ('postal_code', 'postal_code'),
            ('state', 'state'),
            ('taxlot_footprint', 'taxlot_footprint'),
            ('ulid', 'ulid'))
        result = get_state_to_state_tuple('TaxLotState')
        self.assertSequenceEqual(expected, result)

    def test_merge_state_favor_existing(self):
        pv1 = self.property_view_factory.get_property_view(
            address_line_1='original_address', address_line_2='orig',
            extra_data={'field_1': 'orig_value'}
        )
        pv2 = self.property_view_factory.get_property_view(
            address_line_1='new_address', address_line_2='new',
            extra_data={'field_1': 'new_value'}
        )

        # Do not set priority for address_line_2 to make sure that it chooses t
        column_priorities = {
            'address_line_1': 'Favor Existing', 'extra_data': {'field_1': 'Favor Existing'}
        }

        result = merging.merge_state(pv1.state, pv1.state, pv2.state, column_priorities)
        self.assertEqual(result.address_line_1, 'original_address')
        self.assertEqual(result.address_line_2, 'new')
        self.assertEqual(result.extra_data['field_1'], 'orig_value')

    def test_merge_geocoding_results_no_merge_protection(self):
        """
        When merging records that have geocoding results, if none of the
        geocoding results columns have merge protection but both records have
        some form of geocoding results, completely "take" the results from
        the "new" state.
        """
        pv1 = self.property_view_factory.get_property_view(
            address_line_1='original_address',
            latitude=39.765251,
            longitude=-104.986138,
            geocoding_confidence='High (P1AAA)',
            long_lat='POINT (-104.986138 39.765251)',
        )
        pv2 = self.property_view_factory.get_property_view(
            address_line_1='new_address',
            geocoding_confidence='Low - check address (Z1XAA)',
        )

        # Column priorities while purposely leaving out long_lat (as it's not available to users)
        column_priorities = {
            'address_line_1': 'Favor New',
            'geocoding_confidence': 'Favor New',
            'latitude': 'Favor New',
            'longitude': 'Favor New',
            'extra_data': {}
        }

        result = merging.merge_state(pv1.state, pv1.state, pv2.state, column_priorities)
        self.assertEqual(result.geocoding_confidence, 'Low - check address (Z1XAA)')
        self.assertIsNone(result.latitude)
        self.assertIsNone(result.longitude)
        self.assertIsNone(result.long_lat)

    def test_merge_geocoding_results_with_merge_protection(self):
        """
        When merging records that have geocoding results, if any of the
        geocoding results columns have merge protection, and both records have
        some form of geocoding results, completely "take" the results from
        the "existing" state.
        """
        pv1 = self.property_view_factory.get_property_view(
            address_line_1='original_address',
            latitude=39.765251,
            longitude=-104.986138,
            geocoding_confidence='High (P1AAA)',
            long_lat='POINT (-104.986138 39.765251)',
        )
        pv2 = self.property_view_factory.get_property_view(
            address_line_1='new_address',
            geocoding_confidence='Low - check address (Z1XAA)',
        )

        # Column priorities while purposely leaving out long_lat (as it's not available to users)
        column_priorities = {
            'address_line_1': 'Favor New',
            'geocoding_confidence': 'Favor Existing',
            'latitude': 'Favor New',
            'longitude': 'Favor New',
            'extra_data': {}
        }

        result = merging.merge_state(pv1.state, pv1.state, pv2.state, column_priorities)
        self.assertEqual(result.geocoding_confidence, 'High (P1AAA)')
        self.assertEqual(result.latitude, 39.765251)
        self.assertEqual(result.longitude, -104.986138)
        self.assertEqual(long_lat_wkt(result), 'POINT (-104.986138 39.765251)')

    def test_merge_geocoding_results_unpopulated_existing_state_ignores_merge_protections(self):
        """
        When merging records with geocoding columns that have merge protection
        active, if only one record has geocoding results, always take the
        geocoding results from the one record, regardless of merge
        protection settings.
        """
        pv1 = self.property_view_factory.get_property_view(
            address_line_1='original_address',
        )
        pv2 = self.property_view_factory.get_property_view(
            address_line_1='new_address',
            geocoding_confidence='Low - check address (Z1XAA)',
        )

        # Column priorities while purposely leaving out long_lat (as it's not available to users)
        column_priorities = {
            'address_line_1': 'Favor New',
            'geocoding_confidence': 'Favor Existing',
            'latitude': 'Favor Existing',
            'longitude': 'Favor Existing',
            'extra_data': {}
        }

        result = merging.merge_state(pv1.state, pv1.state, pv2.state, column_priorities)
        self.assertEqual(result.geocoding_confidence, 'Low - check address (Z1XAA)')
        self.assertIsNone(result.latitude)
        self.assertIsNone(result.longitude)
        self.assertIsNone(result.long_lat)

    def test_merge_geocoding_results_no_merge_protection_unpopulated_existing_state(self):
        """
        When merging records with geocoding columns that have merge protection
        active, if only one record has geocoding results, always take the
        geocoding results from the one record, regardless of merge
        protection settings.
        """
        pv1 = self.property_view_factory.get_property_view(
            address_line_1='original_address',
            geocoding_confidence='Low - check address (Z1XAA)',
        )
        pv2 = self.property_view_factory.get_property_view(
            address_line_1='new_address',
        )

        # Column priorities while purposely leaving out long_lat (as it's not available to users)
        column_priorities = {
            'address_line_1': 'Favor New',
            'geocoding_confidence': 'Favor New',
            'latitude': 'Favor New',
            'longitude': 'Favor New',
            'extra_data': {}
        }

        result = merging.merge_state(pv1.state, pv1.state, pv2.state, column_priorities)
        self.assertEqual(result.geocoding_confidence, 'Low - check address (Z1XAA)')
        self.assertIsNone(result.latitude)
        self.assertIsNone(result.longitude)
        self.assertIsNone(result.long_lat)

    def test_merge_geocoding_ignore_merge_protection(self):
        """
        When merging records with geocoding columns including the
        ignore_merge_protection flag as True always takes the "new" state's
        geocoding results regardless of geocoding columns merge protection setting.
        """
        pv1 = self.property_view_factory.get_property_view(
            address_line_1='original_address',
            geocoding_confidence='Low - check address (Z1XAA)',
        )
        pv2 = self.property_view_factory.get_property_view(
            address_line_1='new_address',
            latitude=39.765251,
            longitude=-104.986138,
            geocoding_confidence='High (P1AAA)',
            long_lat='POINT (-104.986138 39.765251)',
        )

        # Column priorities while purposely leaving out long_lat (as it's not available to users)
        column_priorities = {
            'address_line_1': 'Favor New',
            'geocoding_confidence': 'Favor Existing',
            'latitude': 'Favor New',
            'longitude': 'Favor New',
            'extra_data': {}
        }

        result = merging.merge_state(pv1.state, pv1.state, pv2.state, column_priorities, True)
        self.assertEqual(result.geocoding_confidence, 'High (P1AAA)')
        self.assertEqual(result.latitude, 39.765251)
        self.assertEqual(result.longitude, -104.986138)
        self.assertEqual(long_lat_wkt(result), 'POINT (-104.986138 39.765251)')

    def test_merge_extra_data(self):
        ed1 = {'field_1': 'orig_value_1', 'field_2': 'orig_value_1', 'field_3': 'only_in_ed1'}
        ed2 = {'field_1': 'new_value_1', 'field_2': 'new_value_2', 'field_4': 'only_in_ed2'}

        # this also tests a priority on the new field but with an existing value that doesn't exist
        # in the new data.
        priorities = {'field_1': 'Favor Existing', 'field_3': 'Favor New'}
        result = merging._merge_extra_data(ed1, ed2, priorities, [])
        expected = {
            'field_1': 'orig_value_1',
            'field_2': 'new_value_2',
            'field_3': 'only_in_ed1',
            'field_4': 'only_in_ed2'
        }
        logger.error(f'--- {result}')
        self.assertDictEqual(result, expected)

    def test_recognize_empty_column_setting_allows_empty_values_to_overwrite_nonempty_values(self):
        # create 2 records
        pv1 = self.property_view_factory.get_property_view(
            address_line_1='original_address',
            energy_score=None,
            extra_data={
                'ed_field_1': 'ed_original_value',
                'ed_field_2': None
            }
        )
        pv2 = self.property_view_factory.get_property_view(
            address_line_1=None,
            energy_score=86,
            extra_data={
                'ed_field_1': None,
                'ed_field_2': 'ED eighty-six'
            }
        )

        # Update and create columns with recognize_empty = True
        self.org.column_set.filter(
            table_name='PropertyState',
            column_name__in=['address_line_1', 'energy_score']
        ).update(recognize_empty=True)
        Column.objects.create(
            column_name='ed_field_1',
            table_name='PropertyState',
            organization=self.org,
            is_extra_data=True,
            recognize_empty=True
        )
        Column.objects.create(
            column_name='ed_field_2',
            table_name='PropertyState',
            organization=self.org,
            is_extra_data=True,
            recognize_empty=True
        )

        # Treat pv1.state as "newer"
        result = merging.merge_state(pv2.state, pv2.state, pv1.state, {'extra_data': {}})

        # should be all the values from state 1
        self.assertEqual(result.address_line_1, 'original_address')
        self.assertIsNone(result.energy_score)
        self.assertEqual(result.extra_data['ed_field_1'], 'ed_original_value')
        self.assertIsNone(result.extra_data['ed_field_2'])

    def test_recognize_empty_and_favor_new_column_settings_together(self):
        # create 2 records
        pv1 = self.property_view_factory.get_property_view(
            address_line_1='original_address',
            energy_score=None,
            extra_data={
                'ed_field_1': 'ed_original_value',
                'ed_field_2': None
            }
        )
        pv2 = self.property_view_factory.get_property_view(
            address_line_1=None,
            energy_score=86,
            extra_data={
                'ed_field_1': None,
                'ed_field_2': 'ED eighty-six'
            }
        )

        # Update and create columns with recognize_empty = True
        self.org.column_set.filter(
            table_name='PropertyState',
            column_name__in=['address_line_1', 'energy_score']
        ).update(recognize_empty=True)
        Column.objects.create(
            column_name='ed_field_1',
            table_name='PropertyState',
            organization=self.org,
            is_extra_data=True,
            recognize_empty=True
        )
        Column.objects.create(
            column_name='ed_field_2',
            table_name='PropertyState',
            organization=self.org,
            is_extra_data=True,
            recognize_empty=True
        )

        # Treat pv1.state as "newer" and favor existing for all priorities
        priorities = {
            'address_line_1': 'Favor Existing',
            'energy_score': 'Favor Existing',
            'extra_data': {
                'ed_field_1': 'Favor Existing',
                'ed_field_2': 'Favor Existing'
            }
        }
        result = merging.merge_state(pv2.state, pv2.state, pv1.state, priorities)

        # should be all the values from state 2
        self.assertIsNone(result.address_line_1)
        self.assertEqual(result.energy_score, 86)
        self.assertIsNone(result.extra_data['ed_field_1'])
        self.assertEqual(result.extra_data['ed_field_2'], 'ED eighty-six')


class MergeRelationshipsTest(TestCase):
    """Tests that our logic for merging relationships for states works."""

    def setUp(self):
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

        self.column_priorities = {'extra_data': {}}
        self.measure_1 = Measure.objects.filter(organization=self.org)[0]
        self.measure_2 = Measure.objects.filter(organization=self.org)[1]

    def test_no_new_relationships_when_none_exist(self):
        # -- Setup
        ps1 = self.property_state_factory.get_property_state()
        ps2 = self.property_state_factory.get_property_state()
        merged_state = PropertyState.objects.create(organization=self.org)

        # -- Act
        merging.merge_state(merged_state, ps1, ps2, self.column_priorities)

        # -- Assert
        self.assertEqual(Scenario.objects.count(), 0)
        self.assertEqual(PropertyMeasure.objects.count(), 0)
        self.assertEqual(Meter.objects.count(), 0)
        self.assertEqual(MeterReading.objects.count(), 0)

    def test_both_have_scenarios(self):
        # -- Setup
        ps1 = self.property_state_factory.get_property_state()
        ps2 = self.property_state_factory.get_property_state()

        Scenario.objects.create(name='Scenario 1', property_state=ps1)
        s2 = Scenario.objects.create(name='Scenario 2', property_state=ps2)

        merged_state = PropertyState.objects.create(organization=self.org)

        # -- Act
        merged_state = merging.merge_state(merged_state, ps1, ps2, self.column_priorities)

        # -- Assert
        # Only scenario should remain
        merged_scenarios = Scenario.objects.filter(property_state=merged_state)
        self.assertEqual(merged_scenarios.count(), 1)
        self.assertEqual(merged_scenarios.filter(name=s2.name).count(), 1)

    def test_old_property_state_has_scenario(self):
        # -- Setup
        ps1 = self.property_state_factory.get_property_state()
        ps2 = self.property_state_factory.get_property_state()

        Scenario.objects.create(name='Scenario 1', property_state=ps1)

        merged_state = PropertyState.objects.create(organization=self.org)

        # -- Act
        merged_state = merging.merge_state(merged_state, ps1, ps2, self.column_priorities)

        # -- Assert
        # Only scenario 2 should remain
        merged_scenarios = Scenario.objects.filter(property_state=merged_state)
        self.assertEqual(merged_scenarios.count(), 0)

    def test_new_property_state_has_scenario(self):
        # -- Setup
        ps1 = self.property_state_factory.get_property_state()
        ps2 = self.property_state_factory.get_property_state()

        s2 = Scenario.objects.create(name='Scenario 2', property_state=ps2)

        merged_state = PropertyState.objects.create(organization=self.org)

        # -- Act
        merged_state = merging.merge_state(merged_state, ps1, ps2, self.column_priorities)

        # -- Assert
        # Only scenario 2 should remain
        merged_scenarios = Scenario.objects.filter(property_state=merged_state)
        self.assertEqual(merged_scenarios.count(), 1)
        self.assertEqual(merged_scenarios.filter(name=s2.name).count(), 1)

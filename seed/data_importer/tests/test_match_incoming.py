# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
import os.path as osp
from datetime import date, datetime

import pytz
from django.core.files.uploadedfile import SimpleUploadedFile
from mock import patch

from config.settings.common import BASE_DIR
from seed.data_importer.match import filter_duplicate_states, save_state_match
from seed.data_importer.models import ImportFile
from seed.data_importer.tasks import (
    geocode_and_match_buildings_task,
    map_data,
    save_raw_data
)
from seed.lib.progress_data.progress_data import ProgressData
from seed.lib.xml_mapping.mapper import default_buildingsync_profile_mappings
from seed.models import (
    ASSESSED_RAW,
    BUILDINGSYNC_RAW,
    DATA_STATE_DELETE,
    DATA_STATE_MAPPING,
    DATA_STATE_MATCHING,
    MERGE_STATE_MERGED,
    MERGE_STATE_NEW,
    MERGE_STATE_UNKNOWN,
    Column,
    Cycle,
    Measure,
    Meter,
    MeterReading,
    Property,
    PropertyAuditLog,
    PropertyMeasure,
    PropertyState,
    PropertyView,
    Scenario,
    TaxLot,
    TaxLotAuditLog,
    TaxLotState,
    TaxLotView
)
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakeTaxLotStateFactory
)
from seed.tests.util import DataMappingBaseTestCase


class TestMatchingInImportFile(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_duplicate_properties_identified(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create pair of properties that are exact duplicates
        self.property_state_factory.get_property_state(**base_details)
        self.property_state_factory.get_property_state(**base_details)

        # Create a non-matching, non-duplicate property
        base_details['address_line_1'] = '123 Different Ave'
        base_details['city'] = 'Denver'
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        geocode_and_match_buildings_task(self.import_file.id)

        # 2 Property, 2 PropertyViews, 3 PropertyState (1 flagged to be ignored)
        self.assertEqual(Property.objects.count(), 2)
        self.assertEqual(PropertyView.objects.count(), 2)
        self.assertEqual(PropertyState.objects.count(), 3)
        self.assertEqual(PropertyState.objects.filter(data_state=DATA_STATE_DELETE).count(), 1)

        # Make sure "deleted" -States are not found in the -Views
        deleted = PropertyState.objects.get(data_state=DATA_STATE_DELETE)
        self.assertNotIn(deleted.id, PropertyView.objects.values_list('state_id', flat=True))

    def test_duplicate_taxlots_identified(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create pair of properties that are exact duplicates
        self.taxlot_state_factory.get_taxlot_state(**base_details)
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # Create a non-matching, non-duplicate property
        base_details['address_line_1'] = '123 Different Ave'
        base_details['city'] = 'Denver'
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        geocode_and_match_buildings_task(self.import_file.id)

        # 2 TaxLot, 2 TaxLotViews, 3 TaxLotState (1 flagged to be ignored)
        self.assertEqual(TaxLot.objects.count(), 2)
        self.assertEqual(TaxLotView.objects.count(), 2)
        self.assertEqual(TaxLotState.objects.count(), 3)
        self.assertEqual(TaxLotState.objects.filter(data_state=DATA_STATE_DELETE).count(), 1)

        # Make sure "deleted" -States are not found in the -Views
        deleted = TaxLotState.objects.get(data_state=DATA_STATE_DELETE)
        self.assertNotIn(deleted.id, TaxLotView.objects.values_list('state_id', flat=True))

    def test_match_properties_if_all_default_fields_match(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create first set of properties that match each other
        ps_1 = self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Denver'
        ps_2 = self.property_state_factory.get_property_state(**base_details)

        # Create second set of properties that match each other
        base_details['pm_property_id'] = '11111'
        ps_3 = self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Philadelphia'
        ps_4 = self.property_state_factory.get_property_state(**base_details)

        # Create unmatched property
        base_details['pm_property_id'] = '000'
        ps_5 = self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        geocode_and_match_buildings_task(self.import_file.id)

        # 3 Property, 3 PropertyViews, 7 PropertyStates (5 imported, 2 merge results)
        self.assertEqual(Property.objects.count(), 3)
        self.assertEqual(PropertyView.objects.count(), 3)
        self.assertEqual(PropertyState.objects.count(), 7)

        # Refresh -States and check data_state and merge_state values
        rps_1 = PropertyState.objects.get(pk=ps_1.id)
        self.assertEqual(rps_1.data_state, DATA_STATE_MAPPING)
        self.assertEqual(rps_1.merge_state, MERGE_STATE_UNKNOWN)

        rps_2 = PropertyState.objects.get(pk=ps_2.id)
        self.assertEqual(rps_2.data_state, DATA_STATE_MAPPING)
        self.assertEqual(rps_2.merge_state, MERGE_STATE_UNKNOWN)

        ps_1_plus_2 = PropertyState.objects.filter(
            pm_property_id__isnull=True,
            city='Denver',
            address_line_1='123 Match Street'
        ).exclude(
            data_state=DATA_STATE_MAPPING,
            merge_state=MERGE_STATE_UNKNOWN
        ).get()

        self.assertEqual(ps_1_plus_2.data_state, DATA_STATE_MATCHING)
        self.assertEqual(ps_1_plus_2.merge_state, MERGE_STATE_MERGED)

        rps_3 = PropertyState.objects.get(pk=ps_3.id)
        self.assertEqual(rps_3.data_state, DATA_STATE_MAPPING)
        self.assertEqual(rps_3.merge_state, MERGE_STATE_UNKNOWN)

        rps_4 = PropertyState.objects.get(pk=ps_4.id)
        self.assertEqual(rps_4.data_state, DATA_STATE_MAPPING)
        self.assertEqual(rps_4.merge_state, MERGE_STATE_UNKNOWN)

        ps_3_plus_4 = PropertyState.objects.filter(
            pm_property_id='11111',
            city='Philadelphia',
            address_line_1='123 Match Street'
        ).exclude(
            data_state=DATA_STATE_MAPPING,
            merge_state=MERGE_STATE_UNKNOWN
        ).get()
        self.assertEqual(ps_3_plus_4.data_state, DATA_STATE_MATCHING)
        self.assertEqual(ps_3_plus_4.merge_state, MERGE_STATE_MERGED)

        rps_5 = PropertyState.objects.get(pk=ps_5.id)
        self.assertEqual(rps_5.data_state, DATA_STATE_MATCHING)
        self.assertEqual(rps_5.merge_state, MERGE_STATE_NEW)

    def test_match_taxlots_if_all_default_fields_match(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create first set of taxlots that match each other
        tls_1 = self.taxlot_state_factory.get_taxlot_state(**base_details)
        base_details['city'] = 'Denver'
        tls_2 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        # Create second set of taxlots that match each other
        base_details['jurisdiction_tax_lot_id'] = '11111'
        tls_3 = self.taxlot_state_factory.get_taxlot_state(**base_details)
        base_details['city'] = 'Philadelphia'
        tls_4 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        # Create unmatched taxlot
        base_details['jurisdiction_tax_lot_id'] = '000'
        tls_5 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        geocode_and_match_buildings_task(self.import_file.id)

        # 3 TaxLot, 3 TaxLotViews, 7 TaxLotStates (5 imported, 2 merge results)
        self.assertEqual(TaxLot.objects.count(), 3)
        self.assertEqual(TaxLotView.objects.count(), 3)
        self.assertEqual(TaxLotState.objects.count(), 7)

        # Refresh -States and check data_state and merge_state values
        rtls_1 = TaxLotState.objects.get(pk=tls_1.id)
        self.assertEqual(rtls_1.data_state, DATA_STATE_MAPPING)
        self.assertEqual(rtls_1.merge_state, MERGE_STATE_UNKNOWN)

        rtls_2 = TaxLotState.objects.get(pk=tls_2.id)
        self.assertEqual(rtls_2.data_state, DATA_STATE_MAPPING)
        self.assertEqual(rtls_2.merge_state, MERGE_STATE_UNKNOWN)

        tls_1_plus_2 = TaxLotState.objects.filter(
            jurisdiction_tax_lot_id__isnull=True,
            city='Denver',
            address_line_1='123 Match Street'
        ).exclude(
            data_state=DATA_STATE_MAPPING,
            merge_state=MERGE_STATE_UNKNOWN
        ).get()

        self.assertEqual(tls_1_plus_2.data_state, DATA_STATE_MATCHING)
        self.assertEqual(tls_1_plus_2.merge_state, MERGE_STATE_MERGED)

        rtls_3 = TaxLotState.objects.get(pk=tls_3.id)
        self.assertEqual(rtls_3.data_state, DATA_STATE_MAPPING)
        self.assertEqual(rtls_3.merge_state, MERGE_STATE_UNKNOWN)

        rtls_4 = TaxLotState.objects.get(pk=tls_4.id)
        self.assertEqual(rtls_4.data_state, DATA_STATE_MAPPING)
        self.assertEqual(rtls_4.merge_state, MERGE_STATE_UNKNOWN)

        tls_3_plus_4 = TaxLotState.objects.filter(
            jurisdiction_tax_lot_id='11111',
            city='Philadelphia',
            address_line_1='123 Match Street'
        ).exclude(
            data_state=DATA_STATE_MAPPING,
            merge_state=MERGE_STATE_UNKNOWN
        ).get()
        self.assertEqual(tls_3_plus_4.data_state, DATA_STATE_MATCHING)
        self.assertEqual(tls_3_plus_4.merge_state, MERGE_STATE_MERGED)

        rtls_5 = TaxLotState.objects.get(pk=tls_5.id)
        self.assertEqual(rtls_5.data_state, DATA_STATE_MATCHING)
        self.assertEqual(rtls_5.merge_state, MERGE_STATE_NEW)

    def test_match_properties_on_ubid(self):
        base_details = {
            'ubid': '86HJPCWQ+2VV-1-3-2-3',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create set of properties that match each other
        self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Denver'
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        geocode_and_match_buildings_task(self.import_file.id)

        # 1 Property, 1 PropertyView, 3 PropertyStates (2 imported, 1 merge result)
        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(PropertyView.objects.count(), 1)
        self.assertEqual(PropertyState.objects.count(), 3)

    def test_match_properties_normalized_address_used_instead_of_address_line_1(self):
        base_details = {
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create set of properties that have the same address_line_1 in slightly different format
        base_details['address_line_1'] = '123 Match Street'
        self.property_state_factory.get_property_state(**base_details)
        base_details['address_line_1'] = '123 match St.'
        base_details['city'] = 'Denver'
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        geocode_and_match_buildings_task(self.import_file.id)

        # 1 Property, 1 PropertyView, 3 PropertyStates (2 imported, 1 merge result)
        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(PropertyView.objects.count(), 1)
        self.assertEqual(PropertyState.objects.count(), 3)

    def test_match_taxlots_normalized_address_used_instead_of_address_line_1(self):
        base_details = {
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create set of taxlots that have the same address_line_1 in slightly different format
        base_details['address_line_1'] = '123 Match Street'
        self.taxlot_state_factory.get_taxlot_state(**base_details)
        base_details['address_line_1'] = '123 match St.'
        base_details['city'] = 'Denver'
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        geocode_and_match_buildings_task(self.import_file.id)

        # 1 TaxLot, 1 TaxLotView, 3 TaxLotStates (2 imported, 1 merge result)
        self.assertEqual(TaxLot.objects.count(), 1)
        self.assertEqual(TaxLotView.objects.count(), 1)
        self.assertEqual(TaxLotState.objects.count(), 3)

    def test_no_matches_if_all_matching_criteria_is_None(self):
        """
        Default matching criteria for PropertyStates are:
            - address_line_1 (substituted by normalized_address)
            - ubid
            - pm_property_id
            - custom_id_1
        and all are set to None.
        """
        base_details = {
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }

        # Create set of properties that won't match
        self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Denver'
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        geocode_and_match_buildings_task(self.import_file.id)

        # 2 Property, 2 PropertyView, 2 PropertyStates - No merges
        self.assertEqual(Property.objects.count(), 2)
        self.assertEqual(PropertyView.objects.count(), 2)
        self.assertEqual(PropertyState.objects.count(), 2)

    def test_match_properties_get_rolled_up_into_one_in_the_order_their_uploaded(self):
        """
        The most recently uploaded should take precedence when merging states.
        If more than 2 states match each other, they are merged two at a time
        until one is remaining.

        Reminder, this is only for -States within an ImportFile.
        """
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create first set of properties that match each other
        base_details['city'] = 'Philadelphia'
        self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Arvada'
        self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Golden'
        self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Denver'
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        geocode_and_match_buildings_task(self.import_file.id)

        # 1 Property, 1 PropertyViews, 7 PropertyStates (4 imported, 3 merge results)
        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(PropertyView.objects.count(), 1)
        self.assertEqual(PropertyState.objects.count(), 7)

        self.assertEqual(PropertyView.objects.first().state.city, 'Denver')


class TestMatchingOutsideImportFile(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file_1, self.import_record_1, self.cycle = selfvars

        self.import_record_2, self.import_file_2 = self.create_import_file(
            self.user, self.org, self.cycle
        )

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_duplicate_properties_identified(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create property in first ImportFile
        ps_1 = self.property_state_factory.get_property_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        geocode_and_match_buildings_task(self.import_file_1.id)

        # Create duplicate property coming from second ImportFile
        base_details['import_file_id'] = self.import_file_2.id
        ps_2 = self.property_state_factory.get_property_state(**base_details)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        geocode_and_match_buildings_task(self.import_file_2.id)

        # 1 Property, 1 PropertyViews, 2 PropertyStates
        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(PropertyView.objects.count(), 1)
        self.assertEqual(PropertyState.objects.count(), 2)

        # Be sure the first property is used in the -View and the second is marked for "deletion"
        self.assertEqual(PropertyView.objects.first().state_id, ps_1.id)
        self.assertEqual(PropertyState.objects.get(data_state=DATA_STATE_DELETE).id, ps_2.id)

    def test_match_properties_if_all_default_fields_match(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create property in first ImportFile
        ps_1 = self.property_state_factory.get_property_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        geocode_and_match_buildings_task(self.import_file_1.id)

        # Create properties from second ImportFile, one matching existing PropertyState
        base_details['import_file_id'] = self.import_file_2.id

        base_details['city'] = 'Denver'
        ps_2 = self.property_state_factory.get_property_state(**base_details)

        base_details['pm_property_id'] = '11111'
        base_details['city'] = 'Philadelphia'
        ps_3 = self.property_state_factory.get_property_state(**base_details)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        geocode_and_match_buildings_task(self.import_file_2.id)

        # 2 Property, 2 PropertyViews, 4 PropertyStates (3 imported, 1 merge result)
        self.assertEqual(Property.objects.count(), 2)
        self.assertEqual(PropertyView.objects.count(), 2)
        self.assertEqual(PropertyState.objects.count(), 4)

        cities_from_views = []
        ps_ids_from_views = []
        for pv in PropertyView.objects.all():
            cities_from_views.append(pv.state.city)
            ps_ids_from_views.append(pv.state_id)

        self.assertIn('Denver', cities_from_views)
        self.assertIn('Philadelphia', cities_from_views)

        self.assertIn(ps_3.id, ps_ids_from_views)
        self.assertNotIn(ps_1.id, ps_ids_from_views)
        self.assertNotIn(ps_2.id, ps_ids_from_views)

        # Refresh -States and check data_state and merge_state values
        rps_1 = PropertyState.objects.get(pk=ps_1.id)
        self.assertEqual(rps_1.data_state, DATA_STATE_MATCHING)
        self.assertEqual(rps_1.merge_state, MERGE_STATE_NEW)

        rps_2 = PropertyState.objects.get(pk=ps_2.id)
        self.assertEqual(rps_2.data_state, DATA_STATE_MATCHING)
        self.assertEqual(rps_2.merge_state, MERGE_STATE_UNKNOWN)

        ps_1_plus_2 = PropertyState.objects.filter(
            pm_property_id__isnull=True,
            city='Denver',
            address_line_1='123 Match Street'
        ).exclude(
            data_state=DATA_STATE_MATCHING,
            merge_state=MERGE_STATE_UNKNOWN
        ).get()
        self.assertEqual(ps_1_plus_2.data_state, DATA_STATE_MATCHING)
        self.assertEqual(ps_1_plus_2.merge_state, MERGE_STATE_MERGED)

        rps_3 = PropertyState.objects.get(pk=ps_3.id)
        self.assertEqual(rps_3.data_state, DATA_STATE_MATCHING)
        self.assertEqual(rps_3.merge_state, MERGE_STATE_NEW)

    def test_match_properties_rolls_up_multiple_existing_matches_in_id_order_if_they_exist(self):
        base_details = {
            'pm_property_id': '123MatchID',
            'city': 'Golden',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 3 non-matching properties in first ImportFile
        ps_1 = self.property_state_factory.get_property_state(**base_details)

        base_details['pm_property_id'] = '789DifferentID'
        base_details['city'] = 'Denver'
        ps_2 = self.property_state_factory.get_property_state(**base_details)

        base_details['pm_property_id'] = '1337AnotherDifferentID'
        base_details['city'] = 'Philadelphia'
        ps_3 = self.property_state_factory.get_property_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        geocode_and_match_buildings_task(self.import_file_1.id)

        # Update -States to make the roll up order be 1, 3, 2
        refreshed_ps_3 = PropertyState.objects.get(id=ps_3.id)
        refreshed_ps_3.pm_property_id = '123MatchID'
        refreshed_ps_3.save()

        refreshed_ps_2 = PropertyState.objects.get(id=ps_2.id)
        refreshed_ps_2.pm_property_id = '123MatchID'
        refreshed_ps_2.save()

        # Verify that none of the 3 have been merged
        self.assertEqual(Property.objects.count(), 3)
        self.assertEqual(PropertyState.objects.count(), 3)
        self.assertEqual(PropertyView.objects.count(), 3)

        # Import a property that will identify the first 3 as matches.
        base_details['import_file_id'] = self.import_file_2.id
        base_details['pm_property_id'] = '123MatchID'
        del base_details['city']
        ps_4 = self.property_state_factory.get_property_state(**base_details)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        geocode_and_match_buildings_task(self.import_file_2.id)

        # There should only be one PropertyView which is associated to new, merged -State
        self.assertEqual(PropertyView.objects.count(), 1)
        view = PropertyView.objects.first()
        self.assertNotIn(view.state_id, [ps_1.id, ps_2.id, ps_3.id, ps_4.id])

        # It will have a -State having city as Denver
        self.assertEqual(view.state.city, 'Denver')

        # The corresponding log should be a System Match
        audit_log = PropertyAuditLog.objects.get(state_id=view.state_id)
        self.assertEqual(audit_log.name, 'System Match')

    def test_match_taxlots_if_all_default_fields_match(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create property in first ImportFile
        tls_1 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        geocode_and_match_buildings_task(self.import_file_1.id)

        # Create properties from second ImportFile, one matching existing PropertyState
        base_details['import_file_id'] = self.import_file_2.id

        base_details['city'] = 'Denver'
        tls_2 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['jurisdiction_tax_lot_id'] = '11111'
        base_details['city'] = 'Philadelphia'
        tls_3 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        geocode_and_match_buildings_task(self.import_file_2.id)

        # 2 TaxLot, 2 TaxLotViews, 4 TaxLotStates (3 imported, 1 merge result)
        self.assertEqual(TaxLot.objects.count(), 2)
        self.assertEqual(TaxLotView.objects.count(), 2)
        self.assertEqual(TaxLotState.objects.count(), 4)

        cities_from_views = []
        tls_ids_from_views = []
        for tlv in TaxLotView.objects.all():
            cities_from_views.append(tlv.state.city)
            tls_ids_from_views.append(tlv.state_id)

        self.assertIn('Denver', cities_from_views)
        self.assertIn('Philadelphia', cities_from_views)

        self.assertIn(tls_3.id, tls_ids_from_views)
        self.assertNotIn(tls_1.id, tls_ids_from_views)
        self.assertNotIn(tls_2.id, tls_ids_from_views)

        # Refresh -States and check data_state and merge_state values
        rtls_1 = TaxLotState.objects.get(pk=tls_1.id)
        self.assertEqual(rtls_1.data_state, DATA_STATE_MATCHING)
        self.assertEqual(rtls_1.merge_state, MERGE_STATE_NEW)

        rtls_2 = TaxLotState.objects.get(pk=tls_2.id)
        self.assertEqual(rtls_2.data_state, DATA_STATE_MATCHING)
        self.assertEqual(rtls_2.merge_state, MERGE_STATE_UNKNOWN)

        tls_1_plus_2 = TaxLotState.objects.filter(
            jurisdiction_tax_lot_id__isnull=True,
            city='Denver',
            address_line_1='123 Match Street'
        ).exclude(
            data_state=DATA_STATE_MATCHING,
            merge_state=MERGE_STATE_UNKNOWN
        ).get()
        self.assertEqual(tls_1_plus_2.data_state, DATA_STATE_MATCHING)
        self.assertEqual(tls_1_plus_2.merge_state, MERGE_STATE_MERGED)

        rtls_3 = TaxLotState.objects.get(pk=tls_3.id)
        self.assertEqual(rtls_3.data_state, DATA_STATE_MATCHING)
        self.assertEqual(rtls_3.merge_state, MERGE_STATE_NEW)

    def test_match_taxlots_rolls_up_multiple_existing_matches_in_id_order_if_they_exist(self):
        base_details = {
            'jurisdiction_tax_lot_id': '123MatchID',
            'city': 'Golden',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 3 non-matching taxlots in first ImportFile
        tls_1 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['jurisdiction_tax_lot_id'] = '789DifferentID'
        base_details['city'] = 'Denver'
        tls_2 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['jurisdiction_tax_lot_id'] = '1337AnotherDifferentID'
        base_details['city'] = 'Philadelphia'
        tls_3 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        geocode_and_match_buildings_task(self.import_file_1.id)

        # Make all those states match
        TaxLotState.objects.filter(pk__in=[tls_2.id, tls_3.id]).update(
            jurisdiction_tax_lot_id='123MatchID'
        )

        # Verify that none of the 3 have been merged
        self.assertEqual(TaxLot.objects.count(), 3)
        self.assertEqual(TaxLotState.objects.count(), 3)
        self.assertEqual(TaxLotView.objects.count(), 3)

        # Import a property that will identify the first 3 as matches.
        base_details['import_file_id'] = self.import_file_2.id
        base_details['jurisdiction_tax_lot_id'] = '123MatchID'
        del base_details['city']
        tls_4 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        geocode_and_match_buildings_task(self.import_file_2.id)

        # There should only be one TaxLotView which is associated to new, merged -State
        self.assertEqual(TaxLotView.objects.count(), 1)
        view = TaxLotView.objects.first()
        self.assertNotIn(view.state_id, [tls_1.id, tls_2.id, tls_3.id, tls_4.id])

        # It will have a -State having city as Philadelphia
        self.assertEqual(view.state.city, 'Philadelphia')

        # The corresponding log should be a System Match
        audit_log = TaxLotAuditLog.objects.get(state_id=view.state_id)
        self.assertEqual(audit_log.name, 'System Match')


class TestMatchingImportIntegration(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file_1, self.import_record_1, self.cycle = selfvars

        self.import_record_2, self.import_file_2 = self.create_import_file(
            self.user, self.org, self.cycle
        )

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_properties(self):
        # Define matching values
        matching_pm_property_id = '11111'
        matching_address_line_1 = '123 Match Street'
        matching_ubid = '86HJPCWQ+2VV-1-3-2-3'
        matching_custom_id_1 = 'MatchingID12345'

        # For first file, create properties with no duplicates or matches
        base_details_file_1 = {
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }

        # No matching_criteria values
        self.property_state_factory.get_property_state(**base_details_file_1)

        # Build out properties with increasingly more matching_criteria values
        base_details_file_1['pm_property_id'] = matching_pm_property_id
        self.property_state_factory.get_property_state(**base_details_file_1)
        base_details_file_1['address_line_1'] = matching_address_line_1
        self.property_state_factory.get_property_state(**base_details_file_1)
        base_details_file_1['ubid'] = matching_ubid
        self.property_state_factory.get_property_state(**base_details_file_1)
        base_details_file_1['custom_id_1'] = matching_custom_id_1
        self.property_state_factory.get_property_state(**base_details_file_1)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        geocode_and_match_buildings_task(self.import_file_1.id)

        # Verify no duplicates/matched-merges yet
        counts = [
            Property.objects.count(),
            PropertyState.objects.count(),
            PropertyView.objects.count(),
        ]
        self.assertEqual([5, 5, 5], counts)

        """
        For second file, create several properties that are one or many of the following:
            - 1 duplicates amongst file_1
            - 2 duplicates amongst file_2
            - 1 matching amongst file_1
            - 2 matching amongst file_2
            - 4 completely new
        """
        base_details_file_2 = {
            'import_file_id': self.import_file_2.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }

        # Create 1 duplicate of the 'No matching_criteria values' properties
        # (outcome: 1 additional -States, NO new Property/-View)
        ps_1 = self.property_state_factory.get_property_state(**base_details_file_2)

        # Create a non-duplicate property also having no matching criteria values
        # (outcome: 1 additional -States, 1 new Property/-View)
        base_details_file_2['postal_code'] = '01234'
        ps_2 = self.property_state_factory.get_property_state(**base_details_file_2)

        # Create 2 completely new properties with misaligned combinations of matching values
        # (outcome: 2 additional -States, 2 new Property/-View)
        base_details_file_2['custom_id_1'] = matching_custom_id_1
        ps_3 = self.property_state_factory.get_property_state(**base_details_file_2)
        base_details_file_2['ubid'] = matching_ubid
        ps_4 = self.property_state_factory.get_property_state(**base_details_file_2)

        # Create 3 properties - with 1 duplicate and 1 match within it's own file that will
        # eventually become 1 completely new property
        # (outcome: 4 additional -States, 1 new Property/-View)
        base_details_file_2['address_line_1'] = matching_address_line_1
        base_details_file_2['city'] = 'Denver'
        ps_5 = self.property_state_factory.get_property_state(**base_details_file_2)
        ps_6 = self.property_state_factory.get_property_state(**base_details_file_2)
        base_details_file_2['city'] = 'Golden'
        ps_7 = self.property_state_factory.get_property_state(**base_details_file_2)

        # Create 3 properties - with 1 duplicate and 1 match within it's own file that will
        # eventually match the last property in file_1
        # (outcome: 5 additional -States, NO new Property/-View)
        base_details_file_2['pm_property_id'] = matching_pm_property_id
        base_details_file_2['state'] = 'Colorado'
        ps_8 = self.property_state_factory.get_property_state(**base_details_file_2)
        ps_9 = self.property_state_factory.get_property_state(**base_details_file_2)
        base_details_file_2['state'] = 'California'
        ps_10 = self.property_state_factory.get_property_state(**base_details_file_2)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        geocode_and_match_buildings_task(self.import_file_2.id)

        self.assertEqual(9, Property.objects.count())
        self.assertEqual(9, PropertyView.objects.count())
        self.assertEqual(18, PropertyState.objects.count())

        ps_ids_of_deleted = PropertyState.objects.filter(
            data_state=DATA_STATE_DELETE
        ).values_list('id', flat=True).order_by('id')
        self.assertEqual(
            [ps_1.id, ps_6.id, ps_9.id],
            list(ps_ids_of_deleted)
        )

        ps_ids_of_merged_in_file = PropertyState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            merge_state=MERGE_STATE_UNKNOWN
        ).values_list('id', flat=True).order_by('id')
        self.assertEqual(
            [ps_5.id, ps_7.id, ps_8.id, ps_10.id],
            list(ps_ids_of_merged_in_file)
        )

        ps_ids_of_all_promoted = PropertyView.objects.values_list('state_id', flat=True)
        self.assertIn(ps_2.id, ps_ids_of_all_promoted)
        self.assertIn(ps_3.id, ps_ids_of_all_promoted)
        self.assertIn(ps_4.id, ps_ids_of_all_promoted)

        rimport_file_2 = ImportFile.objects.get(pk=self.import_file_2.id)
        results = rimport_file_2.matching_results_data
        del results['progress_key']

        expected = {
            'import_file_records': None,  # This is calculated in a separate process
            'property_duplicates_against_existing': 1,
            'property_duplicates_within_file': 2,
            'property_initial_incoming': 10,
            'property_merges_against_existing': 1,
            'property_merges_between_existing': 0,
            'property_merges_within_file': 2,
            'property_new': 4,
            'tax_lot_duplicates_against_existing': 0,
            'tax_lot_duplicates_within_file': 0,
            'tax_lot_initial_incoming': 0,
            'tax_lot_merges_against_existing': 0,
            'tax_lot_merges_between_existing': 0,
            'tax_lot_merges_within_file': 0,
            'tax_lot_new': 0,
        }
        self.assertEqual(results, expected)

    def test_taxlots(self):
        # Define matching values
        matching_jurisdiction_tax_lot_id = '11111'
        matching_address_line_1 = '123 Match Street'
        matching_ubid = '86HJPCWQ+2VV-1-3-2-3'
        matching_custom_id_1 = 'MatchingID12345'

        # For first file, create taxlots with no duplicates or matches
        base_details_file_1 = {
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }

        # No matching_criteria values
        self.taxlot_state_factory.get_taxlot_state(**base_details_file_1)

        # Build out taxlots with increasingly more matching_criteria values
        base_details_file_1['jurisdiction_tax_lot_id'] = matching_jurisdiction_tax_lot_id
        self.taxlot_state_factory.get_taxlot_state(**base_details_file_1)
        base_details_file_1['address_line_1'] = matching_address_line_1
        self.taxlot_state_factory.get_taxlot_state(**base_details_file_1)
        base_details_file_1['ubid'] = matching_ubid
        self.taxlot_state_factory.get_taxlot_state(**base_details_file_1)
        base_details_file_1['custom_id_1'] = matching_custom_id_1
        self.taxlot_state_factory.get_taxlot_state(**base_details_file_1)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        geocode_and_match_buildings_task(self.import_file_1.id)

        # Verify no duplicates/matched-merges yet
        counts = [
            TaxLot.objects.count(),
            TaxLotState.objects.count(),
            TaxLotView.objects.count(),
        ]
        self.assertEqual([5, 5, 5], counts)

        """
        For second file, create several taxlots that are one or many of the following:
            - 1 duplicates amongst file_1
            - 3 duplicates amongst file_2
            - 1 matching amongst file_1
            - 2 matching amongst file_2
            - 3 completely new
        """
        base_details_file_2 = {
            'import_file_id': self.import_file_2.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }

        # Create 2 duplicates of the 'No matching_criteria values' taxlots
        # (outcome: 2 additional -States, NO new TaxLot/-View)
        tls_1 = self.taxlot_state_factory.get_taxlot_state(**base_details_file_2)
        tls_2 = self.taxlot_state_factory.get_taxlot_state(**base_details_file_2)

        # Create 2 completely new taxlots with misaligned combinations of matching values
        # (outcome: 2 additional -States, 2 new TaxLot/-View)
        base_details_file_2['custom_id_1'] = matching_custom_id_1
        tls_3 = self.taxlot_state_factory.get_taxlot_state(**base_details_file_2)
        base_details_file_2['ubid'] = matching_ubid
        tls_4 = self.taxlot_state_factory.get_taxlot_state(**base_details_file_2)

        # Create 3 taxlots - with 1 duplicate and 1 match within it's own file that will
        # eventually become 1 completely new property
        # (outcome: 4 additional -States, 1 new TaxLot/-View)
        base_details_file_2['address_line_1'] = matching_address_line_1
        base_details_file_2['city'] = 'Denver'
        tls_5 = self.taxlot_state_factory.get_taxlot_state(**base_details_file_2)
        tls_6 = self.taxlot_state_factory.get_taxlot_state(**base_details_file_2)
        base_details_file_2['city'] = 'Golden'
        tls_7 = self.taxlot_state_factory.get_taxlot_state(**base_details_file_2)

        # Create 3 properties - with 1 duplicate and 1 match within it's own file that will
        # eventually match the last property in file_1
        # (outcome: 5 additional -States, NO new TaxLot/-View)
        base_details_file_2['jurisdiction_tax_lot_id'] = matching_jurisdiction_tax_lot_id
        base_details_file_2['state'] = 'Colorado'
        tls_8 = self.taxlot_state_factory.get_taxlot_state(**base_details_file_2)
        tls_9 = self.taxlot_state_factory.get_taxlot_state(**base_details_file_2)
        base_details_file_2['state'] = 'California'
        tls_10 = self.taxlot_state_factory.get_taxlot_state(**base_details_file_2)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        geocode_and_match_buildings_task(self.import_file_2.id)

        self.assertEqual(8, TaxLot.objects.count())
        self.assertEqual(8, TaxLotView.objects.count())
        self.assertEqual(18, TaxLotState.objects.count())

        tls_ids_of_deleted = TaxLotState.objects.filter(
            data_state=DATA_STATE_DELETE
        ).values_list('id', flat=True).order_by('id')
        self.assertEqual(
            [tls_1.id, tls_2.id, tls_6.id, tls_9.id],
            list(tls_ids_of_deleted)
        )

        tls_ids_of_merged_in_file = TaxLotState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            merge_state=MERGE_STATE_UNKNOWN
        ).values_list('id', flat=True).order_by('id')
        self.assertEqual(
            [tls_5.id, tls_7.id, tls_8.id, tls_10.id],
            list(tls_ids_of_merged_in_file)
        )

        tls_ids_of_all_promoted = TaxLotView.objects.values_list('state_id', flat=True)
        self.assertIn(tls_3.id, tls_ids_of_all_promoted)
        self.assertIn(tls_4.id, tls_ids_of_all_promoted)

        rimport_file_2 = ImportFile.objects.get(pk=self.import_file_2.id)
        results = rimport_file_2.matching_results_data
        del results['progress_key']

        expected = {
            'import_file_records': None,  # This is calculated in a separate process
            'property_duplicates_against_existing': 0,
            'property_duplicates_within_file': 0,
            'property_initial_incoming': 0,
            'property_merges_against_existing': 0,
            'property_merges_between_existing': 0,
            'property_merges_within_file': 0,
            'property_new': 0,
            'tax_lot_duplicates_against_existing': 1,
            'tax_lot_duplicates_within_file': 3,
            'tax_lot_initial_incoming': 10,
            'tax_lot_merges_against_existing': 1,
            'tax_lot_merges_between_existing': 0,
            'tax_lot_merges_within_file': 2,
            'tax_lot_new': 3,
        }
        self.assertEqual(results, expected)


class TestMatchingHelperMethods(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_save_state_match(self):
        # create a couple states to merge together
        ps_1 = self.property_state_factory.get_property_state(property_name="this should persist")
        ps_2 = self.property_state_factory.get_property_state(
            extra_data={"extra_1": "this should exist too"})

        priorities = Column.retrieve_priorities(self.org.pk)
        merged_state = save_state_match(ps_1, ps_2, priorities)

        self.assertEqual(merged_state.merge_state, MERGE_STATE_MERGED)
        self.assertEqual(merged_state.property_name, ps_1.property_name)
        self.assertEqual(merged_state.extra_data['extra_1'], "this should exist too")

        # verify that the audit log is correct.
        pal = PropertyAuditLog.objects.get(organization=self.org, state=merged_state)
        self.assertEqual(pal.name, 'System Match')
        self.assertEqual(pal.parent_state1, ps_1)
        self.assertEqual(pal.parent_state2, ps_2)
        self.assertEqual(pal.description, 'Automatic Merge')

    def test_filter_duplicate_states(self):
        for i in range(10):
            self.property_state_factory.get_property_state(
                no_default_data=True,
                address_line_1='123 The Same Address',
                # extra_data={"extra_1": "value_%s" % i},
                import_file_id=self.import_file.id,
                data_state=DATA_STATE_MAPPING,
            )
        for i in range(5):
            self.property_state_factory.get_property_state(
                import_file_id=self.import_file.id,
                data_state=DATA_STATE_MAPPING,
            )

        props = self.import_file.find_unmatched_property_states()
        sub_progress_data = ProgressData(func_name='match_sub_progress', unique_id=123)
        sub_progress_data.save()
        uniq_state_ids, dup_state_count = filter_duplicate_states(props, sub_progress_data.key)

        # There should be 6 uniq states. 5 from the second call, and one of 'The Same Address'
        self.assertEqual(len(uniq_state_ids), 6)
        self.assertEqual(dup_state_count, 9)


class TestBuildingSyncImportXml(DataMappingBaseTestCase):
    def setUp(self):
        self.maxDiff = None

        filename = 'buildingsync_v2_0_bricr_workflow.xml'
        filepath = osp.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', filename)

        import_file_source_type = BUILDINGSYNC_RAW
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file_bsync, self.import_record, self.cycle = selfvars

        self.import_file_bsync.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read(),
            content_type="application/xml"
        )
        self.import_file_bsync.uploaded_filename = filename
        self.import_file_bsync.save()

        self.import_record_2, self.import_file_2 = self.create_import_file(
            self.user, self.org, self.cycle
        )

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

    def map_bsync_file(self):
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            progress_info = save_raw_data(self.import_file_bsync.pk)
        self.assertEqual('success', progress_info['status'], json.dumps(progress_info))
        self.assertEqual(PropertyState.objects.filter(import_file=self.import_file_bsync).count(), 1)

        # make the column mappings
        self.fake_mappings = default_buildingsync_profile_mappings()
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file_bsync.pk)

        # map the data
        progress_info = map_data(self.import_file_bsync.pk)
        self.assertEqual('success', progress_info['status'])
        # verify there were no errors with the files
        self.assertEqual({}, progress_info.get('file_info', {}))

    def test_match_buildingsync_works_when_no_existing_scenarios_or_meters(self):
        """If a BuildingSync file is merged into an existing property WITHOUT scenarios and meters,
        we expect the final property to have only the new scenarios and meters"""
        # -- Setup
        # make address_line_1 the only matching criteria
        (
            Column.objects.filter(is_matching_criteria=True)
            .exclude(column_name='address_line_1')
            .update(is_matching_criteria=False)
        )
        # this should be the address in the BSync file
        ADDRESS_LINE_1 = '123 MAIN BLVD'
        base_details = {
            'address_line_1': ADDRESS_LINE_1,
            'import_file_id': self.import_file_2.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create a property which will match with the BuildingSync file
        self.property_state_factory.get_property_state(**base_details)
        # set import_file mapping done so that matching can occur.
        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        geocode_and_match_buildings_task(self.import_file_2.id)

        # Map the BuildingSync file which should match with the existing property
        self.map_bsync_file()
        ps_new = PropertyState.objects.filter(
            address_line_1=ADDRESS_LINE_1,
            import_file=self.import_file_bsync
        )
        self.assertEqual(len(ps_new), 1)

        # -- Act
        geocode_and_match_buildings_task(self.import_file_bsync.id)

        # -- Assert
        # we should end up with only one view b/c the bsync file was merged into the existing property
        self.assertEqual(PropertyView.objects.count(), 1)
        pv = PropertyView.objects.all().first()

        # the bsync file's scenarios should end up on our property view
        ps = pv.state
        scenario = Scenario.objects.filter(property_state=ps)
        self.assertEqual(scenario.count(), 3)

        pms = PropertyMeasure.objects.filter(property_state=ps, recommended=False)
        self.assertEqual(pms.count(), 1)
        pms = PropertyMeasure.objects.filter(property_state=ps, recommended=True)
        self.assertEqual(pms.count(), 70)

        meters = Meter.objects.filter(scenario__in=scenario)
        self.assertEqual(meters.count(), 6)

    def test_match_buildingsync_works_when_there_are_existing_different_scenarios_and_meters(self):
        """If a BuildingSync file is merged into an existing property with scenarios and meters
        that differ from the ones in the file, we expect the final property to have only the new scenarios and meters"""
        # -- Setup
        # make address_line_1 the only matching criteria
        (
            Column.objects.filter(is_matching_criteria=True)
            .exclude(column_name='address_line_1')
            .update(is_matching_criteria=False)
        )
        # this should be the address in the BSync file
        ADDRESS_LINE_1 = '123 MAIN BLVD'
        base_details = {
            'address_line_1': ADDRESS_LINE_1,
            'import_file_id': self.import_file_2.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create a property which will match with the BuildingSync file
        ps_orig = self.property_state_factory.get_property_state(**base_details)
        # set import_file mapping done so that matching can occur.
        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        geocode_and_match_buildings_task(self.import_file_2.id)
        # add scenario, measure, and meter
        scenario = Scenario.objects.create(
            name='My Original Scenario',
            property_state_id=ps_orig.id,
        )
        PropertyMeasure.objects.create(
            property_measure_name='My Original PropertyMeasure',
            measure_id=Measure.objects.filter(organization=self.org).first().id,
            property_state_id=ps_orig.id
        )
        meter = Meter.objects.create(
            scenario_id=scenario.id,
            source_id='My Original Meter',
        )
        MeterReading.objects.create(
            start_time=datetime.now(tz=pytz.UTC),
            end_time=datetime.now(tz=pytz.UTC),
            reading=123,
            meter_id=meter.id,
            conversion_factor=1,
        )

        # Map the BuildingSync file which should match with the existing property
        self.map_bsync_file()
        ps_new = PropertyState.objects.filter(
            address_line_1=ADDRESS_LINE_1,
            import_file=self.import_file_bsync
        )
        self.assertEqual(len(ps_new), 1)

        # -- Act
        geocode_and_match_buildings_task(self.import_file_bsync.id)

        # -- Assert
        # we should end up with only one view b/c the bsync file was merged into the existing property
        self.assertEqual(PropertyView.objects.count(), 1)
        pv = PropertyView.objects.all().first()

        num_bsync_scenarios = 3
        ps = pv.state
        scenario = Scenario.objects.filter(property_state=ps)
        self.assertEqual(scenario.count(), num_bsync_scenarios)

        num_bsync_measures = 71
        pms = PropertyMeasure.objects.filter(property_state=ps)
        self.assertEqual(pms.count(), num_bsync_measures)

        num_bsync_meters = 6
        meters = Meter.objects.filter(scenario__in=scenario)
        self.assertEqual(meters.count(), num_bsync_meters)


class TestMultiCycleImport(DataMappingBaseTestCase):

    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

        # Create cycles
        self.cycle2010_2014, _ = Cycle.objects.get_or_create(
            name='Test Cycle 2010 to 2014',
            organization=self.org,
            start=date(2010, 1, 1),
            end=date(2014, 12, 31),
        )
        self.cycle2018, _ = Cycle.objects.get_or_create(
            name='Test Cycle 2018',
            organization=self.org,
            start=date(2018, 1, 1),
            end=date(2018, 12, 31),
        )
        self.cycle2019, _ = Cycle.objects.get_or_create(
            name='Test Cycle 2019',
            organization=self.org,
            start=date(2019, 1, 1),
            end=date(2019, 12, 31),
        )
        self.cycle2020, _ = Cycle.objects.get_or_create(
            name='Test Cycle 2020',
            organization=self.org,
            start=date(2020, 1, 1),
            end=date(2020, 12, 31),
        )
        self.cycle2021, _ = Cycle.objects.get_or_create(
            name='Test Cycle 2021',
            organization=self.org,
            start=date(2021, 1, 1),
            end=date(2021, 12, 31),
        )
        self.cycle2022_april, _ = Cycle.objects.get_or_create(
            name='Test Cycle 2022',
            organization=self.org,
            start=date(2022, 4, 1),
            end=date(2023, 4, 1),
        )
        # Default cycle will be the first returned for an org (aka the most recent)
        self.cycle_default, _ = Cycle.objects.get_or_create(
            name='Default Cycle',
            organization=self.org,
            start=date(1999, 1, 1),
            end=date(1999, 12, 31),
        )

        base_details = {'import_file_id': self.import_file.id}
        # Properties for cycle 2010_2014
        base_details['property_name'] = 'p2010_2014a'
        base_details['year_ending'] = date(2012, 12, 12)
        self.property_state_factory.get_property_state(**base_details)

        base_details['property_name'] = 'p2010_2014b'
        base_details['year_ending'] = date(2010, 10, 10)
        self.property_state_factory.get_property_state(**base_details)

        base_details['property_name'] = 'p2010_2014c'
        base_details['year_ending'] = date(2014, 10, 15)
        self.property_state_factory.get_property_state(**base_details)

        # Properties for cycle 2018
        base_details['property_name'] = 'p2018a'
        base_details['year_ending'] = date(2018, 12, 31)
        self.property_state_factory.get_property_state(**base_details)

        base_details['property_name'] = 'p2018b'
        base_details['year_ending'] = date(2018, 6, 15)
        self.property_state_factory.get_property_state(**base_details)

        # Properties for cycle 2019
        base_details['property_name'] = 'p2019a'
        base_details['year_ending'] = date(2019, 12, 31)
        self.property_state_factory.get_property_state(**base_details)

        base_details['property_name'] = 'p2019b'
        base_details['year_ending'] = date(2019, 6, 15)
        self.property_state_factory.get_property_state(**base_details)

        # Properties for cycle 2020
        base_details['property_name'] = 'p2020a'
        base_details['year_ending'] = date(2020, 12, 31)
        self.property_state_factory.get_property_state(**base_details)

        base_details['property_name'] = 'p2020b'
        base_details['year_ending'] = date(2020, 12, 30)
        self.property_state_factory.get_property_state(**base_details)

        # Properties for cycle 2021
        base_details['property_name'] = 'p2021a'
        base_details['year_ending'] = date(2021, 1, 1)
        self.property_state_factory.get_property_state(**base_details)

        base_details['property_name'] = 'p2021b'
        base_details['year_ending'] = date(2021, 12, 31)
        self.property_state_factory.get_property_state(**base_details)

        # Properties for cycle 2022 april
        base_details['property_name'] = 'p2022a'
        base_details['year_ending'] = date(2022, 5, 1)
        self.property_state_factory.get_property_state(**base_details)

        base_details['property_name'] = 'p2022b'
        base_details['year_ending'] = date(2023, 3, 1)
        self.property_state_factory.get_property_state(**base_details)

        # Properties with year_ending that do not match any cycles will be placed in default cycle
        base_details['property_name'] = 'p_default_a'
        base_details['year_ending'] = date(1990, 5, 25)
        self.property_state_factory.get_property_state(**base_details)

        base_details['property_name'] = 'p_default_b'
        base_details['year_ending'] = date(2023, 4, 10)
        self.property_state_factory.get_property_state(**base_details)

        # Properties with missing year_ending will be placed in default cycle
        base_details['property_name'] = 'p_default_c'
        base_details.pop('year_ending')
        self.property_state_factory.get_property_state(**base_details)

        # Set multiple_cycle_upload to True to trigger MultiCycle import
        self.import_file.cycle = self.cycle_default
        self.import_file.multiple_cycle_upload = True
        self.import_file.mapping_done = True
        self.import_file.save()

    def test_multi_cycle_import(self):
        geocode_and_match_buildings_task(self.import_file.id)

        def get_cycle(ps):
            return ps.propertyview_set.first().cycle

        p2010_2014a = PropertyState.objects.get(property_name='p2010_2014a')
        p2010_2014b = PropertyState.objects.get(property_name='p2010_2014b')
        p2010_2014c = PropertyState.objects.get(property_name='p2010_2014c')
        p2018a = PropertyState.objects.get(property_name='p2018a')
        p2018b = PropertyState.objects.get(property_name='p2018b')
        p2019a = PropertyState.objects.get(property_name='p2019a')
        p2019b = PropertyState.objects.get(property_name='p2019b')
        p2020a = PropertyState.objects.get(property_name='p2020a')
        p2020b = PropertyState.objects.get(property_name='p2020b')
        p2021a = PropertyState.objects.get(property_name='p2021a')
        p2021b = PropertyState.objects.get(property_name='p2021b')
        p2022a = PropertyState.objects.get(property_name='p2022a')
        p2022b = PropertyState.objects.get(property_name='p2022b')
        p_default_a = PropertyState.objects.get(property_name='p_default_a')
        p_default_b = PropertyState.objects.get(property_name='p_default_b')
        p_default_c = PropertyState.objects.get(property_name='p_default_c')

        self.assertEqual(get_cycle(p2010_2014a), self.cycle2010_2014)
        self.assertEqual(get_cycle(p2010_2014b), self.cycle2010_2014)
        self.assertEqual(get_cycle(p2010_2014c), self.cycle2010_2014)
        self.assertEqual(get_cycle(p2018a), self.cycle2018)
        self.assertEqual(get_cycle(p2018b), self.cycle2018)
        self.assertEqual(get_cycle(p2019a), self.cycle2019)
        self.assertEqual(get_cycle(p2019b), self.cycle2019)
        self.assertEqual(get_cycle(p2020a), self.cycle2020)
        self.assertEqual(get_cycle(p2020b), self.cycle2020)
        self.assertEqual(get_cycle(p2021a), self.cycle2021)
        self.assertEqual(get_cycle(p2021b), self.cycle2021)
        self.assertEqual(get_cycle(p2022a), self.cycle2022_april)
        self.assertEqual(get_cycle(p2022b), self.cycle2022_april)
        self.assertEqual(get_cycle(p_default_a), self.cycle_default)
        self.assertEqual(get_cycle(p_default_b), self.cycle_default)
        self.assertEqual(get_cycle(p_default_c), self.cycle_default)

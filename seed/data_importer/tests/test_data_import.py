# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import datetime
import logging
from unittest import skip

from dateutil import parser
from django.test import TestCase
from mock import patch

from seed.data_importer import tasks
from seed.data_importer.models import ImportFile
from seed.data_importer.tests import util as test_util
from seed.models import (
    ASSESSED_RAW,
    ASSESSED_BS,
    PORTFOLIO_BS,
    POSSIBLE_MATCH,
    SYSTEM_MATCH,
    DATA_STATE_IMPORT,
    Cycle,
    PropertyState,
    PropertyView,
    Column,
    get_ancestors,
    DATA_STATE_MAPPING
)
from seed.tests import util

logger = logging.getLogger(__name__)


class TestMapping(TestCase):
    """Tests for dealing with SEED related tasks for mapping data."""

    def setUp(self):
        # Make sure to delete the old mappings and properties because this
        # tests expects very specific column names and properties in order
        test_util.load_test_data(self, 'portfolio-manager-sample.csv')

    def test_cached_first_row_order(self):
        """Tests to make sure the first row is saved in the correct order.  It should be the order of the headers in the original file."""
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            tasks._save_raw_data(
                self.import_file.pk,
                'fake_cache_key',
                1
            )
        expected_first_row = u"Property Id|#*#|Property Name|#*#|Year Ending|#*#|Property Floor Area (Buildings and Parking) (ft2)|#*#|Address 1|#*#|Address 2|#*#|City|#*#|State/Province|#*#|Postal Code|#*#|Year Built|#*#|ENERGY STAR Score|#*#|Site EUI (kBtu/ft2)|#*#|Total GHG Emissions (MtCO2e)|#*#|Weather Normalized Site EUI (kBtu/ft2)|#*#|National Median Site EUI (kBtu/ft2)|#*#|Source EUI (kBtu/ft2)|#*#|Weather Normalized Source EUI (kBtu/ft2)|#*#|National Median Source EUI (kBtu/ft2)|#*#|Parking - Gross Floor Area (ft2)|#*#|Organization|#*#|Generation Date|#*#|Release Date"

        import_file = ImportFile.objects.get(pk=self.import_file.pk)
        first_row = import_file.cached_first_row
        self.assertEqual(first_row, expected_first_row)

    def test_save_raw_data(self):
        """Save information in extra_data, set other attrs."""
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            tasks._save_raw_data(
                self.import_file.pk,
                'fake_cache_key',
                1
            )

        raw_saved = PropertyState.objects.filter(
            import_file=self.import_file,
        ).latest('id')

        self.assertDictEqual(raw_saved.extra_data, self.fake_extra_data)
        self.assertEqual(raw_saved.super_organization, self.fake_org)

    def test_map_data(self):
        """Save mappings based on user specifications."""
        fake_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            raw_save_done=True
        )
        fake_raw_bs = PropertyState.objects.create(
            import_file=fake_import_file,
            extra_data=self.fake_row,
            source_type=ASSESSED_RAW,
            data_state=DATA_STATE_IMPORT,
        )

        util.make_fake_mappings(self.fake_mappings, self.fake_org)

        tasks.map_data(fake_import_file.pk)

        mapped_bs = list(PropertyState.objects.filter(
            import_file=fake_import_file,
            source_type=ASSESSED_BS,
        ))

        self.assertEqual(len(mapped_bs), 1)

        test_bs = mapped_bs[0]

        self.assertNotEqual(test_bs.pk, fake_raw_bs.pk)
        self.assertEqual(test_bs.property_name, self.fake_row['Name'])
        self.assertEqual(
            test_bs.address_line_1, self.fake_row['Address Line 1']
        )
        self.assertEqual(
            test_bs.year_built,
            parser.parse(self.fake_row['Year Built']).year
        )

        # Make sure that we saved the extra_data column mappings
        data_columns = Column.objects.filter(
            organization=test_bs.super_organization,
            is_extra_data=True
        )

        # There's only one peice of data that didn't cleanly map
        self.assertListEqual(
            sorted([d.column_name for d in data_columns]), ['Double Tester']
        )

    def test_mapping_w_concat(self):
        """When we have a json encoded list as a column mapping, we concat."""
        fake_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            raw_save_done=True
        )
        self.fake_row['City'] = 'Someplace Nice'
        PropertyState.objects.create(
            import_file=fake_import_file,
            source_type=ASSESSED_RAW,
            extra_data=self.fake_row,
            data_state=DATA_STATE_IMPORT,
        )

        self.fake_mappings['address_line_1'] = ['Address Line 1', 'City']
        util.make_fake_mappings(self.fake_mappings, self.fake_org)

        tasks.map_data(fake_import_file.pk)

        mapped_bs = list(PropertyState.objects.filter(
            import_file=fake_import_file,
            source_type=ASSESSED_BS,
        ))[0]

        self.assertEqual(
            mapped_bs.address_line_1, u'1600 Pennsylvania Ave. Someplace Nice'
        )


class TestPromotingProperties(TestCase):
    def setUp(self):
        test_util.import_exported_test_data(self, 'propertystates-one-cycle.csv')

    def test_promote_properties(self):
        """Good case for testing our matching system."""

        cycle, _ = Cycle.objects.get_or_create(
            name=u'Hack Cycle 2015',
            organization=self.fake_org,
            start=datetime.datetime(2015, 1, 1),
            end=datetime.datetime(2015, 12, 31),
        )

        cycle2, _ = Cycle.objects.get_or_create(
            name=u'Hack Cycle 2016',
            organization=self.fake_org,
            start=datetime.datetime(2016, 1, 1),
            end=datetime.datetime(2016, 12, 31),
        )

        # make sure that the new data was loaded correctly
        ps = PropertyState.objects.filter(address_line_1='1181 Douglas Street')[0]
        self.assertEqual(ps.site_eui, 439.9)
        self.assertEqual(ps.extra_data['CoStar Property ID'], '1575599')

        # Promote the PropertyState to a PropertyView
        pv1 = ps.promote(cycle)
        pv2 = ps.promote(cycle)  # should just return the same object
        self.assertEqual(pv1, pv2)

        # promote the same state for a new cycle, same data
        pv3 = ps.promote(cycle2)
        self.assertNotEqual(pv3, pv1)

        props = PropertyView.objects.all()
        self.assertEqual(len(props), 2)


# @skip("Fix for new data model")
class TestMatching(TestCase):
    """Tests for dealing with SEED related tasks for matching data."""

    def setUp(self):
        test_util.import_example_data(self, 'example-data-properties.xlsx')

    def test_is_same_snapshot(self):
        """Test to check if two snapshots are duplicates"""

        # TODO: Fix the PM, tax lot id, and custom ID fields in PropertyState
        bs_data = {
            # 'pm_property_id': 1243,
            # 'tax_lot_id': '435/422',
            'property_name': 'Greenfield Complex',
            # 'custom_id_1': 12,
            'address_line_1': '555 Database LN.',
            'address_line_2': '',
            'city': 'Gotham City',
            'postal_code': 8999,
        }

        s1 = util.make_fake_property(self.import_file, bs_data, ASSESSED_BS, is_canon=True,
                                     org=self.fake_org)

        self.assertTrue(tasks.is_same_snapshot(s1, s1),
                        "Matching a snapshot to itself should return True")

        # Making a different snapshot, now Garfield complex rather than Greenfield complex
        bs_data_2 = {
            # 'pm_property_id': 1243,
            # 'tax_lot_id': '435/422',
            'property_name': 'Garfield Complex',
            # 'custom_id_1': 12,
            'address_line_1': '555 Database LN.',
            'address_line_2': '',
            'city': 'Gotham City',
            'postal_code': 8999,
        }

        s2 = util.make_fake_property(self.import_file, bs_data_2, ASSESSED_BS, is_canon=True,
                                     org=self.fake_org)

        self.assertFalse(tasks.is_same_snapshot(s1, s2),
                         "Matching a snapshot to a different snapshot should return False")

    def test_match_buildings(self):
        """Good case for testing our matching system."""

        cycle, _ = Cycle.objects.get_or_create(
            name=u'Test Hack Cycle 2015',
            organization=self.fake_org,
            start=datetime.datetime(2015, 1, 1),
            end=datetime.datetime(2015, 12, 31),
        )

        ps = PropertyState.objects.filter(data_state=DATA_STATE_MAPPING,
                                          super_organization=self.fake_org)

        # Promote case A (one property <-> one tax lot)
        ps = PropertyState.objects.filter(building_portfolio_manager_identifier=2264)[0]

        ps.promote(cycle)

        ps = tasks.get_canonical_snapshots(self.fake_org)
        from django.db.models.query import QuerySet
        self.assertTrue(isinstance(ps, QuerySet))
        logger.debug("There are %s properties" % len(ps))
        for p in ps:
            from seed.utils.generic import pp
            pp(p)

        self.assertEqual(len(ps), 1)
        self.assertEqual(ps[0].address_line_1, '50 Willow Ave SE')


        # # Promote 5 of these to views to test the remaining code
        # promote_mes = PropertyState.objects.filter(
        #     data_state=DATA_STATE_MAPPING,
        #     super_organization=self.fake_org)[:5]
        # for promote_me in promote_mes:
        #     promote_me.promote(cycle)
        #
        # ps = tasks.get_canonical_snapshots(self.fake_org)
        # from django.db.models.query import QuerySet
        # self.assertTrue(isinstance(ps, QuerySet))
        # logger.debug("There are %s properties" % len(ps))
        # for p in ps:
        #     print p
        #
        # self.assertEqual(len(ps), 5)
        # self.assertEqual(ps[0].address_line_1, '1211 Bryant Street')
        # self.assertEqual(ps[4].address_line_1, '1031 Ellis Lane')

        # tasks.match_buildings(self.import_file.pk, self.fake_user.pk)

        # self.assertEqual(result.property_name, snapshot.property_name)
        # self.assertEqual(result.property_name, new_snapshot.property_name)
        # # Since these two buildings share a common ID, we match that way.
        # # self.assertEqual(result.confidence, 0.9)
        # self.assertEqual(
        #     sorted([r.pk for r in result.parents.all()]),
        #     sorted([new_snapshot.pk, snapshot.pk])
        # )
        # self.assertGreater(AuditLog.objects.count(), 0)
        # self.assertEqual(
        #     AuditLog.objects.first().action_note,
        #     'System matched building ID.'
        # )

    @skip("Fix for new data model")
    def test_match_duplicate_buildings(self):
        """
        Test for behavior when trying to match duplicate building data
        """
        # TODO: Fix the PM, tax lot id, and custom ID fields in PropertyState
        bs_data = {
            # 'pm_property_id': "8450",
            # 'tax_lot_id': '143/292',
            'property_name': 'Greenfield Complex',
            # 'custom_id_1': "99",
            'address_line_1': '93754 Database LN.',
            'address_line_2': '',
            'city': 'Gotham City',
            'postal_code': "8999",
        }

        import_file = ImportFile.objects.create(
            import_record=self.import_record,
            mapping_done=True
        )

        # Setup mapped PM snapshot.
        util.make_fake_property(
            import_file, bs_data, PORTFOLIO_BS, is_canon=True,
            org=self.fake_org
        )
        # Different file, but same ImportRecord.
        # Setup mapped PM snapshot.
        # Should be a duplicate.
        new_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            mapping_done=True
        )

        util.make_fake_property(
            new_import_file, bs_data, PORTFOLIO_BS, org=self.fake_org
        )

        tasks.match_buildings(import_file.pk, self.fake_user.pk)
        tasks.match_buildings(new_import_file.pk, self.fake_user.pk)

        self.assertEqual(len(PropertyState.objects.all()), 2)

    @skip("Fix for new data model")
    def test_handle_id_matches_duplicate_data(self):
        """
        Test for handle_id_matches behavior when matching duplicate data
        """
        # TODO: Fix the PM, tax lot id, and custom ID fields in PropertyState
        bs_data = {
            # 'pm_property_id': "2360",
            # 'tax_lot_id': '476/460',
            'property_name': 'Garfield Complex',
            # 'custom_id_1': "89",
            'address_line_1': '12975 Database LN.',
            'address_line_2': '',
            'city': 'Cartoon City',
            'postal_code': "54321",
        }

        # Setup mapped AS snapshot.
        util.make_fake_property(
            self.import_file, bs_data, ASSESSED_BS, is_canon=True,
            org=self.fake_org
        )

        # Different file, but same ImportRecord.
        # Setup mapped PM snapshot.
        # Should be an identical match.
        new_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            mapping_done=True
        )

        tasks.match_buildings(new_import_file.pk, self.fake_user.pk)

        duplicate_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            mapping_done=True
        )

        new_snapshot = util.make_fake_property(
            duplicate_import_file, bs_data, PORTFOLIO_BS, org=self.fake_org
        )

        self.assertRaises(tasks.DuplicateDataError, tasks.handle_id_matches,
                          new_snapshot, duplicate_import_file,
                          self.fake_user.pk)

    @skip("Fix for new data model")
    def test_match_no_matches(self):
        """When a canonical exists, but doesn't match, we create a new one."""
        # TODO: Fix the PM, tax lot id, and custom ID fields in PropertyState
        bs1_data = {
            # 'pm_property_id': 1243,
            # 'tax_lot_id': '435/422',
            'property_name': 'Greenfield Complex',
            # 'custom_id_1': 1243,
            'address_line_1': '555 Database LN.',
            'address_line_2': '',
            'city': 'Gotham City',
            'postal_code': 8999,
        }

        bs2_data = {
            # 'pm_property_id': 9999,
            # 'tax_lot_id': '1231',
            'property_name': 'A Place',
            # 'custom_id_1': 0o000111000,
            'address_line_1': '44444 Hmmm Ave.',
            'address_line_2': 'Apt 4',
            'city': 'Gotham City',
            'postal_code': 8999,
        }

        snapshot = util.make_fake_property(
            self.import_file, bs1_data, ASSESSED_BS, is_canon=True
        )
        new_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            mapping_done=True
        )
        new_snapshot = util.make_fake_property(
            new_import_file, bs2_data, PORTFOLIO_BS, org=self.fake_org
        )

        self.assertEqual(PropertyState.objects.all().count(), 2)

        tasks.match_buildings(new_import_file.pk, self.fake_user.pk)

        # E.g. we didn't create a match
        self.assertEqual(PropertyState.objects.all().count(), 2)
        latest_snapshot = PropertyState.objects.get(pk=new_snapshot.pk)

        # But we did create another canonical building for the unmatched bs.
        self.assertNotEqual(latest_snapshot.canonical_building, None)
        self.assertNotEqual(
            latest_snapshot.canonical_building.pk,
            snapshot.canonical_building.pk
        )

        self.assertEqual(latest_snapshot.confidence, None)

    @skip("Fix for new data model")
    def test_match_no_canonical_buildings(self):
        """If no canonicals exist, create, but no new PropertyStates."""
        bs1_data = {
            'pm_property_id': 1243,
            'tax_lot_id': '435/422',
            'property_name': 'Greenfield Complex',
            'custom_id_1': 1243,
            'address_line_1': '555 Database LN.',
            'address_line_2': '',
            'city': 'Gotham City',
            'postal_code': 8999,
        }

        # Note: no Canonical Building is created for this snapshot.
        snapshot = util.make_fake_property(
            self.import_file, bs1_data, ASSESSED_BS, is_canon=False,
            org=self.fake_org
        )

        self.import_file.mapping_done = True
        self.import_file.save()

        self.assertEqual(snapshot.canonical_building, None)
        self.assertEqual(PropertyState.objects.all().count(), 1)

        tasks.match_buildings(self.import_file.pk, self.fake_user.pk)

        refreshed_snapshot = PropertyState.objects.get(pk=snapshot.pk)
        self.assertNotEqual(refreshed_snapshot.canonical_building, None)
        self.assertEqual(PropertyState.objects.all().count(), 1)

    @skip("Fix for new data model")
    def test_no_unmatched_buildings(self):
        """Make sure we shortcut out if there isn't unmatched data."""
        bs1_data = {
            'pm_property_id': 1243,
            'tax_lot_id': '435/422',
            'property_name': 'Greenfield Complex',
            'custom_id_1': 1243,
            'address_line_1': '555 Database LN.',
            'address_line_2': '',
            'city': 'Gotham City',
            'postal_code': 8999,
        }

        self.import_file.mapping_done = True
        self.import_file.save()
        util.make_fake_property(
            self.import_file, bs1_data, ASSESSED_BS, is_canon=True
        )

        self.assertEqual(PropertyState.objects.all().count(), 1)

        tasks.match_buildings(self.import_file.pk, self.fake_user.pk)

        self.assertEqual(PropertyState.objects.all().count(), 1)

    @skip("Fix for new data model")
    def test_separates_system_and_possible_match_types(self):
        """We save possible matches separately."""
        bs1_data = {
            'pm_property_id': 123,
            'tax_lot_id': '435/422',
            'property_name': 'Greenfield Complex',
            'custom_id_1': 1243,
            'address_line_1': '555 NorthWest Databaseer Lane.',
            'address_line_2': '',
            'city': 'Gotham City',
            'postal_code': 8999,
        }
        # This building will have a lot less data to identify it.
        bs2_data = {
            'pm_property_id': 1243,
            'custom_id_1': 1243,
            'address_line_1': '555 Database LN.',
            'city': 'Gotham City',
            'postal_code': 8999,
        }
        new_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            mapping_done=True
        )

        util.make_fake_property(
            self.import_file, bs1_data, ASSESSED_BS, is_canon=True,
            org=self.fake_org
        )

        util.make_fake_property(
            new_import_file, bs2_data, PORTFOLIO_BS, org=self.fake_org
        )

        tasks.match_buildings(new_import_file.pk, self.fake_user.pk)

        self.assertEqual(
            PropertyState.objects.filter(match_type=POSSIBLE_MATCH).count(),
            0
        )
        self.assertEqual(
            PropertyState.objects.filter(match_type=SYSTEM_MATCH).count(),
            1
        )

    # Will be obsolete
    @skip("Fix for new data model")
    def test_get_ancestors(self):
        """Tests get_ancestors(building), returns all non-composite, non-raw
            PropertyState instances.
        """
        bs_data = {
            'pm_property_id': 1243,
            'tax_lot_id': '435/422',
            'property_name': 'Greenfield Complex',
            'custom_id_1': 1243,
            'address_line_1': '555 Database LN.',
            'address_line_2': '',
            'city': 'Gotham City',
            'postal_code': 8999,
        }

        # Since we changed to not match duplicate data make a second record that matches with something slighty changed
        # In this case appended a 'A' to the end of address_line_1
        bs_data_2 = {
            'pm_property_id': 1243,
            'tax_lot_id': '435/422',
            'property_name': 'Greenfield Complex',
            'custom_id_1': 1243,
            'address_line_1': '555 Database LN. A',
            'address_line_2': '',
            'city': 'Gotham City',
            'postal_code': 8999,
        }

        # Setup mapped AS snapshot.
        util.make_fake_property(
            self.import_file, bs_data, ASSESSED_BS, is_canon=True,
            org=self.fake_org
        )
        # Different file, but same ImportRecord.
        # Setup mapped PM snapshot.
        # Should be an identical match.
        new_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            raw_save_done=True,
            mapping_done=True
        )

        util.make_fake_property(
            new_import_file, bs_data_2, PORTFOLIO_BS, org=self.fake_org
        )

        tasks.match_buildings(new_import_file.pk, self.fake_user.pk)

        result = PropertyState.objects.filter(source_type=4)[0]
        ancestor_pks = set([b.pk for b in get_ancestors(result)])
        buildings = PropertyState.objects.filter(
            source_type__in=[2, 3]
        ).exclude(
            pk=result.pk
        )
        building_pks = set([b.pk for b in buildings])

        self.assertEqual(ancestor_pks, building_pks)

    @skip("Fix for new data model")
    def test_save_raw_data_batch_iterator(self):
        """Ensure split_csv completes"""
        tasks.save_raw_data(self.import_file.pk)

        self.assertEqual(PropertyState.objects.filter(
            import_file=self.import_file
        ).count(), 512)


# TODO: inherit from TestMatching once this is fixed
class TestTasksXLS(TestMapping):
    """Runs the TestTasks tests with an XLS file"""

    def setUp(self):
        test_util.load_test_data(self, 'portfolio-manager-sample.xls')
        # Make the field match on an integer because XLS mapping handles casting
        self.fake_extra_data['Property Id'] = 101125


class TestTasksXLSX(TestMapping):
    """Runs the TestsTasks tests with an XLSX file."""

    def setUp(self):
        test_util.load_test_data(self, 'portfolio-manager-sample.xlsx')
        # Make the field match on an integer because XLS mapping handles casting
        self.fake_extra_data['Property Id'] = 101125

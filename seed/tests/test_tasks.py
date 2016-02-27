# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from os import path
import logging

from dateutil import parser

from mock import patch
from django.test import TestCase
from django.core.files import File
from seed.audit_logs.models import AuditLog
from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import (
    ASSESSED_RAW,
    ASSESSED_BS,
    PORTFOLIO_BS,
    POSSIBLE_MATCH,
    SYSTEM_MATCH,
    FLOAT,
    BuildingSnapshot,
    CanonicalBuilding,
    Column,
    ColumnMapping,
    Unit,
    get_ancestors,
)
from seed import tasks
from seed.tests import util

logger = logging.getLogger(__name__)

class TestCleaner(TestCase):
    """Tests that our logic for constructing cleaners works."""

    def setUp(self):
        self.org = Organization.objects.create()

        unit = Unit.objects.create(
            unit_name='mapped_col unit',
            unit_type=FLOAT,
        )

        raw = Column.objects.create(
            column_name='raw_col',
            organization=self.org,
        )

        self.mapped_col = 'mapped_col'
        mapped = Column.objects.create(
            column_name=self.mapped_col,
            unit=unit,
            organization=self.org,
        )

        mapping = ColumnMapping.objects.create(
            super_organization=self.org
        )
        mapping.column_raw.add(raw)
        mapping.column_mapped.add(mapped)


    def test_build_cleaner(self):
        cleaner = tasks._build_cleaner(self.org)

        # data is cleaned correctly for fields on BuildingSnapshot
        # model
        bs_field = 'gross_floor_area'
        self.assertEqual(
            cleaner.clean_value('123,456', bs_field),
            123456
        )

        # data is cleaned correctly for mapped fields that have unit
        # type information
        self.assertEqual(
            cleaner.clean_value('123,456', self.mapped_col),
            123456
        )

        # other fields are just strings
        self.assertEqual(
            cleaner.clean_value('123,456', 'random'),
            '123,456'
        )


class TestTasks(TestCase):
    """Tests for dealing with SEED related tasks."""

    def setUp(self):
        self.fake_user = User.objects.create(username='test')
        self.import_record = ImportRecord.objects.create(
            owner=self.fake_user,
        )
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record
        )
        self.import_file.is_espm = True
        self.import_file.source_type = 'PORTFOLIO_RAW'
        self.import_file.file = File(
            open(
                path.join(
                    path.dirname(__file__),
                    'data',
                    'portfolio-manager-sample.csv'
                )
            )
        )
        self.import_file.save()

        # Mimic the representation in the PM file. #ThanksAaron
        self.fake_extra_data = {
            u'City': u'EnergyTown',
            u'ENERGY STAR Score': u'',
            u'State/Province': u'Ilinois', # typo on purpose? The entire pm file has this as well.
            u'Site EUI (kBtu/ft2)': u'',
            u'Year Ending': u'',
            u'Weather Normalized Source EUI (kBtu/ft2)': u'',
            u'Parking - Gross Floor Area (ft2)': u'',
            u'Address 1': u'000015581 SW Sycamore Court',
            u'Property Id': u'101125',
            u'Address 2': u'Not Available',
            u'Source EUI (kBtu/ft2)': u'',
            u'Release Date': u'',
            u'National Median Source EUI (kBtu/ft2)': u'',
            u'Weather Normalized Site EUI (kBtu/ft2)': u'',
            u'National Median Site EUI (kBtu/ft2)': u'',
            u'Year Built': u'',
            u'Postal Code': u'10108-9812',
            u'Organization': u'Occidental Management',
            u'Property Name': u'Not Available',
            u'Property Floor Area (Buildings and Parking) (ft2)': u'',
            u'Total GHG Emissions (MtCO2e)': u'',
            u'Generation Date': u'',
        }
        self.fake_row = {
            u'Name': u'The Whitehouse',
            u'Address Line 1': u'1600 Pennsylvania Ave.',
            u'Year Built': u'1803',
            u'Double Tester': 'Just a note from bob'
        }

        self.fake_org = Organization.objects.create()
        OrganizationUser.objects.create(
            user=self.fake_user, organization=self.fake_org
        )

        self.import_record.super_organization = self.fake_org
        self.import_record.save()

        self.fake_mappings = {
            'property_name': u'Name',
            'address_line_1': u'Address Line 1',
            'year_built': u'Year Built'
        }

    def test_cached_first_row_order(self):
        """Tests to make sure the first row is saved in the correct order.  It should be the order of the headers in the original file."""
        with patch.object(
            ImportFile, 'cache_first_rows', return_value=None
        ) as mock_method:
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
        with patch.object(
            ImportFile, 'cache_first_rows', return_value=None
        ) as mock_method:
            tasks._save_raw_data(
                self.import_file.pk,
                'fake_cache_key',
                1
            )

        raw_saved = BuildingSnapshot.objects.filter(
            import_file=self.import_file,
        )

        raw_bldg = raw_saved[0]

        self.assertDictEqual(raw_bldg.extra_data, self.fake_extra_data)
        self.assertEqual(raw_bldg.super_organization, self.fake_org)

        expected_pk = raw_bldg.pk

        for k in self.fake_extra_data:
            self.assertEqual(
                raw_bldg.extra_data_sources.get(k),
                expected_pk,
                "%s didn't match the expected source pk.  %s vs %s" %
                (k, expected_pk, raw_bldg.extra_data_sources.get(k))
            )

    def test_map_data(self):
        """Save mappings based on user specifications."""
        fake_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            raw_save_done=True
        )
        fake_raw_bs = BuildingSnapshot.objects.create(
            import_file=fake_import_file,
            extra_data=self.fake_row,
            source_type=ASSESSED_RAW
        )

        util.make_fake_mappings(self.fake_mappings, self.fake_org)

        tasks.map_data(fake_import_file.pk)

        mapped_bs = list(BuildingSnapshot.objects.filter(
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
        BuildingSnapshot.objects.create(
            import_file=fake_import_file,
            source_type=ASSESSED_RAW,
            extra_data=self.fake_row
        )

        self.fake_mappings['address_line_1'] = ['Address Line 1', 'City']
        util.make_fake_mappings(self.fake_mappings, self.fake_org)

        tasks.map_data(fake_import_file.pk)

        mapped_bs = list(BuildingSnapshot.objects.filter(
            import_file=fake_import_file,
            source_type=ASSESSED_BS,
        ))[0]

        self.assertEqual(
            mapped_bs.address_line_1, u'1600 Pennsylvania Ave. Someplace Nice'
        )

    def test_is_same_snapshot(self):
        """Test to check if two snapshots are duplicates"""

        bs_data = {
            'pm_property_id': 1243,
            'tax_lot_id': '435/422',
            'property_name': 'Greenfield Complex',
            'custom_id_1': 12,
            'address_line_1': '555 Database LN.',
            'address_line_2': '',
            'city': 'Gotham City',
            'postal_code': 8999,
        }

        s1 = util.make_fake_snapshot(
            self.import_file, bs_data, ASSESSED_BS, is_canon=True,
            org=self.fake_org
        )

        self.assertTrue(tasks.is_same_snapshot(s1, s1), "Matching a snapshot to itself should return True")

        #Making a different snapshot, now Garfield complex rather than Greenfield complex
        bs_data_2 = {
            'pm_property_id': 1243,
            'tax_lot_id': '435/422',
            'property_name': 'Garfield Complex',
            'custom_id_1': 12,
            'address_line_1': '555 Database LN.',
            'address_line_2': '',
            'city': 'Gotham City',
            'postal_code': 8999,
        }

        s2 = util.make_fake_snapshot(
            self.import_file, bs_data_2, ASSESSED_BS, is_canon=True,
            org=self.fake_org
        )

        self.assertFalse(tasks.is_same_snapshot(s1, s2), "Matching a snapshot to a different snapshot should return False")



    def test_match_buildings(self):
        """Good case for testing our matching system."""
        bs_data = {
            'pm_property_id': 1243,
            'tax_lot_id': '435/422',
            'property_name': 'Greenfield Complex',
            'custom_id_1': 12,
            'address_line_1': '555 Database LN.',
            'address_line_2': '',
            'city': 'Gotham City',
            'postal_code': 8999,
        }

        #Since the change to not match duplicates there needs to be a second record that isn't exactly the same
        #to run this test.  In this case address_line_2 now has a value of 'A' rather than ''
        bs_data_2 = {
            'pm_property_id': 1243,
            'tax_lot_id': '435/422',
            'property_name': 'Greenfield Complex',
            'custom_id_1': 12,
            'address_line_1': '555 Database LN.',
            'address_line_2': 'A',
            'city': 'Gotham City',
            'postal_code': 8999,
        }

        # Setup mapped AS snapshot.
        snapshot = util.make_fake_snapshot(
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

        new_snapshot = util.make_fake_snapshot(
            new_import_file, bs_data_2, PORTFOLIO_BS, org=self.fake_org
        )

        tasks.match_buildings(new_import_file.pk, self.fake_user.pk)

        result = BuildingSnapshot.objects.all()[0]

        self.assertEqual(result.property_name, snapshot.property_name)
        self.assertEqual(result.property_name, new_snapshot.property_name)
        # Since these two buildings share a common ID, we match that way.
        self.assertEqual(result.confidence, 0.9)
        self.assertEqual(
            sorted([r.pk for r in result.parents.all()]),
            sorted([new_snapshot.pk, snapshot.pk])
        )
        self.assertGreater(AuditLog.objects.count(), 0)
        self.assertEqual(
            AuditLog.objects.first().action_note,
            'System matched building ID.'
        )


    def test_match_duplicate_buildings(self):
        """
        Test for behavior when trying to match duplicate building data
        """
        bs_data = {
            'pm_property_id': "8450",
            'tax_lot_id': '143/292',
            'property_name': 'Greenfield Complex',
            'custom_id_1': "99",
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
        snapshot = util.make_fake_snapshot(
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

        new_snapshot = util.make_fake_snapshot(
            new_import_file, bs_data, PORTFOLIO_BS, org=self.fake_org
        )

        tasks.match_buildings(import_file.pk, self.fake_user.pk)
        tasks.match_buildings(new_import_file.pk, self.fake_user.pk)

        self.assertEqual(len(BuildingSnapshot.objects.all()), 2)


    def test_handle_id_matches_duplicate_data(self):
        """
        Test for handle_id_matches behavior when matching duplicate data
        """
        bs_data = {
            'pm_property_id': "2360",
            'tax_lot_id': '476/460',
            'property_name': 'Garfield Complex',
            'custom_id_1': "89",
            'address_line_1': '12975 Database LN.',
            'address_line_2': '',
            'city': 'Cartoon City',
            'postal_code': "54321",
        }

        # Setup mapped AS snapshot.
        snapshot = util.make_fake_snapshot(
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

        new_snapshot = util.make_fake_snapshot(
            duplicate_import_file, bs_data, PORTFOLIO_BS, org=self.fake_org
        )

        self.assertRaises(tasks.DuplicateDataError, tasks.handle_id_matches, new_snapshot, duplicate_import_file, self.fake_user.pk)



    def test_match_no_matches(self):
        """When a canonical exists, but doesn't match, we create a new one."""
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

        bs2_data = {
           'pm_property_id': 9999,
           'tax_lot_id': '1231',
           'property_name': 'A Place',
           'custom_id_1': 0000111000,
           'address_line_1': '44444 Hmmm Ave.',
           'address_line_2': 'Apt 4',
           'city': 'Gotham City',
           'postal_code': 8999,
        }

        snapshot = util.make_fake_snapshot(
            self.import_file, bs1_data, ASSESSED_BS, is_canon=True
        )
        new_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            mapping_done=True
        )
        new_snapshot = util.make_fake_snapshot(
            new_import_file, bs2_data, PORTFOLIO_BS, org=self.fake_org
        )

        self.assertEqual(BuildingSnapshot.objects.all().count(), 2)

        tasks.match_buildings(new_import_file.pk, self.fake_user.pk)

        # E.g. we didn't create a match
        self.assertEqual(BuildingSnapshot.objects.all().count(), 2)
        latest_snapshot = BuildingSnapshot.objects.get(pk=new_snapshot.pk)

        # But we did create another canonical building for the unmatched bs.
        self.assertNotEqual(latest_snapshot.canonical_building, None)
        self.assertNotEqual(
            latest_snapshot.canonical_building.pk,
            snapshot.canonical_building.pk
        )

        self.assertEqual(latest_snapshot.confidence, None)

    def test_match_no_canonical_buildings(self):
        """If no canonicals exist, create, but no new BSes."""
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
        snapshot = util.make_fake_snapshot(
            self.import_file, bs1_data, ASSESSED_BS, is_canon=False,
            org=self.fake_org
        )

        self.import_file.mapping_done = True
        self.import_file.save()

        self.assertEqual(snapshot.canonical_building, None)
        self.assertEqual(BuildingSnapshot.objects.all().count(), 1)

        tasks.match_buildings(self.import_file.pk, self.fake_user.pk)

        refreshed_snapshot = BuildingSnapshot.objects.get(pk=snapshot.pk)
        self.assertNotEqual(refreshed_snapshot.canonical_building, None)
        self.assertEqual(BuildingSnapshot.objects.all().count(), 1)

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
        util.make_fake_snapshot(
            self.import_file, bs1_data, ASSESSED_BS, is_canon=True
        )

        self.assertEqual(BuildingSnapshot.objects.all().count(), 1)

        tasks.match_buildings(self.import_file.pk, self.fake_user.pk)

        self.assertEqual(BuildingSnapshot.objects.all().count(), 1)

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

        util.make_fake_snapshot(
            self.import_file, bs1_data, ASSESSED_BS, is_canon=True,
            org=self.fake_org
        )

        util.make_fake_snapshot(
            new_import_file, bs2_data, PORTFOLIO_BS, org=self.fake_org
        )

        tasks.match_buildings(new_import_file.pk, self.fake_user.pk)

        self.assertEqual(
            BuildingSnapshot.objects.filter(match_type=POSSIBLE_MATCH).count(),
            0
        )
        self.assertEqual(
            BuildingSnapshot.objects.filter(match_type=SYSTEM_MATCH).count(),
            1
        )

    def test_get_ancestors(self):
        """Tests get_ancestors(building), returns all non-composite, non-raw
            BuildingSnapshot instances.
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

        #Since we changed to not match duplicate data make a second record that matches with something slighty changed
        #In this case appended a 'A' to the end of address_line_1
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
        snapshot = util.make_fake_snapshot(
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

        new_snapshot = util.make_fake_snapshot(
            new_import_file, bs_data_2, PORTFOLIO_BS, org=self.fake_org
        )

        tasks.match_buildings(new_import_file.pk, self.fake_user.pk)

        result = BuildingSnapshot.objects.filter(source_type=4)[0]
        ancestor_pks = set([b.pk for b in get_ancestors(result)])
        buildings = BuildingSnapshot.objects.filter(
            source_type__in=[2, 3]
        ).exclude(
            pk=result.pk
        )
        building_pks = set([b.pk for b in buildings])

        self.assertEqual(ancestor_pks, building_pks)

    def test_save_raw_data_batch_iterator(self):
        """Ensure split_csv completes"""
        tasks.save_raw_data(self.import_file.pk)

        self.assertEqual(BuildingSnapshot.objects.filter(
            import_file=self.import_file
        ).count(), 512)

    def test_delete_organization_buildings(self):
        """tests the delete builings for an org"""
        # start with the normal use case
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

        snapshot = util.make_fake_snapshot(
            self.import_file, bs1_data, ASSESSED_BS, is_canon=True
        )

        snapshot.super_organization = self.fake_org
        snapshot.save()

        snapshot = util.make_fake_snapshot(
            new_import_file,
            bs2_data, PORTFOLIO_BS
        )
        snapshot.super_organization = self.fake_org
        snapshot.save()

        tasks.match_buildings(new_import_file.pk, self.fake_user.pk)

        # make one more building snapshot in a different org
        fake_org_2 = Organization.objects.create()
        snapshot = util.make_fake_snapshot(
            self.import_file, bs1_data, ASSESSED_BS, is_canon=True
        )
        snapshot.super_organization = fake_org_2
        snapshot.save()

        self.assertGreater(BuildingSnapshot.objects.filter(
            super_organization=self.fake_org
        ).count(), 0)

        tasks.delete_organization_buildings(self.fake_org.pk)

        self.assertEqual(BuildingSnapshot.objects.filter(
            super_organization=self.fake_org
        ).count(), 0)

        self.assertGreater(BuildingSnapshot.objects.filter(
            super_organization=fake_org_2
        ).count(), 0)

        # test that the CanonicalBuildings are deleted
        self.assertEqual(CanonicalBuilding.objects.filter(
            canonical_snapshot__super_organization=self.fake_org
        ).count(), 0)
        # test that other orgs CanonicalBuildings are not deleted
        self.assertGreater(CanonicalBuilding.objects.filter(
            canonical_snapshot__super_organization=fake_org_2
        ).count(), 0)


class TestTasksXLS(TestTasks):
    """Runs the TestTasks tests with an XLS file"""

    def setUp(self):
        self.maxDiff = None
        self.fake_user = User.objects.create(username='test')
        self.import_record = ImportRecord.objects.create(
            owner=self.fake_user,
        )
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record
        )
        self.import_file.is_espm = True
        self.import_file.source_type = 'PORTFOLIO_RAW'
        self.import_file.file = File(
            open(
                path.join(
                    path.dirname(__file__),
                    'data',
                    'portfolio-manager-sample.xls'
                )
            )
        )
        self.import_file.save()

        # Mimic the representation in the PM file. #ThanksAaron
        self.fake_extra_data = {
            u'City': u'EnergyTown',
            u'ENERGY STAR Score': u'',
            u'State/Province': u'Ilinois',
            u'Site EUI (kBtu/ft2)': u'',
            u'Year Ending': u'',
            u'Weather Normalized Source EUI (kBtu/ft2)': u'',
            u'Parking - Gross Floor Area (ft2)': u'',
            u'Address 1': u'000015581 SW Sycamore Court',
            u'Property Id': 101125,
            u'Address 2': u'Not Available',
            u'Source EUI (kBtu/ft2)': u'',
            u'Release Date': u'',
            u'National Median Source EUI (kBtu/ft2)': u'',
            u'Weather Normalized Site EUI (kBtu/ft2)': u'',
            u'National Median Site EUI (kBtu/ft2)': u'',
            u'Year Built': u'',
            u'Postal Code': u'10108-9812',
            u'Organization': u'Occidental Management',
            u'Property Name': u'Not Available',
            u'Property Floor Area (Buildings and Parking) (ft2)': u'',
            u'Total GHG Emissions (MtCO2e)': u'', u'Generation Date': u'',
            u'Generation Date': u'',
        }
        self.fake_row = {
            u'Name': u'The Whitehouse',
            u'Address Line 1': u'1600 Pennsylvania Ave.',
            u'Year Built': u'1803',
            u'Double Tester': 'Just a note from bob'
        }

        self.fake_org = Organization.objects.create()
        OrganizationUser.objects.create(
            user=self.fake_user, organization=self.fake_org
        )

        self.import_record.super_organization = self.fake_org
        self.import_record.save()

        self.fake_mappings = {
            'property_name': u'Name',
            'address_line_1': u'Address Line 1',
            'year_built': u'Year Built'
        }


class TestTasksXLSX(TestTasks):
    """Runs the TestsTasks tests with an XLSX file."""

    def setUp(self):
        self.maxDiff = None
        self.fake_user = User.objects.create(username='test')
        self.import_record = ImportRecord.objects.create(
            owner=self.fake_user,
        )
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record
        )
        self.import_file.is_espm = True
        self.import_file.source_type = 'PORTFOLIO_RAW'
        self.import_file.file = File(
            open(
                path.join(
                    path.dirname(__file__),
                    'data',
                    'portfolio-manager-sample.xlsx'
                )
            )
        )
        self.import_file.save()

        # Mimic the representation in the PM file. #ThanksAaron
        self.fake_extra_data = {
            u'City': u'EnergyTown',
            u'ENERGY STAR Score': u'',
            u'State/Province': u'Ilinois',
            u'Site EUI (kBtu/ft2)': u'',
            u'Year Ending': u'',
            u'Weather Normalized Source EUI (kBtu/ft2)': u'',
            u'Parking - Gross Floor Area (ft2)': u'',
            u'Address 1': u'000015581 SW Sycamore Court',
            u'Property Id': 101125,
            u'Address 2': u'Not Available',
            u'Source EUI (kBtu/ft2)': u'',
            u'Release Date': u'',
            u'National Median Source EUI (kBtu/ft2)': u'',
            u'Weather Normalized Site EUI (kBtu/ft2)': u'',
            u'National Median Site EUI (kBtu/ft2)': u'',
            u'Year Built': u'',
            u'Postal Code': u'10108-9812',
            u'Organization': u'Occidental Management',
            u'Property Name': u'Not Available',
            u'Property Floor Area (Buildings and Parking) (ft2)': u'',
            u'Total GHG Emissions (MtCO2e)': u'',
            u'Generation Date': u'',
        }
        self.fake_row = {
            u'Name': u'The Whitehouse',
            u'Address Line 1': u'1600 Pennsylvania Ave.',
            u'Year Built': u'1803',
            u'Double Tester': 'Just a note from bob'
        }

        self.fake_org = Organization.objects.create()
        OrganizationUser.objects.create(
            user=self.fake_user, organization=self.fake_org
        )

        self.import_record.super_organization = self.fake_org
        self.import_record.save()

        self.fake_mappings = {
            'property_name': u'Name',
            'address_line_1': u'Address Line 1',
            'year_built': u'Year Built'
        }

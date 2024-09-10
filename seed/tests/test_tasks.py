# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
import pathlib
from os import path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from seed import tasks
from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.models import DATA_STATE_MATCHING, PORTFOLIO_RAW, SEED_DATA_SOURCES, Column, PropertyState
from seed.test_helpers.fake import FakePropertyFactory, FakePropertyStateFactory
from seed.utils.organizations import create_organization

logger = logging.getLogger(__name__)


class TestTasks(TestCase):
    """Tests for dealing with SEED related tasks."""

    def setUp(self):
        self.fake_user = User.objects.create(username="test")
        self.fake_org, _, _ = create_organization(self.fake_user)
        self.import_record = ImportRecord.objects.create(
            owner=self.fake_user, last_modified_by=self.fake_user, access_level_instance=self.fake_org.root
        )

        filepath = path.join(path.dirname(__file__), "data", "portfolio-manager-sample.csv")
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type=SEED_DATA_SOURCES[PORTFOLIO_RAW][1],
        )
        self.import_file.file = SimpleUploadedFile(name="portfolio-manager-sample.csv", content=pathlib.Path(filepath).read_bytes())
        self.import_file.save()

        # Mimic the representation in the PM file. #ThanksAaron
        self.fake_extra_data = {
            "City": "EnergyTown",
            "ENERGY STAR Score": "",
            "State/Province": "Illinois",
            "Site EUI (kBtu/ft2)": "",
            "Year Ending": "",
            "Weather Normalized Source EUI (kBtu/ft2)": "",
            "Parking - Gross Floor Area (ft2)": "",
            "Address 1": "000015581 SW Sycamore Court",
            "Property Id": "101125",
            "Address 2": "Not Available",
            "Source EUI (kBtu/ft2)": "",
            "Release Date": "",
            "National Median Source EUI (kBtu/ft2)": "",
            "Weather Normalized Site EUI (kBtu/ft2)": "",
            "National Median Site EUI (kBtu/ft2)": "",
            "Year Built": "",
            "Postal Code": "10108-9812",
            "Organization": "Occidental Management",
            "Property Name": "Not Available",
            "Property Floor Area (Buildings and Parking) (ft2)": "",
            "Total GHG Emissions (MtCO2e)": "",
            "Generation Date": "",
        }
        self.fake_row = {
            "Name": "The Whitehouse",
            "Address Line 1": "1600 Pennsylvania Ave.",
            "Year Built": "1803",
            "Double Tester": "Just a note from bob",
        }

        self.import_record.super_organization = self.fake_org
        self.import_record.save()

        self.fake_mappings = {"property_name": "Name", "address_line_1": "Address Line 1", "year_built": "Year Built"}
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

    def test_delete_organization(self):
        self.assertTrue(User.objects.filter(pk=self.fake_user.pk).exists())
        self.assertTrue(Organization.objects.filter(pk=self.fake_org.pk).exists())
        self.assertTrue(ImportRecord.objects.filter(pk=self.import_record.pk).exists())
        self.assertTrue(ImportFile.objects.filter(pk=self.import_file.pk).exists())

        tasks.delete_organization(self.fake_org.pk)

        self.assertTrue(User.objects.filter(pk=self.fake_user.pk).exists())
        self.assertFalse(Organization.objects.filter(pk=self.fake_org.pk).exists())
        self.assertFalse(ImportRecord.objects.filter(pk=self.import_record.pk).exists())
        self.assertFalse(ImportFile.objects.filter(pk=self.import_file.pk).exists())

    def test_rehash_query_or_structure(self):
        state_1 = self.property_state_factory.get_property_state()
        state_1.water_use = 100
        state_1.data_state = DATA_STATE_MATCHING
        state_1.save()
        state_2 = self.property_state_factory.get_property_state()
        state_2.data_state = DATA_STATE_MATCHING
        state_2.save()
        column = Column.objects.filter(column_name="water_use", table_name="PropertyState", organization_id=state_1.organization_id)[0]
        column.is_excluded_from_hash = True
        column.save()

        query = tasks._build_property_query_for_rehashed_columns(state_1.organization_id, [column])
        ids = PropertyState.objects.filter(query).values_list("id", flat=True)

        self.assertIn(state_1.id, ids)
        self.assertNotIn(state_2.id, ids)

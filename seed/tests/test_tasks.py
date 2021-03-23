# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
from os import path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from seed import tasks
from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.utils.organizations import create_organization

logger = logging.getLogger(__name__)


class TestTasks(TestCase):
    """Tests for dealing with SEED related tasks."""

    def setUp(self):
        self.fake_user = User.objects.create(username='test')
        self.fake_org, _, _ = create_organization(self.fake_user)
        self.import_record = ImportRecord.objects.create(
            owner=self.fake_user, last_modified_by=self.fake_user
        )

        filepath = path.join(path.dirname(__file__), 'data', 'portfolio-manager-sample.csv')
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type='PORTFOLIO_RAW',
        )
        self.import_file.file = SimpleUploadedFile(
            name='portfolio-manager-sample.csv',
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()

        # Mimic the representation in the PM file. #ThanksAaron
        self.fake_extra_data = {
            'City': 'EnergyTown',
            'ENERGY STAR Score': '',
            'State/Province': 'Illinois',
            'Site EUI (kBtu/ft2)': '',
            'Year Ending': '',
            'Weather Normalized Source EUI (kBtu/ft2)': '',
            'Parking - Gross Floor Area (ft2)': '',
            'Address 1': '000015581 SW Sycamore Court',
            'Property Id': '101125',
            'Address 2': 'Not Available',
            'Source EUI (kBtu/ft2)': '',
            'Release Date': '',
            'National Median Source EUI (kBtu/ft2)': '',
            'Weather Normalized Site EUI (kBtu/ft2)': '',
            'National Median Site EUI (kBtu/ft2)': '',
            'Year Built': '',
            'Postal Code': '10108-9812',
            'Organization': 'Occidental Management',
            'Property Name': 'Not Available',
            'Property Floor Area (Buildings and Parking) (ft2)': '',
            'Total GHG Emissions (MtCO2e)': '',
            'Generation Date': '',
        }
        self.fake_row = {
            'Name': 'The Whitehouse',
            'Address Line 1': '1600 Pennsylvania Ave.',
            'Year Built': '1803',
            'Double Tester': 'Just a note from bob'
        }

        self.import_record.super_organization = self.fake_org
        self.import_record.save()

        self.fake_mappings = {
            'property_name': 'Name',
            'address_line_1': 'Address Line 1',
            'year_built': 'Year Built'
        }

    def test_delete_organization(self):
        self.assertTrue(
            User.objects.filter(pk=self.fake_user.pk).exists())
        self.assertTrue(
            Organization.objects.filter(pk=self.fake_org.pk).exists())
        self.assertTrue(
            ImportRecord.objects.filter(pk=self.import_record.pk).exists())
        self.assertTrue(
            ImportFile.objects.filter(pk=self.import_file.pk).exists())

        tasks.delete_organization(self.fake_org.pk)

        self.assertTrue(
            User.objects.filter(pk=self.fake_user.pk).exists())
        self.assertFalse(
            Organization.objects.filter(pk=self.fake_org.pk).exists())
        self.assertFalse(
            ImportRecord.objects.filter(pk=self.import_record.pk).exists())
        self.assertFalse(
            ImportFile.objects.filter(pk=self.import_file.pk).exists())

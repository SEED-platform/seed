# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
from os import path

from django.core.files import File
from django.test import TestCase

from seed import tasks
from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser

logger = logging.getLogger(__name__)


class TestTasks(TestCase):
    """Tests for dealing with SEED related tasks."""

    def setUp(self):
        self.fake_user = User.objects.create(username='test')
        self.import_record = ImportRecord.objects.create(
            owner=self.fake_user, last_modified_by=self.fake_user
        )
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record
        )
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
            u'State/Province': u'Illinois',
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

    def test_delete_organization(self):
        self.assertTrue(User.objects.filter(pk=self.fake_user.pk).exists())
        self.assertTrue(
            Organization.objects.filter(pk=self.fake_org.pk).exists())
        self.assertTrue(
            ImportRecord.objects.filter(pk=self.import_record.pk).exists())
        self.assertTrue(
            ImportFile.objects.filter(pk=self.import_file.pk).exists())

        tasks.delete_organization(self.fake_org.pk, 'fake-progress-key')

        self.assertFalse(User.objects.filter(pk=self.fake_user.pk).exists())
        self.assertFalse(
            Organization.objects.filter(pk=self.fake_org.pk).exists())
        self.assertFalse(
            ImportRecord.objects.filter(pk=self.import_record.pk).exists())
        self.assertFalse(
            ImportFile.objects.filter(pk=self.import_file.pk).exists())

    def test_delete_organization_doesnt_delete_user_if_multiple_memberships(
            self):
        """
        Deleting an org should not delete the orgs users if the user belongs to many orgs.
        """
        org = Organization.objects.create()
        OrganizationUser.objects.create(organization=org, user=self.fake_user)

        self.assertTrue(User.objects.filter(pk=self.fake_user.pk).exists())

        tasks.delete_organization(self.fake_org.pk, 'fake-progress-key')

        self.assertTrue(User.objects.filter(pk=self.fake_user.pk).exists())

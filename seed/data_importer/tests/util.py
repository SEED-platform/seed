# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
from os import path

from django.core.files import File

from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser

logger = logging.getLogger(__name__)

def load_test_data(test_obj, filename):
    """
    Load some test data for running tests

    Args:
        test_obj: The test object (typically self)
        filename: Name of the file to load in tests/data directory

    Returns:

    """
    test_obj.maxDiff = None
    test_obj.fake_user = User.objects.create(username='test')
    test_obj.import_record = ImportRecord.objects.create(
        owner=test_obj.fake_user, last_modified_by=test_obj.fake_user
    )
    test_obj.import_file = ImportFile.objects.create(
        import_record=test_obj.import_record
    )
    test_obj.import_file.is_espm = True
    test_obj.import_file.source_type = 'PORTFOLIO_RAW'
    test_obj.import_file.file = File(
        open(
            path.join(
                path.dirname(__file__),
                'data',
                filename
            )
        )
    )
    test_obj.import_file.save()

    # Mimic the representation in the PM file. #ThanksAaron
    # This is the last row of the portfolio manager file
    test_obj.fake_extra_data = {
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
    test_obj.fake_row = {
        u'Name': u'The Whitehouse',
        u'Address Line 1': u'1600 Pennsylvania Ave.',
        u'Year Built': u'1803',
        u'Double Tester': 'Just a note from bob'
    }

    test_obj.fake_org = Organization.objects.create()
    OrganizationUser.objects.create(
        user=test_obj.fake_user, organization=test_obj.fake_org
    )

    test_obj.import_record.super_organization = test_obj.fake_org
    test_obj.import_record.save()

    test_obj.fake_mappings = {
        'property_name': u'Name',
        'address_line_1': u'Address Line 1',
        'year_built': u'Year Built'
    }

    return test_obj

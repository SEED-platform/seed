# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import datetime
from django.utils import timezone
import logging
import os.path

from django.core.files import File
from django.test import TestCase

from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import (
    ColumnMapping,
    Cycle,
    PropertyState,
)
from seed.models import (
    DATA_STATE_IMPORT,
    # DATA_STATE_MAPPING,
)

logger = logging.getLogger(__name__)

TAXLOT_MAPPING = [
    {
        "from_field": u'jurisdiction tax lot id',
        "to_table_name": u'TaxLotState',
        "to_field": u'jurisdiction_tax_lot_id',
    },
    {
        "from_field": u'address',
        "to_table_name": u'TaxLotState',
        "to_field": u'address_line_1'
    },
    {
        "from_field": u'city',
        "to_table_name": u'TaxLotState',
        "to_field": u'city'
    },
    {
        "from_field": u'number buildings',
        "to_table_name": u'TaxLotState',
        "to_field": u'number_properties'
    },
]

PROPERTIES_MAPPING = [
    {
        "from_field": u'jurisdiction tax lot id',
        "to_table_name": u'TaxLotState',
        "to_field": u'jurisdiction_tax_lot_id',
    }, {
        "from_field": u'jurisdiction property id',
        "to_table_name": u'PropertyState',
        "to_field": u'jurisdiction_property_id',
    }, {
        "from_field": u'pm property id',
        "to_table_name": u'PropertyState',
        "to_field": u'pm_property_id',
    }, {
        "from_field": u'custom id 1',
        "to_table_name": u'PropertyState',
        "to_field": u'custom_id_1',
    }, {
        "from_field": u'pm parent property id',
        "to_table_name": u'PropertyState',
        "to_field": u'pm_parent_property_id'
    }, {
        "from_field": u'address line 1',
        "to_table_name": u'PropertyState',
        "to_field": u'address_line_1'
    }, {
        "from_field": u'city',
        "to_table_name": u'PropertyState',
        "to_field": u'city'
    }, {
        "from_field": u'property name',
        "to_table_name": u'PropertyState',
        "to_field": u'property_name'
    }, {
        "from_field": u'property notes',
        "to_table_name": u'PropertyState',
        "to_field": u'property_notes'
    }, {
        "from_field": u'use description',
        "to_table_name": u'PropertyState',
        "to_field": u'use_description'
    }, {
        "from_field": u'gross floor area',
        "to_table_name": u'PropertyState',
        "to_field": u'gross_floor_area'
    }, {
        "from_field": u'owner',
        "to_table_name": u'PropertyState',
        "to_field": u'owner'
    }, {
        "from_field": u'owner email',
        "to_table_name": u'PropertyState',
        "to_field": u'owner_email'
    }, {
        "from_field": u'owner telephone',
        "to_table_name": u'PropertyState',
        "to_field": u'owner_telephone'
    }, {
        "from_field": u'site eui',
        "to_table_name": u'PropertyState',
        "to_field": u'site_eui'
    }, {
        "from_field": u'energy score',
        "to_table_name": u'PropertyState',
        "to_field": u'energy_score'
    }, {
        "from_field": u'year ending',
        "to_table_name": u'PropertyState',
        "to_field": u'year_ending'
    }, {
        "from_field": u'extra data 1',
        "to_table_name": u'PropertyState',
        "to_field": u'data_007'
    }, {
        "from_field": u'extra data 2',
        "to_table_name": u'TaxLotState',
        "to_field": u'data_008'
    }
]

FAKE_EXTRA_DATA = {
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

FAKE_ROW = {
    u'Name': u'The Whitehouse',
    u'Address Line 1': u'1600 Pennsylvania Ave.',
    u'Year Built': u'1803',
    u'Double Tester': 'Just a note from bob'
}

FAKE_MAPPINGS = {
    'portfolio': PROPERTIES_MAPPING,
    'taxlot': TAXLOT_MAPPING,
    'full': [
        {
            "from_field": u'Name',
            "to_table_name": u'PropertyState',
            "to_field": u'property_name',
        }, {
            "from_field": u'Address Line 1',
            "to_table_name": u'PropertyState',
            "to_field": u'address_line_1',
        }, {
            "from_field": u'Year Built',
            "to_table_name": u'PropertyState',
            "to_field": u'year_built',
        }, {
            "from_field": u'Double Tester',
            "to_table_name": u'PropertyState',
            "to_field": u'Double Tester',
        }

    ],
    'fake_row': [
        {
            "from_field": u'Name',
            "to_table_name": u'PropertyState',
            "to_field": u'property_name',
        }, {
            "from_field": u'Address Line 1',
            "to_table_name": u'PropertyState',
            "to_field": u'address_line_1',
        }, {
            "from_field": u'Year Built',
            "to_table_name": u'PropertyState',
            "to_field": u'year_built',
        }, {
            "from_field": u'Double Tester',
            "to_table_name": u'PropertyState',
            "to_field": u'Double Tester',
        }
    ],
    'short': {  # Short should no longer be used and probably doesn't work anymore.
        'property_name': u'Name',
        'address_line_1': u'Address Line 1',
        'year_built': u'Year Built'
    },
}


class DataMappingBaseTestCase(TestCase):
    """Base Test Case Class to handle data import"""

    def set_up(self, import_file_source_type):
        # default_values
        import_file_is_espm = getattr(self, 'import_file_is_espm', True)
        import_file_data_state = getattr(self, 'import_file_data_state', DATA_STATE_IMPORT)

        user = User.objects.create(username='test')
        org = Organization.objects.create()

        cycle, _ = Cycle.objects.get_or_create(
            name=u'Test Hack Cycle 2015',
            organization=org,
            start=datetime.datetime(2015, 1, 1, tzinfo=timezone.get_current_timezone()),
            end=datetime.datetime(2015, 12, 31, tzinfo=timezone.get_current_timezone()),
        )

        # Create an org user
        OrganizationUser.objects.create(user=user, organization=org)

        import_record = ImportRecord.objects.create(
            owner=user, last_modified_by=user, super_organization=org
        )
        import_file = ImportFile.objects.create(import_record=import_record, cycle=cycle)
        import_file.is_espm = import_file_is_espm
        import_file.source_type = import_file_source_type
        import_file.data_state = import_file_data_state
        import_file.save()

        return user, org, import_file, import_record, cycle

    def load_import_file_file(self, filename, import_file):
        f = os.path.join(os.path.dirname(__file__), 'data', filename)
        import_file.file = File(open(f))
        import_file.save()
        return import_file

    def tearDown(self):
        User.objects.all().delete()
        ColumnMapping.objects.all().delete()
        ImportFile.objects.all().delete()
        ImportRecord.objects.all().delete()
        OrganizationUser.objects.all().delete()
        Organization.objects.all().delete()
        User.objects.all().delete()
        Cycle.objects.all().delete()
        PropertyState.objects.all().delete()

# import csv
# import json
# import logging
# import os
# from os import path
#
# from django.core.files import File
#
# from seed.data_importer.models import ImportFile, ImportRecord
# from seed.data_importer.tasks import save_raw_data, map_data
# from seed.landing.models import SEEDUser as User
# from seed.lib.superperms.orgs.models import Organization, OrganizationUser
# from seed.models import (
#     Column,
#     DATA_STATE_IMPORT,
#     ASSESSED_RAW
# )
#
# logger = logging.getLogger(__name__)
#
#
# def load_test_data(test_obj, filename):
#     """
#     Load some test data for running tests
#
#     Args:
#         test_obj: The test object (typically self)
#         filename: Name of the file to load in tests/data directory
#
#     Returns:
#
#     """
#     test_obj.maxDiff = None
#     test_obj.import_filename = filename
#     test_obj.fake_user = User.objects.create(username='test')
#     test_obj.import_record = ImportRecord.objects.create(
#         owner=test_obj.fake_user,
#         last_modified_by=test_obj.fake_user
#     )
#     test_obj.import_file = ImportFile.objects.create(
#         import_record=test_obj.import_record
#     )
#     test_obj.import_file.is_espm = True
#     test_obj.import_file.source_type = 'PORTFOLIO_RAW'
#     test_obj.import_file.data_state = DATA_STATE_IMPORT
#     f = path.join(path.dirname(__file__), 'data', filename)
#     test_obj.import_file.file = File(open(f))
#     test_obj.import_file.save()
#
#     # Mimic the representation in the PM file. #ThanksAaron
#     # This is the last row of the portfolio manager file
#     test_obj.fake_extra_data = {
#         u'City': u'EnergyTown',
#         u'ENERGY STAR Score': u'',
#         u'State/Province': u'Illinois',
#         u'Site EUI (kBtu/ft2)': u'',
#         u'Year Ending': u'',
#         u'Weather Normalized Source EUI (kBtu/ft2)': u'',
#         u'Parking - Gross Floor Area (ft2)': u'',
#         u'Address 1': u'000015581 SW Sycamore Court',
#         u'Property Id': u'101125',
#         u'Address 2': u'Not Available',
#         u'Source EUI (kBtu/ft2)': u'',
#         u'Release Date': u'',
#         u'National Median Source EUI (kBtu/ft2)': u'',
#         u'Weather Normalized Site EUI (kBtu/ft2)': u'',
#         u'National Median Site EUI (kBtu/ft2)': u'',
#         u'Year Built': u'',
#         u'Postal Code': u'10108-9812',
#         u'Organization': u'Occidental Management',
#         u'Property Name': u'Not Available',
#         u'Property Floor Area (Buildings and Parking) (ft2)': u'',
#         u'Total GHG Emissions (MtCO2e)': u'',
#         u'Generation Date': u'',
#     }
#     test_obj.fake_row = {
#         u'Name': u'The Whitehouse',
#         u'Address Line 1': u'1600 Pennsylvania Ave.',
#         u'Year Built': u'1803',
#         u'Double Tester': 'Just a note from bob'
#     }
#
#     test_obj.fake_org = Organization.objects.create()
#     OrganizationUser.objects.create(
#         user=test_obj.fake_user,
#         organization=test_obj.fake_org
#     )
#
#     test_obj.import_record.super_organization = test_obj.fake_org
#     test_obj.import_record.save()
#
#     test_obj.fake_mappings = [
#         {
#             "from_field": u'Name',
#             "to_table_name": u'PropertyState',
#             "to_field": u'property_name',
#         }, {
#             "from_field": u'Address Line 1',
#             "to_table_name": u'PropertyState',
#             "to_field": u'address_line_1',
#         }, {
#             "from_field": u'Year Built',
#             "to_table_name": u'PropertyState',
#             "to_field": u'year_built',
#         }, {
#             "from_field": u'Double Tester',
#             "to_table_name": u'PropertyState',
#             "to_field": u'Double Tester',
#         }
#
#     ]
#
#     return test_obj
#
#
# def import_example_data(test_obj, filename):
#     """
#     Import example spreadsheets that contain the 4 cases to test the
#     new data model.
#
#     Args:
#         test_obj: test object to add data to
#         filename: name of the file to import
#
#     Returns:
#         test_obj
#
#     """
#
#     test_obj.fake_user = User.objects.create(username='test')
#     test_obj.fake_org = Organization.objects.create()
#
#     # Create an org user
#     OrganizationUser.objects.create(
#         user=test_obj.fake_user,
#         organization=test_obj.fake_org
#     )
#
#     test_obj.import_record = ImportRecord.objects.create(
#         owner=test_obj.fake_user,
#         last_modified_by=test_obj.fake_user,
#         super_organization=test_obj.fake_org
#     )
#     test_obj.import_file = ImportFile.objects.create(
#         import_record=test_obj.import_record
#     )
#     test_obj.import_file.is_espm = True
#     test_obj.import_file.source_type = ASSESSED_RAW
#     test_obj.import_file.data_state = DATA_STATE_IMPORT
#
#     f = path.join(path.dirname(__file__), 'data', filename)
#     test_obj.import_file.file = File(open(f))
#     test_obj.import_file.save()
#
#     save_raw_data(test_obj.import_file.id)
#
#     from seed.models import PropertyState
#     print PropertyState.objects.all().last().__dict__
#
#     # setup the mapping
#     test_obj.fake_mapping = [
#         {
#             "from_field": u'jurisdiction_taxlot_identifier',
#             "to_table_name": u'TaxLotState',
#             "to_field": u'jurisdiction_taxlot_identifier',
#         }, {
#             "from_field": u'jurisdiction_property_identifier',
#             "to_table_name": u'PropertyState',
#             "to_field": u'jurisdiction_property_identifier',
#         }, {
#             "from_field": u'building_portfolio_manager_identifier',
#             "to_table_name": u'PropertyState',
#             "to_field": u'building_portfolio_manager_identifier',
#         }, {
#             "from_field": u'pm_parent_property_id',
#             "to_table_name": u'PropertyState',
#             "to_field": u'pm_parent_property_id'
#         }, {
#             "from_field": u'address_line_1',
#             "to_table_name": u'PropertyState',
#             "to_field": u'address_line_1'
#         }, {
#             "from_field": u'city',
#             "to_table_name": u'PropertyState',
#             "to_field": u'city'
#         }, {
#             "from_field": u'property_name',
#             "to_table_name": u'PropertyState',
#             "to_field": u'property_name'
#         }, {
#             "from_field": u'property_notes',
#             "to_table_name": u'PropertyState',
#             "to_field": u'property_notes'
#         }, {
#             "from_field": u'use_description',
#             "to_table_name": u'PropertyState',
#             "to_field": u'use_description'
#         }, {
#             "from_field": u'gross_floor_area',
#             "to_table_name": u'PropertyState',
#             "to_field": u'gross_floor_area'
#         }, {
#             "from_field": u'owner',
#             "to_table_name": u'PropertyState',
#             "to_field": u'owner'
#         }, {
#             "from_field": u'owner_email',
#             "to_table_name": u'PropertyState',
#             "to_field": u'owner_email'
#         }, {
#             "from_field": u'owner_telephone',
#             "to_table_name": u'PropertyState',
#             "to_field": u'owner_telephone'
#         }, {
#             "from_field": u'site_eui',
#             "to_table_name": u'PropertyState',
#             "to_field": u'site_eui'
#         }, {
#             "from_field": u'energy_score',
#             "to_table_name": u'PropertyState',
#             "to_field": u'energy_score'
#         }, {
#             "from_field": u'year_ending',
#             "to_table_name": u'PropertyState',
#             "to_field": u'year_ending'
#         }, {
#             "from_field": u'extra_data_1',
#             "to_table_name": u'PropertyState',
#             "to_field": u'data_007'
#         }, {
#             "from_field": u'extra_data_2',
#             "to_table_name": u'TaxLotState',
#             "to_field": u'data_008'
#         }
#     ]
#
#     Column.create_mappings(test_obj.fake_mapping, test_obj.fake_org, test_obj.fake_user)
#
#     # call the mapping function from the tasks file
#     map_data(test_obj.import_file.id)
#
#     # print len(PropertyState.objects.all())
#
#     # This is the last row of the portfolio manager file
#     test_obj.fake_extra_data = {
#         u'City': u'EnergyTown',
#         u'ENERGY STAR Score': u'',
#         u'State/Province': u'Illinois',
#         u'Site EUI (kBtu/ft2)': u'',
#         u'Year Ending': u'',
#         u'Weather Normalized Source EUI (kBtu/ft2)': u'',
#         u'Parking - Gross Floor Area (ft2)': u'',
#         u'Address 1': u'000015581 SW Sycamore Court',
#         u'Property Id': u'101125',
#         u'Address 2': u'Not Available',
#         u'Source EUI (kBtu/ft2)': u'',
#         u'Release Date': u'',
#         u'National Median Source EUI (kBtu/ft2)': u'',
#         u'Weather Normalized Site EUI (kBtu/ft2)': u'',
#         u'National Median Site EUI (kBtu/ft2)': u'',
#         u'Year Built': u'',
#         u'Postal Code': u'10108-9812',
#         u'Organization': u'Occidental Management',
#         u'Property Name': u'Not Available',
#         u'Property Floor Area (Buildings and Parking) (ft2)': u'',
#         u'Total GHG Emissions (MtCO2e)': u'',
#         u'Generation Date': u'',
#     }
#     test_obj.fake_row = {
#         u'Name': u'The Whitehouse',
#         u'Address Line 1': u'1600 Pennsylvania Ave.',
#         u'Year Built': u'1803',
#         u'Double Tester': 'Just a note from bob'
#     }
#
#     test_obj.import_record.super_organization = test_obj.fake_org
#     test_obj.import_record.save()
#
#     test_obj.fake_mappings = {
#         'property_name': u'Name',
#         'address_line_1': u'Address Line 1',
#         'year_built': u'Year Built'
#     }
#
#     return test_obj
#
#
# def import_exported_test_data(test_obj, filename):
#     """
#     Import test files from Stephen for many-to-many testing. This imports and
#     maps the data accordingly. Presently these files are missing a couple
#     attributes to make them valid: 1) need the master campus record to define
#     the pm_property_id, 2) the joins between propertystate and taxlotstate
#     seem to be missing
#
#         Args:
#             test_obj: test object to add data to
#             filename: name of the file to import in the new format
#
#         Returns:
#             test_obj
#     """
#
#     test_obj.fake_user = User.objects.create(username='test')
#     test_obj.fake_org = Organization.objects.create()
#     # Create an org user
#     OrganizationUser.objects.create(user=test_obj.fake_user, organization=test_obj.fake_org)
#
#     test_obj.import_record = ImportRecord.objects.create(
#         owner=test_obj.fake_user,
#         last_modified_by=test_obj.fake_user,
#         super_organization=test_obj.fake_org
#     )
#     test_obj.import_file = ImportFile.objects.create(import_record=test_obj.import_record)
#     test_obj.import_file.is_espm = True
#     test_obj.import_file.source_type = ASSESSED_RAW
#     test_obj.import_file.data_state = DATA_STATE_IMPORT
#
#     # Do a bunch of work to flatten out this temp file that has extra_data as
#     # a string representation of a dict
#     data = []
#     keys = None
#     new_keys = set()
#
#     f = path.join(path.dirname(__file__), 'data', filename)
#     with open(f, 'rb') as csvfile:
#         reader = csv.DictReader(csvfile)
#         keys = reader.fieldnames
#         for row in reader:
#             ed = json.loads(row.pop('extra_data'))
#             for k, v in ed.iteritems():
#                 new_keys.add(k)
#                 row[k] = v
#             data.append(row)
#
#     # remove the extra_data column and add in the new columns
#     keys.remove('extra_data')
#     for k in new_keys:
#         keys.append(k)
#
#     # save the new file
#     new_file_name = 'tmp_' + os.path.splitext(os.path.basename(filename))[0] + '_flat.csv'
#     f_new = path.join(path.dirname(__file__), 'data', new_file_name)
#     with open(f_new, 'w') as csvfile:
#         writer = csv.DictWriter(csvfile, fieldnames=keys)
#         writer.writeheader()
#         for d in data:
#             writer.writerow(d)
#
#     # save the keys
#     new_file_name = 'tmp_' + os.path.splitext(os.path.basename(filename))[0] + '_keys.csv'
#     f_new = path.join(path.dirname(__file__), 'data', new_file_name)
#     with open(f_new, 'w') as outfile:
#         for item in keys:
#             print>> outfile, item
#
#     # Continue saving the raw data
#     new_file_name = 'tmp_' + os.path.splitext(os.path.basename(filename))[0] + '_flat.csv'
#     f_new = path.join(path.dirname(__file__), 'data', new_file_name)
#     test_obj.import_file.file = File(open(f_new))
#     test_obj.import_file.save()
#
#     save_raw_data(test_obj.import_file.id)
#
#     # for ps in PropertyState.objects.all():
#     #     print ps.__dict__
#
#     # the mapping is just the 'keys' repeated since the file was created as a
#     # database dump
#     mapping = []
#     for k in keys:
#         if k == 'id':
#             continue
#         mapping.append(
#             {
#                 "from_field": k,
#                 "to_table_name": "PropertyState",
#                 "to_field": k
#             }
#         )
#
#     Column.create_mappings(mapping, test_obj.fake_org, test_obj.fake_user)
#
#     # call the mapping function from the tasks file
#     map_data(test_obj.import_file.id)
#
#     # print len(PropertyState.objects.all())
#
#     # Mimic the representation in the PM file. #ThanksAaron
#     # This is the last row of the portfolio manager file
#     test_obj.fake_extra_data = {
#         u'City': u'EnergyTown',
#         u'ENERGY STAR Score': u'',
#         u'State/Province': u'Illinois',
#         u'Site EUI (kBtu/ft2)': u'',
#         u'Year Ending': u'',
#         u'Weather Normalized Source EUI (kBtu/ft2)': u'',
#         u'Parking - Gross Floor Area (ft2)': u'',
#         u'Address 1': u'000015581 SW Sycamore Court',
#         u'Property Id': u'101125',
#         u'Address 2': u'Not Available',
#         u'Source EUI (kBtu/ft2)': u'',
#         u'Release Date': u'',
#         u'National Median Source EUI (kBtu/ft2)': u'',
#         u'Weather Normalized Site EUI (kBtu/ft2)': u'',
#         u'National Median Site EUI (kBtu/ft2)': u'',
#         u'Year Built': u'',
#         u'Postal Code': u'10108-9812',
#         u'Organization': u'Occidental Management',
#         u'Property Name': u'Not Available',
#         u'Property Floor Area (Buildings and Parking) (ft2)': u'',
#         u'Total GHG Emissions (MtCO2e)': u'',
#         u'Generation Date': u'',
#     }
#     test_obj.fake_row = {
#         u'Name': u'The Whitehouse',
#         u'Address Line 1': u'1600 Pennsylvania Ave.',
#         u'Year Built': u'1803',
#         u'Double Tester': 'Just a note from bob'
#     }
#
#     test_obj.import_record.super_organization = test_obj.fake_org
#     test_obj.import_record.save()
#
#     # setup the mapping
#     test_obj.fake_mappings = []

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import datetime
import logging

from django.test import TestCase
from django.utils import timezone

from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models.data_quality import DataQualityCheck
from seed.models import (
    Column,
    ColumnMapping,
    Cycle,
    Property,
    PropertyState,
    PropertyView,
    DATA_STATE_IMPORT,
    ASSESSED_RAW,
    PropertyAuditLog,
    StatusLabel,
    TaxLotAuditLog,
    TaxLotState,
    TaxLot,
    TaxLotView,
    TaxLotProperty,
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
    'short': {  # Short should no longer be used and probably does not work anymore.
        'property_name': u'Name',
        'address_line_1': u'Address Line 1',
        'year_built': u'Year Built'
    },
}


class DeleteModelsTestCase(TestCase):
    def tearDown(self):
        User.objects.all().delete()
        Organization.objects.all().delete()
        OrganizationUser.objects.all().delete()
        Column.objects.all().delete()
        ColumnMapping.objects.all().delete()
        Cycle.objects.all().delete()
        DataQualityCheck.objects.all().delete()
        ImportFile.objects.all().delete()
        ImportRecord.objects.all().delete()
        Property.objects.all().delete()
        PropertyState.objects.all().delete()
        PropertyView.objects.all().delete()
        PropertyAuditLog.objects.all().delete()
        StatusLabel.objects.all().delete()
        TaxLot.objects.all().delete()
        TaxLotState.objects.all().delete()
        TaxLotView.objects.all().delete()
        TaxLotAuditLog.objects.all().delete()
        TaxLotProperty.objects.all().delete()


class DataMappingBaseTestCase(DeleteModelsTestCase):
    """Base Test Case Class to handle data import"""

    def set_up(self, import_file_source_type):
        # default_values
        import_file_is_espm = getattr(self, 'import_file_is_espm', True)
        import_file_data_state = getattr(self, 'import_file_data_state', DATA_STATE_IMPORT)

        if not User.objects.filter(username='test_user@demo.com').exists():
            user = User.objects.create_user('test_user@demo.com', password='test_pass')
        else:
            user = User.objects.get(username='test_user@demo.com')

        org = Organization.objects.create()

        cycle, _ = Cycle.objects.get_or_create(
            name=u'Test Hack Cycle 2015',
            organization=org,
            start=datetime.datetime(2015, 1, 1, tzinfo=timezone.get_current_timezone()),
            end=datetime.datetime(2015, 12, 31, tzinfo=timezone.get_current_timezone()),
        )

        # Create an org user
        OrganizationUser.objects.create(user=user, organization=org)

        import_record, import_file = self.create_import_file(user, org, cycle,
                                                             import_file_is_espm,
                                                             import_file_source_type,
                                                             import_file_data_state)

        return user, org, import_file, import_record, cycle

    def create_import_file(self, user, org, cycle, espm=True, source_type=ASSESSED_RAW,
                           data_state=DATA_STATE_IMPORT):
        import_record = ImportRecord.objects.create(
            owner=user, last_modified_by=user, super_organization=org
        )
        import_file = ImportFile.objects.create(import_record=import_record, cycle=cycle)
        import_file.is_espm = espm
        import_file.source_type = source_type
        import_file.data_state = data_state
        import_file.save()

        return import_record, import_file

    def tearDown(self):
        super(DataMappingBaseTestCase, self).tearDown()

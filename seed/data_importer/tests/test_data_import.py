# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import csv
import datetime
import json
import logging
import os.path as osp
import copy

from dateutil import parser
from django.core.files import File
from django.utils import timezone
from mock import patch

from seed.data_importer import tasks
from seed.data_importer.models import ImportFile, ImportRecord
from seed.data_importer.tasks import save_raw_data, map_data
from seed.data_importer.tests.util import (
    DataMappingBaseTestCase,
    FAKE_EXTRA_DATA,
    FAKE_MAPPINGS,
    FAKE_ROW,
)
from seed.models import (
    ASSESSED_RAW,
    ASSESSED_BS,
    DATA_STATE_IMPORT,
    PORTFOLIO_RAW,
    Column,
    PropertyState,
    PropertyView,
    TaxLotState,
    Cycle,
)

_log = logging.getLogger(__name__)


class TestMappingPortfolioData(DataMappingBaseTestCase):
    """Tests for dealing with SEED related tasks for mapping data."""

    def setUp(self):
        # Make sure to delete the old mappings and properties because this
        # tests expects very specific column names and properties in order
        filename = getattr(self, 'filename', 'portfolio-manager-sample.csv')
        import_file_source_type = PORTFOLIO_RAW
        self.fake_mappings = FAKE_MAPPINGS['portfolio']
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        self.import_file.load_import_file(
            osp.join(osp.dirname(__file__), '..', '..', 'tests', 'data', filename)
        )

    def test_cached_first_row_order(self):
        """Tests to make sure the first row is saved in the correct order.
        It should be the order of the headers in the original file."""
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)

        expected_first_row = u"Property Id|#*#|Property Name|#*#|Year Ending|#*#|Property Floor Area (Buildings and Parking) (ft2)|#*#|Address 1|#*#|Address 2|#*#|City|#*#|State/Province|#*#|Postal Code|#*#|Year Built|#*#|ENERGY STAR Score|#*#|Site EUI (kBtu/ft2)|#*#|Total GHG Emissions (MtCO2e)|#*#|Weather Normalized Site EUI (kBtu/ft2)|#*#|National Median Site EUI (kBtu/ft2)|#*#|Source EUI (kBtu/ft2)|#*#|Weather Normalized Source EUI (kBtu/ft2)|#*#|National Median Source EUI (kBtu/ft2)|#*#|Parking - Gross Floor Area (ft2)|#*#|Organization|#*#|Generation Date|#*#|Release Date"  # NOQA

        import_file = ImportFile.objects.get(pk=self.import_file.pk)
        first_row = import_file.cached_first_row
        self.assertEqual(first_row, expected_first_row)

    def test_save_raw_data(self):
        """Save information in extra_data, set other attrs."""
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)

        raw_saved = PropertyState.objects.filter(
            import_file=self.import_file,
        ).latest('id')

        self.assertDictEqual(raw_saved.extra_data, self.fake_extra_data)
        self.assertEqual(raw_saved.organization, self.org)

    def test_map_data(self):
        """Save mappings based on user specifications."""
        # Create new import file to test
        import_record = ImportRecord.objects.create(
            owner=self.user, last_modified_by=self.user, super_organization=self.org
        )
        import_file = ImportFile.objects.create(
            import_record=import_record,
            source_type=ASSESSED_RAW,
        )
        import_file.raw_save_done = True
        import_file.save()

        fake_raw_bs = PropertyState.objects.create(
            organization=self.org,
            import_file=import_file,
            extra_data=self.fake_row,
            source_type=ASSESSED_RAW,
            data_state=DATA_STATE_IMPORT,
        )

        self.fake_mappings = copy.deepcopy(FAKE_MAPPINGS['fake_row'])
        Column.create_mappings(self.fake_mappings, self.org, self.user, import_file.pk)
        tasks.map_data(import_file.pk)

        mapped_bs = list(PropertyState.objects.filter(
            import_file=import_file,
            source_type=ASSESSED_BS,
        ))

        self.assertEqual(len(mapped_bs), 1)

        test_bs = mapped_bs[0]
        self.assertNotEqual(test_bs.pk, fake_raw_bs.pk)
        self.assertEqual(test_bs.property_name, self.fake_row['Name'])
        self.assertEqual(test_bs.address_line_1, self.fake_row['Address Line 1'])
        self.assertEqual(
            test_bs.year_built,
            parser.parse(self.fake_row['Year Built']).year
        )

        # Make sure that we saved the extra_data column mappings
        data_columns = Column.objects.filter(
            organization=self.org,
            is_extra_data=True
        ).exclude(table_name='')

        # There's only one piece of data that did not cleanly map.
        # Note that as of 09/15/2016 - extra data still needs to be defined in the mappings, it
        # will no longer magically appear in the extra_data field if the user did not specify to
        # map it!
        self.assertListEqual(
            sorted([d.column_name for d in data_columns]), ['Double Tester']
        )


class TestMappingExampleData(DataMappingBaseTestCase):
    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['portfolio']
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        self.import_file.load_import_file(osp.join(osp.dirname(__file__), 'data', filename))

    def test_mapping(self):
        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.pk)
        tasks.map_data(self.import_file.pk)

        # There are a total of 18 tax lot ids in the import file
        ts = TaxLotState.objects.all()

        self.assertEqual(len(ts), 18)

        # make sure that the new data was loaded correctly and that the lot_number was set
        # appropriately
        ps = PropertyState.objects.filter(address_line_1='2700 Welstone Ave NE')[0]
        self.assertEqual(ps.site_eui, 1202)
        self.assertEqual(ps.lot_number, '11160509')

        ps = PropertyState.objects.filter(address_line_1='521 Elm Street')[0]
        self.assertEqual(ps.site_eui, 1358)
        # The lot_number should also have the normalized code run, then re-delimited
        self.assertEqual(ps.lot_number, '33366555;33366125;33366148')

    def test_promote_properties(self):
        """Test if the promoting of a property works as expected"""
        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.pk)
        tasks.map_data(self.import_file.pk)

        cycle2, _ = Cycle.objects.get_or_create(
            name=u'Hack Cycle 2016',
            organization=self.org,
            start=datetime.datetime(2016, 1, 1, tzinfo=timezone.get_current_timezone()),
            end=datetime.datetime(2016, 12, 31, tzinfo=timezone.get_current_timezone()),
        )

        # make sure that the new data was loaded correctly
        ps = PropertyState.objects.filter(address_line_1='50 Willow Ave SE')[0]
        self.assertEqual(ps.site_eui, 125)

        # Promote the PropertyState to a PropertyView
        pv1 = ps.promote(self.cycle)
        pv2 = ps.promote(self.cycle)  # should just return the same object
        self.assertEqual(pv1, pv2)

        # promote the same state for a new cycle, same data
        pv3 = ps.promote(cycle2)
        self.assertNotEqual(pv3, pv1)

        props = PropertyView.objects.all()
        self.assertEqual(len(props), 2)


# For some reason if you comment out the next two test cases (TestMappingPropertiesOnly and
# TestMappingTaxLotsOnly), the test_views_matching.py file will fail. I cannot figure out
# what is causing this and it is really annoying. Inherenting from DataMappingBaseTestCase
# will delete all the model data upon completion, Maybe because FAKE_MAPPINGS
# is not a copy, rather a pointer?

class TestMappingPropertiesOnly(DataMappingBaseTestCase):
    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['portfolio']
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        self.import_file.load_import_file(osp.join(osp.dirname(__file__), 'data', filename))

    def test_mapping_properties_only(self):
        # update the mappings to not include any taxlot tables in the data
        # note that save_data reads in from the propertystate table, so that will always
        # have entries in the db (for now).
        new_mappings = copy.deepcopy(self.fake_mappings)
        for m in new_mappings:
            if m["to_table_name"] == 'TaxLotState':
                m["to_table_name"] = 'PropertyState'

        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(new_mappings, self.org, self.user, self.import_file.pk)
        tasks.map_data(self.import_file.pk)

        # make sure that no taxlot objects were created
        ts = TaxLotState.objects.all()
        self.assertEqual(len(ts), 0)

        # make sure that the new data was loaded correctly
        ps = PropertyState.objects.filter(address_line_1='2700 Welstone Ave NE')[0]
        self.assertEqual(ps.site_eui, 1202)
        self.assertEqual(ps.extra_data['jurisdiction_tax_lot_id'], '11160509')


class TestMappingTaxLotsOnly(DataMappingBaseTestCase):
    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['portfolio']
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        self.import_file.load_import_file(osp.join(osp.dirname(__file__), 'data', filename))

    def test_mapping_tax_lots_only(self):
        # update the mappings to not include any taxlot tables in the data
        new_mappings = copy.deepcopy(self.fake_mappings)
        for m in new_mappings:
            if m["to_table_name"] == 'PropertyState':
                m["to_table_name"] = 'TaxLotState'

        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(new_mappings, self.org, self.user, self.import_file.pk)
        tasks.map_data(self.import_file.pk)

        # make sure that no taxlot objects were created. the 12 here are the import extra_data.
        ps = PropertyState.objects.all()
        self.assertEqual(len(ps), 14)

        # make sure that the new data was loaded correctly
        ts = TaxLotState.objects.filter(address_line_1='50 Willow Ave SE').first()
        self.assertEqual(ts.extra_data['site_eui'], 125)

        # note that this used to be 2700 Welstone Ave NE but needed to change the check because
        # this has the same jurisdiction_tax_lot_id as others so it was never imported. So assigning
        # the address was never happening because the tax_lot_id was already in use.


class TestPromotingProperties(DataMappingBaseTestCase):
    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['full']
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        self.import_file.load_import_file(osp.join(osp.dirname(__file__), 'data', filename))

    def import_exported_data(self, filename):
        """
        Import test files from Stephen for many-to-many testing. This imports
        and maps the data accordingly. Presently these files are missing a
        couple of attributes to make them valid:
            1) the master campus record to define the pm_property_id
            2) the joins between propertystate and taxlotstate
        """

        # Do a bunch of work to flatten out this temp file that has extra_data
        # asa string representation of a dict
        data = []
        new_keys = set()

        f = osp.join(osp.dirname(__file__), 'data', filename)
        with open(f, 'rb') as csvfile:
            reader = csv.DictReader(csvfile)
            keys = reader.fieldnames
            for row in reader:
                ed = json.loads(row.pop('extra_data'))
                for k, v in ed.iteritems():
                    new_keys.add(k)
                    row[k] = v
                data.append(row)

        # remove the extra_data column and add in the new columns
        keys.remove('extra_data')
        for k in new_keys:
            keys.append(k)

        # save the new file
        new_file_name = 'tmp_{}_flat.csv'.format(
            osp.splitext(osp.basename(filename))[0]
        )
        f_new = osp.join(osp.dirname(__file__), 'data', new_file_name)
        with open(f_new, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys)
            writer.writeheader()
            for d in data:
                writer.writerow(d)

        # save the keys this does not appear to be used anywhere
        new_file_name = 'tmp_{}_keys.csv'.format(
            osp.splitext(osp.basename(filename))[0]
        )
        f_new = osp.join(osp.dirname(__file__), 'data', new_file_name)
        with open(f_new, 'w') as outfile:
            outfile.writelines([str(key) + '\n' for key in keys])

        # Continue saving the raw data
        new_file_name = "tmp_{}_flat.csv".format(
            osp.splitext(osp.basename(filename))[0]
        )
        f_new = osp.join(osp.dirname(__file__), 'data', new_file_name)
        self.import_file.file = File(open(f_new))
        self.import_file.save()

        save_raw_data(self.import_file.id)

        # the mapping is just the 'keys' repeated since the file
        # was created as a database dump
        mapping = []
        for k in keys:
            if k == 'id':
                continue
            mapping.append(
                {
                    "from_field": k,
                    "to_table_name": "PropertyState",
                    "to_field": k
                }
            )

        Column.create_mappings(mapping, self.org, self.user, self.import_file.pk)

        # call the mapping function from the tasks file
        map_data(self.import_file.id)

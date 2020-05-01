# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import copy
import csv
import datetime
import json
import logging
import os.path as osp
import zipfile

from dateutil import parser
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from mock import patch

from config.settings.common import BASE_DIR
from seed.data_importer import tasks
from seed.data_importer.models import ImportFile, ImportRecord
from seed.data_importer.tasks import save_raw_data, map_data
from seed.data_importer.tests.util import (
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
    Meter,
    Scenario,
    BuildingFile,
)
from seed.tests.util import DataMappingBaseTestCase

_log = logging.getLogger(__name__)


class TestDataImport(DataMappingBaseTestCase):
    """Tests for dealing with SEED related tasks for mapping data."""

    def setUp(self):
        # Make sure to delete the old mappings and properties because this
        # tests expects very specific column names and properties in order
        self.maxDiff = None

        filename = getattr(self, 'filename', 'portfolio-manager-sample.csv')
        import_file_source_type = PORTFOLIO_RAW
        self.fake_mappings = FAKE_MAPPINGS['portfolio']
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        filepath = osp.join(osp.dirname(__file__), '..', '..', '..', 'tests', 'data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()

    def test_cached_first_row_order(self):
        """Tests to make sure the first row is saved in the correct order.
        It should be the order of the headers in the original file."""
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            tasks.save_raw_data(self.import_file.pk)

        expected_first_row = 'Property Id|#*#|Property Name|#*#|Year Ending|#*#|Property Floor Area (Buildings and Parking) (ft2)|#*#|Address 1|#*#|Address 2|#*#|City|#*#|State/Province|#*#|Postal Code|#*#|Year Built|#*#|ENERGY STAR Score|#*#|Site EUI (kBtu/ft2)|#*#|Total GHG Emissions (MtCO2e)|#*#|Weather Normalized Site EUI (kBtu/ft2)|#*#|National Median Site EUI (kBtu/ft2)|#*#|Source EUI (kBtu/ft2)|#*#|Weather Normalized Source EUI (kBtu/ft2)|#*#|National Median Source EUI (kBtu/ft2)|#*#|Parking - Gross Floor Area (ft2)|#*#|Organization|#*#|Generation Date|#*#|Release Date'  # NOQA

        import_file = ImportFile.objects.get(pk=self.import_file.pk)
        first_row = import_file.cached_first_row
        self.assertEqual(first_row, expected_first_row)

    def test_save_raw_data(self):
        """Save information in extra_data, set other attrs."""
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            tasks.save_raw_data(self.import_file.pk)

        self.assertEqual(PropertyState.objects.filter(import_file=self.import_file).count(), 512)
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


class TestBuildingSyncImportZipBad(DataMappingBaseTestCase):
    def setUp(self):
        self.maxDiff = None

        # setup the ImportFile for using the example zip file
        filename = 'ex1_no_schemaLocation_and_ex_1.zip'
        filepath = osp.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', filename)

        # Verify we have the expected number of BuildingSync files in the zip file
        with zipfile.ZipFile(filepath, "r", zipfile.ZIP_STORED) as openzip:
            filelist = openzip.infolist()
            xml_files_found = 0
            for f in filelist:
                if '.xml' in f.filename and '__MACOSX' not in f.filename:
                    xml_files_found += 1

            self.assertEqual(xml_files_found, 2)

        import_file_source_type = 'BuildingSync Raw'
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read(),
            content_type="application/zip"
        )
        self.import_file.save()

    def test_save_raw_data_zip(self):
        # -- Act
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            progress_info = tasks.save_raw_data(self.import_file.pk)

        # -- Assert
        self.assertEqual('error', progress_info['status'])
        self.assertIn('Invalid or missing schema specification', progress_info['message'])


class TestBuildingSyncImportZip(DataMappingBaseTestCase):
    def setUp(self):
        self.maxDiff = None

        # setup the ImportFile for using the example zip file
        filename = 'ex_1_and_buildingsync_ex01_measures.zip'
        filepath = osp.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', filename)

        # Verify we have the expected number of BuildingSync files in the zip file
        with zipfile.ZipFile(filepath, "r", zipfile.ZIP_STORED) as openzip:
            filelist = openzip.infolist()
            xml_files_found = 0
            for f in filelist:
                if '.xml' in f.filename and '__MACOSX' not in f.filename:
                    xml_files_found += 1

            self.assertEqual(xml_files_found, 2)

        import_file_source_type = 'BuildingSync Raw'
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read(),
            content_type="application/zip"
        )
        self.import_file.save()

    def test_save_raw_data_zip(self):
        # -- Act
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            tasks.save_raw_data(self.import_file.pk)

        # -- Assert
        self.assertEqual(PropertyState.objects.filter(import_file=self.import_file).count(), 2)
        raw_saved = PropertyState.objects.filter(
            import_file=self.import_file,
        ).latest('id')
        self.assertEqual(raw_saved.organization, self.org)

    def test_map_data_zip(self):
        # -- Setup
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            tasks.save_raw_data(self.import_file.pk)
        self.assertEqual(PropertyState.objects.filter(import_file=self.import_file).count(), 2)

        # -- Act
        progress_info = tasks.map_data(self.import_file.pk)

        # -- Assert
        self.assertEqual('success', progress_info['status'])
        # verify there were no errors with the files
        self.assertEqual({}, progress_info.get('file_info', {}))
        ps = PropertyState.objects.filter(address_line_1='123 Main St',
                                          import_file=self.import_file)
        self.assertEqual(len(ps), 2)


class TestBuildingSyncImportXml(DataMappingBaseTestCase):
    def setUp(self):
        self.maxDiff = None

        filename = 'buildingsync_v2_0_bricr_workflow.xml'
        filepath = osp.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', filename)

        import_file_source_type = 'BuildingSync Raw'
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read(),
            content_type="application/xml"
        )
        self.import_file.save()

    def test_save_raw_data_xml(self):
        # -- Act
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            tasks.save_raw_data(self.import_file.pk)

        # -- Assert
        self.assertEqual(PropertyState.objects.filter(import_file=self.import_file).count(), 1)
        raw_saved = PropertyState.objects.filter(
            import_file=self.import_file,
        ).latest('id')
        self.assertEqual(raw_saved.organization, self.org)

    def test_map_data_xml(self):
        # -- Setup
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            tasks.save_raw_data(self.import_file.pk)
        self.assertEqual(PropertyState.objects.filter(import_file=self.import_file).count(), 1)

        # -- Act
        progress_info = tasks.map_data(self.import_file.pk)

        # -- Assert
        self.assertEqual('success', progress_info['status'])
        # verify there were no errors with the files
        self.assertEqual({}, progress_info.get('file_info', {}))

        ps = PropertyState.objects.filter(address_line_1='123 MAIN BLVD',
                                          import_file=self.import_file)
        self.assertEqual(len(ps), 1)

    def test_map_data_xml_is_idempotent(self):
        # -- Setup
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            tasks.save_raw_data(self.import_file.pk)
        self.assertEqual(PropertyState.objects.filter(import_file=self.import_file).count(), 1)

        # -- Act
        # Call map data multiple times
        tasks.map_data(self.import_file.pk)
        tasks.map_data(self.import_file.pk, remap=True)
        progress_info = tasks.map_data(self.import_file.pk, remap=True)

        # -- Assert
        self.assertEqual('success', progress_info['status'])
        # verify there were no errors with the files
        self.assertEqual({}, progress_info.get('file_info', {}))

        ps = PropertyState.objects.filter(address_line_1='123 MAIN BLVD',
                                          import_file=self.import_file)
        self.assertEqual(len(ps), 1)

        building_file = BuildingFile.objects.filter(property_state=ps[0].id)
        self.assertEqual(len(building_file), 1)

    def test_map_all_models_xml(self):
        # -- Setup
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            tasks.save_raw_data(self.import_file.pk)
        self.assertEqual(PropertyState.objects.filter(import_file=self.import_file).count(), 1)

        progress_info = tasks.map_data(self.import_file.pk)
        self.assertEqual('success', progress_info['status'])
        # verify there were no errors with the files
        self.assertEqual({}, progress_info.get('file_info', {}))

        ps = PropertyState.objects.filter(address_line_1='123 MAIN BLVD',
                                          import_file=self.import_file)
        self.assertEqual(len(ps), 1)

        # -- Act
        tasks.map_additional_models(self.import_file.pk)

        # -- Assert
        ps = PropertyState.objects.filter(address_line_1='123 MAIN BLVD', import_file=self.import_file)

        self.assertEqual(ps.count(), 1)

        # verify the property view, scenario and meter data were created
        pv = PropertyView.objects.filter(state=ps[0])
        self.assertEqual(pv.count(), 1)

        meters = Meter.objects.filter(property=pv[0].property)
        self.assertEqual(meters.count(), 6)

        scenario = Scenario.objects.filter(property_state=ps[0])
        self.assertEqual(scenario.count(), 3)


class TestBuildingSyncImportInvalid(DataMappingBaseTestCase):
    def setUp(self):
        self.maxDiff = None

        filename = 'ex_1_no_street_address.xml'
        filepath = osp.join(osp.dirname(__file__), '../../..', 'building_sync', 'tests', 'data', filename)

        import_file_source_type = 'BuildingSync Raw'
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read(),
            content_type="application/xml"
        )
        self.import_file.save()

    def test_map_xml_missing_street_address_fails(self):
        # -- Setup
        with patch.object(ImportFile, 'cache_first_rows', return_value=None):
            tasks.save_raw_data(self.import_file.pk)
        self.assertEqual(PropertyState.objects.filter(import_file=self.import_file).count(), 1)

        # -- Act
        progress_info = tasks.map_data(self.import_file.pk)

        # -- Assert
        ps = PropertyState.objects.filter(address_line_1='123 Main St', import_file=self.import_file)
        self.assertEqual(len(ps), 0)

        self.assertIn('file_info', progress_info)
        # grab the file name which is changed on upload by django (ie we can't reference directly)
        uploaded_file_name = list(progress_info['file_info'].keys())[0]
        self.assertNotEqual(0, len(progress_info['file_info'][uploaded_file_name]['errors']))


class TestMappingExampleData(DataMappingBaseTestCase):
    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['portfolio']
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        filepath = osp.join(osp.dirname(__file__), '..', 'data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()

    def test_mapping(self):
        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.pk)
        tasks.map_data(self.import_file.pk)

        # There are a total of 18 tax lot ids in the import file
        ts = TaxLotState.objects.all()

        self.assertEqual(len(ts), 18)

        # make sure that the new data was loaded correctly and that the lot_number was set
        # appropriately
        ps = PropertyState.objects.filter(address_line_1='2700 Welstone Ave NE')[0]
        self.assertEqual(ps.site_eui.magnitude, 1202)
        self.assertEqual(ps.lot_number, '11160509')

        ps = PropertyState.objects.filter(address_line_1='521 Elm Street')[0]
        self.assertEqual(ps.site_eui.magnitude, 1358)
        # The lot_number should also have the normalized code run, then re-delimited
        self.assertEqual(ps.lot_number, '333/66555;333/66125;333/66148')

    def test_promote_properties(self):
        """Test if the promoting of a property works as expected"""
        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.pk)
        tasks.map_data(self.import_file.pk)

        cycle2, _ = Cycle.objects.get_or_create(
            name='Hack Cycle 2016',
            organization=self.org,
            start=datetime.datetime(2016, 1, 1, tzinfo=timezone.get_current_timezone()),
            end=datetime.datetime(2016, 12, 31, tzinfo=timezone.get_current_timezone()),
        )

        # make sure that the new data was loaded correctly
        ps = PropertyState.objects.filter(address_line_1='50 Willow Ave SE')[0]
        self.assertEqual(ps.site_eui.magnitude, 125)

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
        filepath = osp.join(osp.dirname(__file__), '..', 'data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()

    def test_mapping_properties_only(self):
        # update the mappings to not include any taxlot tables in the data
        # note that save_data reads in from the propertystate table, so that will always
        # have entries in the db (for now).
        new_mappings = copy.deepcopy(self.fake_mappings)
        for m in new_mappings:
            if m["to_table_name"] == 'TaxLotState':
                m["to_table_name"] = 'PropertyState'

        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(new_mappings, self.org, self.user, self.import_file.pk)
        tasks.map_data(self.import_file.pk)

        # make sure that no taxlot objects were created
        ts = TaxLotState.objects.all()
        self.assertEqual(len(ts), 0)

        # make sure that the new data was loaded correctly
        ps = PropertyState.objects.filter(address_line_1='2700 Welstone Ave NE')[0]
        self.assertEqual(ps.site_eui.magnitude, 1202)
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
        filepath = osp.join(osp.dirname(__file__), '..', 'data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()

    def test_mapping_tax_lots_only(self):
        # update the mappings to not include any taxlot tables in the data
        new_mappings = copy.deepcopy(self.fake_mappings)
        for m in new_mappings:
            if m["to_table_name"] == 'PropertyState':
                m["to_table_name"] = 'TaxLotState'

        tasks.save_raw_data(self.import_file.pk)
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
        filepath = osp.join(osp.dirname(__file__), 'data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()

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
                for k, v in ed.items():
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


class TestPostalCode(DataMappingBaseTestCase):
    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties-postal.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        filepath = osp.join(osp.dirname(__file__), '..', 'data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()

    def test_postal_code_property(self):

        new_mappings = copy.deepcopy(self.fake_mappings['portfolio'])

        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(new_mappings, self.org, self.user, self.import_file.pk)
        tasks.map_data(self.import_file.pk)

        # get mapped property postal_code
        ps = PropertyState.objects.filter(address_line_1='11 Ninth Street')[0]
        self.assertEqual(ps.postal_code, '00340')

        ps = PropertyState.objects.filter(address_line_1='20 Tenth Street')[0]
        self.assertEqual(ps.postal_code, '00000')

        ps = PropertyState.objects.filter(address_line_1='93029 Wellington Blvd')[0]
        self.assertEqual(ps.postal_code, '00001-0002')

    def test_postal_code_taxlot(self):

        new_mappings = copy.deepcopy(self.fake_mappings['taxlot'])

        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(new_mappings, self.org, self.user, self.import_file.pk)
        tasks.map_data(self.import_file.pk)

        # get mapped taxlot postal_code
        ts = TaxLotState.objects.filter(address_line_1='35 Tenth Street').first()

        if ts is None:
            raise TypeError("Invalid Taxlot Address!")
        self.assertEqual(ts.postal_code, '00333')

        ts = TaxLotState.objects.filter(address_line_1='93030 Wellington Blvd').first()

        if ts is None:
            raise TypeError("Invalid Taxlot Address!")
        self.assertEqual(ts.postal_code, '00000-0000')

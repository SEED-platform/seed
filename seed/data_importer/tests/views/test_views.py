# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import json
import os.path as osp

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse_lazy

from seed.data_importer import tasks
from seed.data_importer.models import ImportFile, ImportRecord
from seed.data_importer.tests.util import (
    FAKE_EXTRA_DATA,
    FAKE_MAPPINGS,
    FAKE_ROW,
)
from seed.data_importer.views import convert_first_five_rows_to_list
from seed.landing.models import SEEDUser as User
from seed.lib.mcm.reader import ROW_DELIMITER
from seed.models import (
    PORTFOLIO_RAW,
)
from seed.tests.util import DataMappingBaseTestCase


def first_five_rows_helper(headers, raw_data):
    save_format = '\n'.join([ROW_DELIMITER.join(row) for row in raw_data])
    expected = [dict(zip(headers, row)) for row in raw_data]
    return save_format, expected


class DataImporterViewTests(DataMappingBaseTestCase):
    """
    Tests of the data_importer views (and the objects they create).
    """

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(email='test_user@demo.com', **user_details)
        self.client.login(**user_details)

    def test_get_raw_column_names(self):
        """Make sure we get column names back in a format we expect."""
        import_record = ImportRecord.objects.create()
        expected_raw_columns = ['tax id', 'name', 'etc.']
        expected_saved_format = ROW_DELIMITER.join(expected_raw_columns)
        import_file = ImportFile.objects.create(
            import_record=import_record,
            cached_first_row=expected_saved_format
        )

        # Just make sure we were saved correctly
        self.assertEqual(import_file.cached_first_row, expected_saved_format)

        url = reverse_lazy("api:v2:import_files-raw-column-names", args=[import_file.pk])
        resp = self.client.get(
            url, content_type='application/json'
        )

        body = json.loads(resp.content)

        self.assertEqual(body.get('raw_columns', []), expected_raw_columns)

    def test_get_first_five_rows(self):
        """Make sure we get our first five rows back correctly."""
        import_record = ImportRecord.objects.create()
        expected_raw_columns = ['tax id', 'name', 'etc.']
        expected_raw_rows = [
            ['02023', '12 Jefferson St.', 'etc.'],
            ['12433', '23 Washington St.', 'etc.'],
            ['04422', '4 Adams St.', 'etc.'],
        ]

        expected = [
            dict(zip(expected_raw_columns, row)) for row in expected_raw_rows
        ]
        expected_saved_format = '\n'.join([
            ROW_DELIMITER.join(row) for row
            in expected_raw_rows
        ])
        import_file = ImportFile.objects.create(
            import_record=import_record,
            cached_first_row=ROW_DELIMITER.join(expected_raw_columns),
            cached_second_to_fifth_row=expected_saved_format
        )

        # Just make sure we were saved correctly
        self.assertEqual(
            import_file.cached_second_to_fifth_row, expected_saved_format
        )

        url = reverse_lazy("api:v2:import_files-first-five-rows", args=[import_file.pk])
        resp = self.client.get(
            url, content_type='application/json'
        )

        body = json.loads(resp.content)

        self.assertEqual(body.get('first_five_rows', []), expected)

    def test_get_first_five_rows_simple(self):
        header = ['id', 'name', 'etc']
        raw_data = [
            ['1', 'test_1', 'simple'],
            ['2', 'test_2', 'example'],
        ]
        save_format, expected = first_five_rows_helper(header, raw_data)
        converted = convert_first_five_rows_to_list(header, save_format)
        self.assertEqual(converted, expected)

    def test_get_first_five_rows_newline_middle(self):
        header = ['id', 'name', 'etc']
        raw_data = [
            ['1', 'test\nmiddle', 'new'],
            ['2', 'test_2', 'single'],
        ]
        save_format, expected = first_five_rows_helper(header, raw_data)
        converted = convert_first_five_rows_to_list(header, save_format)
        self.assertEqual(converted, expected)

    def test_get_first_five_rows_newline_end(self):
        header = ['id', 'name', 'etc']
        raw_data = [
            ['1', 'test_1', 'new\nat_end'],
            ['2', 'test_2', 'single'],
        ]
        save_format, expected = first_five_rows_helper(header, raw_data)
        converted = convert_first_five_rows_to_list(header, save_format)
        self.assertEqual(converted, expected)

    def test_get_first_five_rows_newline_various(self):
        header = ['id', 'name', 'etc']
        raw_data = [
            ['1', 'test_1', 'new\n\nat_end\n\n'],
            ['2', 'test_2', 'single\nat_end_too\n'],
        ]
        save_format, expected = first_five_rows_helper(header, raw_data)
        converted = convert_first_five_rows_to_list(header, save_format)
        self.assertEqual(converted, expected)

    def test_get_first_five_rows_newline_should_work(self):
        """
        This test shows where this logic breaks down. There is no other way around this issue
        unless we move away from the |#*#| syntax and store it in a more supported CSV format
        syntax with quotes and escape characters
        :return:
        """
        header = ['id', 'name', 'etc']
        raw_data = [
            ['1', 'test_1', 'new\n\nat_end\n\n'],
            ['2\nThisBreaksMe', 'test_2', 'single\nat_end_too\n'],
        ]
        save_format, expected = first_five_rows_helper(header, raw_data)
        converted = convert_first_five_rows_to_list(header, save_format)

        # This test passes as it is the expected behavior, even though it is wrong.
        # the ID of row 2 should be 2\nThisBreaksMe, but the convert_first_five_to_list does
        # not know that the crlf was part of the field and not the line break.
        self.assertNotEqual(converted, expected)

    def test_get_first_five_rows_one_column(self):
        header = ['id']
        raw_data = [
            ['1'],
            ['2'],
        ]
        save_format, expected = first_five_rows_helper(header, raw_data)
        converted = convert_first_five_rows_to_list(header, save_format)
        self.assertEqual(converted, expected)

    def test_get_first_five_rows_one_column_with_crlf(self):
        header = ['id']
        raw_data = [
            ['1'],
            ['2\nshould_be_the_id'],
        ]
        save_format, expected = first_five_rows_helper(header, raw_data)
        converted = convert_first_five_rows_to_list(header, save_format)

        # This test fails on purpose becasue the format of the first five rows will not
        # support this use case.
        self.assertNotEqual(converted, expected)


class TestDataImportViewWithCRLF(DataMappingBaseTestCase):
    """Tests for dealing with SEED related tasks for mapping data."""

    def setUp(self):
        filename = getattr(self, 'filename', 'portfolio-manager-sample-with-crlf.xlsx')
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

        tasks.save_raw_data(self.import_file.pk)

        # reload the import file
        self.import_file = ImportFile.objects.get(pk=self.import_file.pk)
        first_row = self.import_file.cached_first_row
        expected_first_row = "Property Id|#*#|Property Name|#*#|Year Ending|#*#|Property Notes|#*#|Address 1|#*#|Address 2|#*#|City|#*#|State/Province|#*#|Postal Code|#*#|Year Built|#*#|ENERGY STAR Score|#*#|Site EUI (kBtu/ft2)|#*#|Total GHG Emissions (MtCO2e)|#*#|Weather Normalized Site EUI (kBtu/ft2)|#*#|National Median Site EUI (kBtu/ft2)|#*#|Source EUI (kBtu/ft2)|#*#|Weather Normalized Source EUI (kBtu/ft2)|#*#|Parking - Gross Floor Area (ft2)|#*#|Organization|#*#|Generation Date|#*#|Release Date"
        self.assertEqual(first_row, expected_first_row)

        # setup the API access
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.client.login(**user_details)

        url = reverse_lazy("api:v2:import_files-first-five-rows", args=[self.import_file.pk])
        resp = self.client.get(url, content_type='application/json')
        body = json.loads(resp.content)
        self.assertEqual(body['status'], 'success')
        self.assertEqual(len(body['first_five_rows']), 5)

        expected_property_notes = 'These are property notes:\n- Nice building\n- Large atrium\n- Extra crlf here'
        self.assertEqual(body['first_five_rows'][0]['Property Notes'], expected_property_notes)

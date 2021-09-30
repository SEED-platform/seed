# !/usr/bin/env python
# encoding: utf-8

import ast
import copy
import json
import os
from datetime import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse, reverse_lazy
from django.utils.timezone import get_current_timezone
from seed.data_importer import tasks
from seed.data_importer.models import ImportFile, ImportRecord
from seed.data_importer.tests.util import (FAKE_EXTRA_DATA, FAKE_MAPPINGS,
                                           FAKE_ROW)
from seed.data_importer.views import (ImportFileViewSet,
                                      convert_first_five_rows_to_list)
from seed.landing.models import SEEDUser as User
from seed.lib.mcm.reader import ROW_DELIMITER
from seed.lib.superperms.orgs.models import Organization
from seed.models import (ASSESSED_RAW, DATA_STATE_MAPPING, DATA_STATE_MATCHING,
                         MERGE_STATE_NEW, MERGE_STATE_UNKNOWN, PORTFOLIO_RAW,
                         Column, PropertyState, PropertyView)
from seed.test_helpers.fake import (FakeCycleFactory, FakePropertyFactory,
                                    FakePropertyStateFactory)
from seed.tests.util import DataMappingBaseTestCase
from seed.utils.organizations import create_organization


class TestMeterViewSet(DataMappingBaseTestCase):
    def setUp(self):
        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_user(
            email='test_user@demo.com', **self.user_details
        )
        self.org, _, _ = create_organization(self.user)

        # For some reason, defaults weren't established consistently for each test.
        self.org.display_meter_units = Organization._default_display_meter_units.copy()
        self.org.save()
        self.client.login(**self.user_details)

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id

        # pm_property_ids must match those within example-monthly-meter-usage.xlsx
        self.pm_property_id_1 = '5766973'
        self.pm_property_id_2 = '5766975'

        property_details['pm_property_id'] = self.pm_property_id_1
        state_1 = PropertyState(**property_details)
        state_1.save()
        self.state_1 = PropertyState.objects.get(pk=state_1.id)

        property_details['pm_property_id'] = self.pm_property_id_2
        state_2 = PropertyState(**property_details)
        state_2.save()
        self.state_2 = PropertyState.objects.get(pk=state_2.id)

        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_1 = self.property_factory.get_property()
        self.property_2 = self.property_factory.get_property()

        self.property_view_1 = PropertyView.objects.create(property=self.property_1, cycle=self.cycle, state=self.state_1)
        self.property_view_2 = PropertyView.objects.create(property=self.property_2, cycle=self.cycle, state=self.state_2)

        self.import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)

        # This file has multiple tabs
        filename = "example-pm-monthly-meter-usage.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

    def test_parsed_meters_confirmation_verifies_energy_type_and_units(self):
        url = reverse('api:v3:import_files-pm-meters-preview', kwargs={'pk': self.import_file.id})
        url += f'?organization_id={self.org.pk}'
        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = [
            {
                "parsed_type": "Electric - Grid",
                "parsed_unit": "kBtu (thousand Btu)",
            },
            {
                "parsed_type": "Natural Gas",
                "parsed_unit": "kBtu (thousand Btu)",
            },
        ]

        self.assertCountEqual(result_dict.get("validated_type_units"), expectation)

    def test_parsed_meters_confirmation_verifies_energy_type_and_units_and_ignores_invalid_types_and_units(self):
        filename = "example-pm-monthly-meter-usage-with-unknown-types-and-units.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        import_file_with_invalids = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

        url = reverse('api:v3:import_files-pm-meters-preview', kwargs={'pk': import_file_with_invalids.id})
        url += f'?organization_id={self.org.pk}'
        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = [
            {
                "parsed_type": "Electric - Grid",
                "parsed_unit": "kBtu (thousand Btu)",
            },
            {
                "parsed_type": "Natural Gas",
                "parsed_unit": "kBtu (thousand Btu)",
            },
        ]

        self.assertCountEqual(result_dict.get("validated_type_units"), expectation)

    def test_parsed_meters_confirmation_returns_pm_property_ids_and_corresponding_incoming_counts(self):
        url = reverse('api:v3:import_files-pm-meters-preview', kwargs={'pk': self.import_file.id})
        url += f'?organization_id={self.org.pk}'
        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = [
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-0",
                "type": 'Electric - Grid',
                "incoming": 2,
            }, {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-1",
                "type": 'Natural Gas',
                "incoming": 2,
            }, {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-0",
                "type": 'Electric - Grid',
                "incoming": 2,
            }, {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-1",
                "type": 'Natural Gas',
                "incoming": 2,
            },
        ]

        self.assertCountEqual(result_dict.get("proposed_imports"), expectation)

    def test_parsed_meters_confirmation_also_verifies_cost_type_and_units_and_counts(self):
        filename = "example-pm-monthly-meter-usage-2-cost-meters.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        cost_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

        url = reverse('api:v3:import_files-pm-meters-preview', kwargs={'pk': cost_import_file.id})
        url += f'?organization_id={self.org.pk}'
        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        validated_type_units = [
            {
                "parsed_type": "Electric - Grid",
                "parsed_unit": "kBtu (thousand Btu)",
            },
            {
                "parsed_type": "Natural Gas",
                "parsed_unit": "kBtu (thousand Btu)",
            },
            {
                "parsed_type": "Cost",
                "parsed_unit": "US Dollars",
            },
        ]

        self.assertCountEqual(result_dict.get("validated_type_units"), validated_type_units)

        proposed_imports = [
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-0",
                "type": 'Electric - Grid',
                "incoming": 2,
            }, {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-1",
                "type": 'Natural Gas',
                "incoming": 2,
            }, {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-0",
                "type": 'Cost',
                "incoming": 2,
            }, {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-1",
                "type": 'Cost',
                "incoming": 2,
            }, {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-0",
                "type": 'Electric - Grid',
                "incoming": 2,
            }, {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-1",
                "type": 'Natural Gas',
                "incoming": 2,
            },
        ]

        self.assertCountEqual(result_dict.get("proposed_imports"), proposed_imports)

        # Verify this works for Org with CAN thermal conversions
        self.org.thermal_conversion_assumption = Organization.CAN
        self.org.save()

        can_result = self.client.get(url)
        can_result_dict = ast.literal_eval(can_result.content.decode("utf-8"))

        validated_type_units[2] = {
            "parsed_type": "Cost",
            "parsed_unit": "CAN Dollars",
        }

        self.assertCountEqual(can_result_dict.get("validated_type_units"), validated_type_units)

    def test_green_button_parsed_meters_confirmation_returns_a_green_button_id_incoming_counts_and_parsed_type_units_and_saves_property_id_to_file_cache(self):
        filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        xml_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="GreenButton",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

        url = reverse('api:v3:import_files-greenbutton-meters-preview', kwargs={'pk': xml_import_file.id})
        url += f'?organization_id={self.org.pk}&view_id={self.property_view_1.id}'
        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        proposed_imports = [
            {
                "source_id": '409483',
                "property_id": self.property_1.id,
                "type": 'Electric - Grid',
                "incoming": 2,
            },
        ]

        validated_type_units = [
            {
                "parsed_type": "Electric - Grid",
                "parsed_unit": "Wh (Watt-hours)",
            },
        ]

        self.assertEqual(result_dict['proposed_imports'], proposed_imports)
        self.assertEqual(result_dict['validated_type_units'], validated_type_units)

        refreshed_import_file = ImportFile.objects.get(pk=xml_import_file.id)
        self.assertEqual(refreshed_import_file.matching_results_data, {'property_id': self.property_view_1.property_id})

    def test_parsed_meters_confirmation_returns_unlinkable_pm_property_ids(self):
        PropertyState.objects.all().delete()

        url = reverse('api:v3:import_files-pm-meters-preview', kwargs={'pk': self.import_file.id})
        url += f'?organization_id={self.org.pk}'
        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = [
            {
                "portfolio_manager_id": "5766973",
            },
            {
                "portfolio_manager_id": "5766975",
            },
        ]

        self.assertCountEqual(result_dict.get("unlinkable_pm_ids"), expectation)


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
        self.user = User.objects.create_user(email='test_user@demo.com', **user_details)
        self.org, _, _ = create_organization(self.user, "my org")
        self.client.login(**user_details)

    def test_get_raw_column_names(self):
        """Make sure we get column names back in a format we expect."""
        import_record = ImportRecord.objects.create(super_organization=self.org)
        expected_raw_columns = ['tax id', 'name', 'etc.']
        expected_saved_format = ROW_DELIMITER.join(expected_raw_columns)
        import_file = ImportFile.objects.create(
            import_record=import_record,
            cached_first_row=expected_saved_format
        )

        # Just make sure we were saved correctly
        self.assertEqual(import_file.cached_first_row, expected_saved_format)

        url = reverse_lazy("api:v3:import_files-raw-column-names", args=[import_file.pk])
        resp = self.client.get(
            url, {'organization_id': self.org.id}, content_type='application/json'
        )

        body = json.loads(resp.content)

        self.assertEqual(body.get('raw_columns', []), expected_raw_columns)

    def test_get_first_five_rows(self):
        """Make sure we get our first five rows back correctly."""
        import_record = ImportRecord.objects.create(super_organization=self.org)
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

        url = reverse_lazy("api:v3:import_files-first-five-rows", args=[import_file.pk])
        resp = self.client.get(
            url, {'organization_id': self.org.id}, content_type='application/json'
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

    def test_get_check_for_meters_tab_returns_true_when_meter_entries_tab_present(self):
        # create import file record with Meter Entries tab
        import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)
        filename = "example-pm-monthly-meter-usage.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        import_file = ImportFile.objects.create(
            import_record=import_record,
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
        )

        # hit endpoint with record ID
        url = reverse_lazy('api:v3:import_files-check-meters-tab-exists', args=[import_file.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url)

        # verify return true
        body = json.loads(response.content)
        self.assertEqual(body.get('data'), True)

    def test_get_check_for_meters_tab_returns_true_when_monthly_usage_tab_present(self):
        # create import file record with Meter Entries tab
        import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)
        filename = "example-data-request-response.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        import_file = ImportFile.objects.create(
            import_record=import_record,
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
        )

        # hit endpoint with record ID
        url = reverse_lazy('api:v3:import_files-check-meters-tab-exists', args=[import_file.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url)

        # verify return true
        body = json.loads(response.content)
        self.assertEqual(body.get('data'), True)

    def test_get_check_for_meters_tab_returns_false(self):
        # create import file record without either a Meter Entries or a Monthly Usage tab
        import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)
        filename = "portfolio-manager-sample.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        import_file = ImportFile.objects.create(
            import_record=import_record,
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
        )

        # hit endpoint with record ID
        url = reverse_lazy('api:v3:import_files-check-meters-tab-exists', args=[import_file.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url)

        # verify return false
        body = json.loads(response.content)
        self.assertEqual(body.get('data'), False)

    def test_get_check_for_meters_tab_returns_false_when_not_xlsx(self):
        # create import file record that's not an xlsx
        import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)
        filename = "san-jose-test-taxlots.csv"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        import_file = ImportFile.objects.create(
            import_record=import_record,
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
        )

        # hit endpoint with record ID
        url = reverse_lazy('api:v3:import_files-check-meters-tab-exists', args=[import_file.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url)

        # verify return false
        body = json.loads(response.content)
        self.assertEqual(body.get('data'), False)

    def test_post_reuse_inventory_file_for_meters_creates_new_import_file_based_on_the_same_file_and_returns_the_new_id(self):
        # create import file record with Meter Entries tab
        import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)
        filename = "example-pm-monthly-meter-usage.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        import_file = ImportFile.objects.create(
            import_record=import_record,
            uploaded_filename=filename,
            mapping_done=True,
            source_type="Assessed Raw",
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
        )

        # hit endpoint with record ID
        url = reverse_lazy('api:v3:import_files-reuse-inventory-file-for-meters') + '?organization_id=' + str(self.org.id)
        response = self.client.post(
            url,
            data=json.dumps({"import_file_id": import_file.id}),
            content_type='application/json'
        )

        # check that the new and old file reference the same 'file'
        newest_import_file = ImportFile.objects.order_by('-id').first()
        body = json.loads(response.content)

        self.assertEqual(body.get('import_file_id'), newest_import_file.id)
        self.assertEqual(import_file.file, newest_import_file.file)


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
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename
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

        url = reverse_lazy("api:v3:import_files-first-five-rows", args=[self.import_file.pk])
        resp = self.client.get(url, {'organization_id': self.org.pk}, content_type='application/json')
        body = json.loads(resp.content)
        self.assertEqual(body['status'], 'success', body)
        self.assertEqual(len(body['first_five_rows']), 5)

        expected_property_notes = 'These are property notes:\n- Nice building\n- Large atrium\n- Extra crlf here'
        self.assertEqual(body['first_five_rows'][0]['Property Notes'], expected_property_notes)


class DeleteFileViewTests(DataMappingBaseTestCase):
    """
    Tests of the SEED Building Detail page
    """

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_user(**user_details)
        self.org, _, _ = create_organization(self.user, "test-organization-a")
        self.org_2, _, _ = create_organization()

        self.import_record = ImportRecord.objects.create(owner=self.user,
                                                         super_organization=self.org)
        self.import_record_2 = ImportRecord.objects.create(owner=self.user,
                                                           super_organization=self.org_2)
        self.import_file_1 = ImportFile.objects.create(import_record=self.import_record)
        self.import_file_2 = ImportFile.objects.create(import_record=self.import_record_2)

        self.client.login(**user_details)

    def test_delete_file_no_perms(self):
        """ tests the delete_file request invalid request"""
        url = reverse("api:v3:import_files-detail", args=[self.import_file_2.pk])
        response = self.client.delete(
            url + '?organization_id=' + str(self.org.pk),
            content_type='application/json',
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data.get('status'), 'error')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ImportFile.objects.all().count(), 2)

    def test_delete_file_wrong_org(self):
        """ tests the delete_file request with wrong org"""
        url = reverse("api:v3:import_files-detail", args=[self.import_file_2.pk])
        response = self.client.delete(
            url + '?organization_id=' + str(self.org_2.pk),
            content_type='application/json',
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data.get('status'), 'error')
        self.assertEqual(ImportFile.objects.all().count(), 2)


class TestViewsMatching(DataMappingBaseTestCase):
    def setUp(self):
        data_importer_data_dir = os.path.join(os.path.dirname(__file__), '..', 'data_importer', 'tests', 'data')
        filename = getattr(self, 'filename', 'example-data-properties.xlsx')
        self.fake_mappings = copy.copy(FAKE_MAPPINGS['portfolio'])
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        filepath = os.path.join(data_importer_data_dir, filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()
        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.id)
        tasks.map_data(self.import_file.pk)
        tasks.geocode_and_match_buildings_task(self.import_file.id)

        # import second file that is currently the same, but should be slightly different
        filename_2 = getattr(self, 'filename', 'example-data-properties-small-changes.xlsx')
        _, self.import_file_2 = self.create_import_file(self.user, self.org, self.cycle)
        filepath = os.path.join(data_importer_data_dir, filename_2)
        self.import_file_2.file = SimpleUploadedFile(
            name=filename_2,
            content=open(filepath, 'rb').read()
        )
        self.import_file_2.save()

        tasks.save_raw_data(self.import_file_2.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file_2.id)
        tasks.map_data(self.import_file_2.pk)
        tasks.geocode_and_match_buildings_task(self.import_file_2.id)

        # for api tests
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.client.login(**user_details)

    def test_get_mapping_results_returns_numbers_for_unitted_values(self):
        url = reverse("api:v3:import_files-mapping-results", args=[self.import_file.pk])
        url += f'?organization_id={self.org.pk}'
        resp = self.client.post(url, content_type='application/json')

        self.assertEqual(200, resp.status_code)
        mapped_property = json.loads(resp.content)['properties'][0]
        unitted_column_names = ['gross_floor_area', 'site_eui']
        for column_name, val in mapped_property.items():
            for unitted_column_name in unitted_column_names:
                if column_name.startswith(unitted_column_name):
                    self.assertTrue(isinstance(val, (float, int)))

    # def test_use_description_updated(self):
    #     """
    #     Most of the buildings will match, except the ones that haven't changed.
    #         124 Mainstreet
    #
    #     TODO: There's an error with automatic matching of 93029 Wellington Blvd - College/University
    #     TODO: There are significant issues with the matching here!
    #     """
    #     state_ids = list(
    #         PropertyView.objects.filter(cycle=self.cycle).select_related('state').values_list(
    #             'state_id', flat=True))
    #     self.assertEqual(len(state_ids), 14)
    #
    #     property_states = PropertyState.objects.filter(id__in=state_ids)
    #     # Check that the use descriptions have been updated to the new ones
    #     # expected = ['Bar', 'Building', 'Club', 'Coffee House',
    #     #             'Daycare', 'Diversity Building', 'House', 'Multifamily Housing',
    #     #             'Multistorys', 'Pizza House', 'Residence', 'Residence', 'Residence',
    #     #             'Swimming Pool']
    #
    #     # print(sorted([p.use_description for p in property_states]))
    #     results = sorted([p.use_description for p in property_states])
    #     self.assertTrue('Bar' in results)
    #     self.assertTrue('Building' in results)
    #     self.assertTrue('Club' in results)
    #     self.assertTrue('Coffee House' in results)
    #
    #     logs = PropertyAuditLog.objects.filter(state_id__in=state_ids)
    #     self.assertEqual(logs.count(), 14)
    #
    # def test_get_filtered_mapping_results_date(self):
    #     url = reverse("api:v3:import_files-filtered-mapping-results", args=[self.import_file.pk])
    #     resp = self.client.post(
    #         url, data=json.dumps({"organization_id": self.org.id}), content_type='application/json'
    #     )
    #
    #     body = json.loads(resp.content)
    #     for prop in body['properties']:
    #         if prop['custom_id_1'] == '1':
    #             self.assertEqual(body['properties'][0]['recent_sale_date'], '1888-01-05T08:00:00')
    #         if prop['custom_id_1'] == '4':
    #             self.assertEqual(body['properties'][1]['recent_sale_date'], '2017-01-05T08:00:00')
    #         if prop['custom_id_1'] == '6':
    #             self.assertEqual(body['properties'][2]['recent_sale_date'], None)
    #
    # def test_get_filtered_mapping_results(self):
    #     url = reverse("api:v3:import_files-filtered-mapping-results", args=[self.import_file_2.pk])
    #     resp = self.client.post(
    #         url, data=json.dumps({"get_coparents": True}), content_type='application/json'
    #     )
    #
    #     body = json.loads(resp.content)
    #
    #     # spot check the results
    #     expected = {
    #         "lot_number": "1552813",
    #         "extra_data": {
    #             "data_007": "a"
    #         },
    #         "coparent": {
    #             "lot_number": "1552813",
    #             "owner_email": "ULLC@gmail.com",
    #             "year_ending": "2015-12-31",
    #             "owner": "U LLC",
    #             "site_eui": 125.0,
    #             "custom_id_1": "1",
    #             "city": "Rust",
    #             "property_notes": "Case A-1: 1 Property, 1 Tax Lot",
    #             "pm_property_id": "2264",
    #             "use_description": "Hotel",
    #             "gross_floor_area": 12555.0,
    #             "owner_telephone": "213-852-1238",
    #             "energy_score": 75,
    #             "address_line_1": "50 Willow Ave SE"
    #         },
    #         "matched": True
    #     }
    #
    #     # find lot number 1552813 in body['properties']
    #     found_prop = [k for k in body['properties'] if k['lot_number'] == '1552813']
    #     self.assertEqual(len(found_prop), 1)
    #
    #     found_prop = found_prop[0]
    #     del found_prop['id']
    #     del found_prop['coparent']['id']
    #     self.assertEqual(body['status'], 'success')
    #     self.assertEqual(len(body['tax_lots']), 12)
    #     self.assertEqual(len(body['properties']), 14)
    #     self.assertEqual(expected['lot_number'], found_prop['lot_number'])
    #     self.assertEqual(expected['matched'], found_prop['matched'])
    #     self.assertDictContainsSubset(expected['coparent'], found_prop['coparent'])
    #
    # def test_get_coparents(self):
    #     # get a specific test case with coparents
    #     property_state = PropertyState.objects.filter(
    #         use_description='Pizza House',
    #         import_file_id=self.import_file_2,
    #         data_state__in=[DATA_STATE_MAPPING, DATA_STATE_MATCHING],
    #         merge_state__in=[MERGE_STATE_UNKNOWN, MERGE_STATE_NEW]
    #     ).first()
    #
    #     vs = ImportFileViewSet()
    #     fields = ['id', 'extra_data', 'lot_number', 'use_description']
    #
    #     coparents = vs.has_coparent(property_state.id, 'properties', fields)
    #     expected = {
    #         'lot_number': '11160509',
    #         'gross_floor_area': 23543.0,
    #         'owner_telephone': '213-546-9755',
    #         'energy_score': 63,
    #         'use_description': 'Retail',
    #     }
    #     self.assertDictContainsSubset(expected, coparents)

    def test_unmatch(self):
        # unmatch a specific entry
        property_state = PropertyState.objects.filter(
            use_description='Club',
            import_file_id=self.import_file_2,
            data_state__in=[DATA_STATE_MAPPING, DATA_STATE_MATCHING],
            merge_state__in=[MERGE_STATE_UNKNOWN, MERGE_STATE_NEW]
        ).first()

        vs = ImportFileViewSet()
        fields = ['id', 'extra_data', 'lot_number', 'use_description']

        # get the coparent of the 'Club' to get the ID
        coparents = vs.has_coparent(property_state.id, 'properties', fields)

        # verify that the coparent id is not part of the view
        prop = PropertyView.objects.filter(cycle=self.cycle, state__id=coparents['id'])
        self.assertFalse(prop.exists())

        # TODO: Alex, this seems to not work with the notes causing validation errors. I can't figure out why
        # but am punting for now until after your merge capability is finished.

        # data = {
        #     "inventory_type": "properties",
        #     "state_id": property_state.id,
        #     "coparent_id": coparents['id']
        # }
        # url = reverse("api:v3:import_files-unmatch", args=[self.import_file_2.pk])
        # resp = self.client.post(
        #     url, data=json.dumps(data), content_type='application/json'
        # )
        # body = json.loads(resp.content)
        # self.assertEqual(body['status'], 'success')
        #
        # # verify that the coparent id is now in the view
        # self.assertTrue(prop.exists())

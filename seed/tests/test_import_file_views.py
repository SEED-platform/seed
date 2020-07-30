# !/usr/bin/env python
# encoding: utf-8

import ast
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
from seed.data_importer.views import convert_first_five_rows_to_list
from seed.landing.models import SEEDUser as User
from seed.lib.mcm.reader import ROW_DELIMITER
from seed.lib.superperms.orgs.models import Organization
from seed.models import PORTFOLIO_RAW, PropertyState, PropertyView
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
        self.user = User.objects.create_superuser(
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
                "parsed_unit": "kWh (thousand Watt-hours)",
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

        url = reverse_lazy("api:v2:import_files-first-five-rows", args=[self.import_file.pk])
        resp = self.client.get(url, content_type='application/json')
        body = json.loads(resp.content)
        self.assertEqual(body['status'], 'success')
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
        url = reverse("api:v2:import_files-detail", args=[self.import_file_2.pk])
        response = self.client.delete(
            url + '?organization_id=' + str(self.org.pk),
            content_type='application/json',
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data, {
            'status': 'error',
            'message': 'user does not have permission to delete file'
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ImportFile.objects.all().count(), 2)

    def test_delete_file_wrong_org(self):
        """ tests the delete_file request with wrong org"""
        url = reverse("api:v2:import_files-detail", args=[self.import_file_2.pk])
        response = self.client.delete(
            url + '?organization_id=' + str(self.org_2.pk),
            content_type='application/json',
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data, {
            'status': 'error',
            'message': 'No relationship to organization'
        })
        self.assertEqual(ImportFile.objects.all().count(), 2)

"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author Paul Munday <paul@paulmunday.net>
"""

import json
import locale
import os
from os import path
from pathlib import Path
from unittest import skip, skipIf

import pytest
import requests
import xmltodict
from django.test import TestCase
from django.urls import reverse_lazy
from xlrd import open_workbook

from seed.data_importer.models import ImportRecord
from seed.landing.models import SEEDUser as User
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization
from seed.views.v3.portfolio_manager import PortfolioManagerImport

PM_UN = "SEED_PM_UN"
PM_PW = "SEED_PM_PW"
pm_skip_test_check = skipIf(
    not os.environ.get(PM_UN, False) and not os.environ.get(PM_PW, False),  # noqa: PLW1508
    f'Cannot run "expect-pass" PM unit tests without {PM_UN} and {PM_PW} in environment',
)

# override this decorator for more pressing conditions
try:
    pm_avail_check = requests.get("https://isthewallbuilt.inbelievable.com/api.json", timeout=5)
    string_response = pm_avail_check.json()["status"]
    skip_due_to_espm_down = string_response == "no"

    if skip_due_to_espm_down:
        pm_skip_test_check = skip("ESPM is likely down temporarily, ESPM tests will not run")
except Exception:  # noqa: S110
    pass


class PortfolioManagerImportTest(TestCase):
    def test_unsuccessful_login(self):
        # To test a successful login, we'd have to include valid PM credentials, which we don't want to do,
        # so I will at least test an unsuccessful login attempt here
        pmi = PortfolioManagerImport("bad_username", "bad_password")
        with pytest.raises(Exception):  # noqa: PT011
            pmi.login_and_set_cookie_header()

    def test_get_template_by_name(self):
        template_1 = {"id": 1, "name": "first"}
        template_2 = {"id": 2, "name": "second"}
        template_set = [template_1, template_2]
        self.assertDictEqual(template_1, PortfolioManagerImport.get_template_by_name(template_set, "first"))
        self.assertDictEqual(template_2, PortfolioManagerImport.get_template_by_name(template_set, "second"))
        with pytest.raises(Exception):  # noqa: PT011
            PortfolioManagerImport.get_template_by_name(template_set, "missing")


class PortfolioManagerTemplateListViewTestsFailure(TestCase):
    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
            "email": "test_user@demo.com",
            "first_name": "Johnny",
            "last_name": "Energy",
        }
        self.user = User.objects.create_user(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.client.login(**user_details)

    def tearDown(self):
        self.user.delete()
        self.org.delete()

    def test_template_list_interface_no_username(self):
        resp = self.client.post(
            reverse_lazy("api:v3:portfolio_manager-template-list"), json.dumps({"password": "nothing"}), content_type="application/json"
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing username"
        self.assertEqual(400, resp.status_code)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("message", data)
        self.assertEqual("error", data["status"])
        self.assertIn("missing username", data["message"])

    def test_template_list_interface_no_password(self):
        resp = self.client.post(
            reverse_lazy("api:v3:portfolio_manager-template-list"),
            json.dumps({"username": "nothing"}),
            content_type="application/json",
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing password"
        self.assertEqual(400, resp.status_code)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("message", data)
        self.assertEqual("error", data["status"])
        self.assertIn("missing password", data["message"])

    @pm_skip_test_check
    def test_template_list_invalid_credentials(self):
        resp = self.client.post(
            reverse_lazy("api:v3:portfolio_manager-template-list"),
            json.dumps({"password": "nothing", "username": "nothing"}),
            content_type="application/json",
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing template"
        self.assertEqual(400, resp.status_code)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("message", data)
        self.assertEqual("error", data["status"])
        self.assertIn("Check credentials.", data["message"])


class PortfolioManagerTemplateListViewTestsSuccess(TestCase):
    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
            "email": "test_user@demo.com",
            "first_name": "Johnny",
            "last_name": "Energy",
        }
        self.user = User.objects.create_user(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.client.login(**user_details)

    @pm_skip_test_check
    def test_template_views(self):
        # if we get into this test, the PM_UN and PM_PW variables should be available
        # we'll still check of course
        pm_un = os.environ.get(PM_UN, False)  # noqa: PLW1508
        pm_pw = os.environ.get(PM_PW, False)  # noqa: PLW1508
        if not pm_un or not pm_pw:
            self.fail(f"Somehow PM test was initiated without {PM_UN} or {PM_PW} in the environment")

        # so now we'll make the call out to PM
        resp = self.client.post(
            reverse_lazy("api:v3:portfolio_manager-template-list"),
            json.dumps({"username": pm_un, "password": pm_pw}),
            content_type="application/json",
        )
        # this kinda gets a little fragile here.
        # We can't really guarantee that the test account over on ESPM will stay exactly like it is the whole time
        # But we can try to at least test the "form" of the response to make sure it is what we expect
        # And if we ever break the stuff over on ESPM it should be clear what went wrong

        # at a minimum, we should have a successful login and response
        self.assertEqual(200, resp.status_code)

        # the body should come as json; if not, this will fail to parse I presume and fail this test
        body = resp.json()

        # body should represent the successful process
        self.assertTrue(body["status"])

        # templates should be present, and be a list
        self.assertIn("templates", body)
        self.assertIsInstance(body["templates"], list)

        # every object in that list should be a dictionary that contains a bunch of expected keys
        for row in body["templates"]:
            for expected_key in ["name", "display_name", "z_seed_child_row"]:
                self.assertIn(expected_key, row)

            # if it is a child (data request) row, the display name should be formatted
            # it is possible that a parent row could have the same "indentation", and that's fine, we don't assert there
            if row["z_seed_child_row"]:
                self.assertEqual("  -  ", row["display_name"][0:5])


class PortfolioManagerReportGenerationViewTestsFailure(TestCase):
    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
            "email": "test_user@demo.com",
            "first_name": "Johnny",
            "last_name": "Energy",
        }
        self.user = User.objects.create_user(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.client.login(**user_details)

    def test_report_interface_no_username(self):
        resp = self.client.post(
            reverse_lazy("api:v3:portfolio_manager-report"),
            json.dumps({"password": "nothing", "template": "nothing"}),
            content_type="application/json",
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing username"
        self.assertEqual(400, resp.status_code)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("message", data)
        self.assertEqual("error", data["status"])
        self.assertIn("missing username", data["message"])

    def test_report_interface_no_password(self):
        resp = self.client.post(
            reverse_lazy("api:v3:portfolio_manager-report"),
            json.dumps({"username": "nothing", "template": "nothing"}),
            content_type="application/json",
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing password"
        self.assertEqual(400, resp.status_code)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("message", data)
        self.assertEqual("error", data["status"])
        self.assertIn("missing password", data["message"])

    def test_report_interface_no_template(self):
        resp = self.client.post(
            reverse_lazy("api:v3:portfolio_manager-report"),
            json.dumps({"password": "nothing", "username": "nothing"}),
            content_type="application/json",
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing template"
        self.assertEqual(400, resp.status_code)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("message", data)
        self.assertEqual("error", data["status"])
        self.assertIn("missing template", data["message"])

    @pm_skip_test_check
    def test_report_invalid_credentials(self):
        resp = self.client.post(
            reverse_lazy("api:v3:portfolio_manager-report"),
            json.dumps(
                {"password": "nothing", "username": "nothing", "template": {"id": 1, "name": "template_name", "z_seed_child_row": False}}
            ),
            content_type="application/json",
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing template"
        self.assertEqual(400, resp.status_code)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("message", data)
        self.assertEqual("error", data["status"])
        self.assertIn("Check credentials.", data["message"])


class PortfolioManagerReportGenerationViewTestsSuccess(TestCase):
    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
            "email": "test_user@demo.com",
            "first_name": "Johnny",
            "last_name": "Energy",
        }
        self.user = User.objects.create_user(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.client.login(**user_details)

        # if we get into this test, the PM_UN and PM_PW variables should be available
        # we'll still check of course
        self.pm_un = os.environ.get(PM_UN, False)  # noqa: PLW1508
        self.pm_pw = os.environ.get(PM_PW, False)  # noqa: PLW1508
        if not self.pm_un or not self.pm_pw:
            self.fail(f"Somehow PM test was initiated without {PM_UN} or {PM_PW} in the environment")

    @pm_skip_test_check
    def test_report_generation_parent_template(self):
        parent_template = {
            "display_name": "SEED City Test Report",
            "name": "SEED City Test Report",
            "id": 1103344,
            "z_seed_child_row": False,
            "type": 0,
            "children": [],
            "pending": 0,
        }

        # so now we'll call out to PM to get a parent template report
        resp = self.client.post(
            reverse_lazy("api:v3:portfolio_manager-report"),
            json.dumps({"username": self.pm_un, "password": self.pm_pw, "template": parent_template}),
            content_type="application/json",
        )

        # as usual, the first thing to test is really the status code of the response
        self.assertEqual(200, resp.status_code)

        # and we expect a json blob to come back
        body = resp.json()

        # the status flag should be successful
        self.assertEqual("success", body["status"])

        # we expect a list of properties to come back
        self.assertIn("properties", body)
        self.assertIsInstance(body["properties"], list)

        # then for each property, we expect some keys to come back, but if it has the property id, that should suffice
        for prop in body["properties"]:
            self.assertIn("portfolioManagerPropertyId", prop)

    @pm_skip_test_check
    def test_report_generation_empty_child_template(self):
        child_template = {
            "display_name": "  -  Data Request:SEED City Test Report April 24 2018",
            "name": "Data Request:SEED City Test Report April 24 2018",
            "id": 2097417,
            "subtype": 2,
            "z_seed_child_row": True,
            "hasChildrenRows": False,
            "type": 1,
            "children": [],
            "pending": 0,
        }

        # so now we'll call out to PM to get a child template report
        resp = self.client.post(
            reverse_lazy("api:v3:portfolio_manager-report"),
            json.dumps({"username": self.pm_un, "password": self.pm_pw, "template": child_template}),
            content_type="application/json",
        )

        # this child template is empty over on PM, so it comes back as a 400
        self.assertEqual(400, resp.status_code)

        # still, we expect a json blob to come back
        body = resp.json()

        # the status flag should be error
        self.assertEqual("error", body["status"])

        # in this case, we expect a meaningful error message
        self.assertIn("message", body)
        self.assertIn("empty", body["message"])


class PortfolioManagerReportSinglePropertyUploadTest(TestCase):
    """Test case for downloading a report with a single building and saving
    it to SEED's Dataset upload api."""

    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        self.user = User.objects.create_superuser(email="test_user@demo.com", **user_details)
        self.org, _, _ = create_organization(self.user)
        self.client.login(**user_details)

        # create a dataset
        dataset_name = "test_dataset"
        response = self.client.post(
            reverse_lazy("api:v3:datasets-list") + "?organization_id=" + str(self.org.pk),
            data=json.dumps({"name": dataset_name}),
            content_type="application/json",
        )
        dataset = response.json()
        self.dataset_id = dataset["id"]

        self.pm_un = os.environ.get(PM_UN, False)  # noqa: PLW1508
        self.pm_pw = os.environ.get(PM_PW, False)  # noqa: PLW1508
        if not self.pm_un or not self.pm_pw:
            self.fail(f"Somehow PM test was initiated without {PM_UN} or {PM_PW} in the environment")

    @pm_skip_test_check
    def test_single_property_template_for_upload(self):
        # create a single ESPM property report with template
        template = {
            "children": [],
            "display_name": "SEED_Test - Single Property",
            "id": 5440635,
            "name": "SEED_Test - Single Property",
            "newReport": 0,
            "z_seed_child_row": 0,
        }

        report_response = self.client.post(
            reverse_lazy("api:v3:portfolio_manager-report"),
            json.dumps({"username": self.pm_un, "password": self.pm_pw, "template": template}),
            content_type="application/json",
        )
        self.assertEqual(200, report_response.status_code)

        property_info = report_response.json()
        self.assertEqual(1, len(property_info["properties"]))
        self.assertIsInstance(property_info["properties"], list)

        # add report to SEED's dataset
        response = self.client.post(
            reverse_lazy("api:v3:upload-create-from-pm-import"),
            json.dumps({"properties": property_info["properties"], "import_record_id": self.dataset_id, "organization_id": self.org.pk}),
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code)


class UploadViewSetPermission(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.root_property = self.property_factory.get_property(access_level_instance=self.root_level_instance)
        self.child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)

        self.import_record = ImportRecord.objects.create(
            owner=self.root_member_user,
            last_modified_by=self.root_member_user,
            super_organization=self.org,
            access_level_instance=self.org.root,
        )

    def test_create(self):
        filename = path.join(path.dirname(__file__), "data", "property_sample_data.json")
        with open(filename, "rb") as f:
            url = reverse_lazy("api:v3:upload-list")
            url += "?organization_id=" + str(self.org.id)
            url += "&import_record=" + str(self.import_record.id)
            params = {"file": f}

            self.login_as_child_member()
            response = self.client.post(url, data=params)
            assert response.status_code == 404

            self.login_as_root_member()
            response = self.client.post(url, data=params)
            assert response.status_code == 200

    def test_create_from_pm_import(self):
        url = reverse_lazy("api:v3:upload-create-from-pm-import")
        params = json.dumps({"properties": [], "import_record_id": self.import_record.pk, "organization_id": self.org.pk})

        self.login_as_child_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 404

        self.login_as_root_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 200


class PortfolioManagerSingleReportXSLX(TestCase):
    """Test downloading a single ESPM report in XSLX format."""

    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        self.user = User.objects.create_superuser(email="test_user@demo.com", **user_details)
        self.org, _, _ = create_organization(self.user)
        self.client.login(**user_details)

        self.pm_un = os.environ.get(PM_UN, False)  # noqa: PLW1508
        self.pm_pw = os.environ.get(PM_PW, False)  # noqa: PLW1508
        if not self.pm_un or not self.pm_pw:
            self.fail(f"Somehow PM test was initiated without {PM_UN} or {PM_PW} in the environment")

        self.output_dir = Path(__file__).parent.absolute() / "output"
        if not self.output_dir.exists():
            os.mkdir(self.output_dir)

    @pm_skip_test_check
    def test_single_report_download(self):
        # PM ID 22178850 is a more complete test case with meter data
        pm_id = 22178850

        # remove the file if it exists
        new_file = self.output_dir / f"single_property_{pm_id}.xlsx"
        if new_file.exists():
            new_file.unlink()
        self.assertFalse(new_file.exists())

        pm = PortfolioManagerImport(self.pm_un, self.pm_pw)

        content = pm.return_single_property_report(pm_id)
        self.assertIsNotNone(content)
        with open(new_file, "wb") as file:
            file.write(content)

        self.assertTrue(new_file.exists())

        # TODO: load the xlsx file and ensure that it has the right tabs
        workbook = open_workbook(new_file)
        self.assertIn("Property", workbook.sheet_names())
        self.assertIn("Meters", workbook.sheet_names())
        self.assertIn("Meter Entries", workbook.sheet_names())

        # verify that the Property worksheet has the PM id in it
        sheet = workbook.sheet_by_name("Property")
        self.assertTrue(str(pm_id) in str(sheet._cell_values))

    @pm_skip_test_check
    def test_single_report_view(self):
        pm_id = 22178850
        response = self.client.post(
            reverse_lazy("api:v3:portfolio_manager-download", args=[pm_id]),
            json.dumps({"username": self.pm_un, "password": self.pm_pw}),
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code)


class PortfolioManagerReportParsingTest(TestCase):
    """Test the parsing of the resulting PM XML file. This is only for the
    version 2 parsing"""

    def test_parse_pm_report(self):
        pm = PortfolioManagerImport("not_a_real_password", "not_a_real_password")
        xml_path = Path(__file__).parent.absolute() / "data" / "portfolio-manager-report.xml"
        with open(xml_path, encoding=locale.getpreferredencoding(False)) as file:
            content_object = xmltodict.parse(file.read(), dict_constructor=dict)

            success, properties = pm._parse_properties_v2(content_object)

            self.assertTrue(success)
            self.assertEqual(len(properties), 9)
            self.assertEqual(properties[0]["portfolioManagerPropertyId"], "22178843")
            self.assertIsNone(properties[0]["parentPropertyId"])
            self.assertEqual(properties[0]["propertyFloorAreaBuildingsAndParking"], "89250.0")

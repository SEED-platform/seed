"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import ast
import json
import os
import pathlib
import unittest
from datetime import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.urls import reverse
from django.utils.timezone import (
    get_current_timezone,
    make_aware,  # make_aware is used because inconsistencies exist in creating datetime with tzinfo
)
from pytz import timezone

from config.settings.common import BASE_DIR, TIME_ZONE
from seed.data_importer.models import ImportFile, ImportRecord
from seed.data_importer.tasks import geocode_and_match_buildings_task, save_raw_data
from seed.landing.models import SEEDUser as User
from seed.lib.xml_mapping.mapper import default_buildingsync_profile_mappings
from seed.models import (
    DATA_STATE_MAPPING,
    DATA_STATE_MATCHING,
    GREEN_BUTTON,
    PORTFOLIO_METER_USAGE,
    PORTFOLIO_RAW,
    SEED_DATA_SOURCES,
    BuildingFile,
    Column,
    ColumnMappingProfile,
    InventoryDocument,
    Meter,
    MeterReading,
    Note,
    Organization,
    Property,
    PropertyState,
    PropertyView,
    Scenario,
    StatusLabel,
    TaxLotProperty,
    TaxLotView,
)
from seed.serializers.properties import PropertyStatePromoteWritableSerializer, PropertyStateSerializer
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeColumnListProfileFactory,
    FakeCycleFactory,
    FakeNoteFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeStatusLabelFactory,
    FakeTaxLotFactory,
    FakeTaxLotStateFactory,
)
from seed.tests.util import AccessLevelBaseTestCase, DataMappingBaseTestCase
from seed.utils.match import match_merge_link
from seed.utils.merge import merge_properties
from seed.utils.organizations import create_organization
from seed.utils.properties import pair_unpair_property_taxlot

COLUMNS_TO_SEND = [
    "project_id",
    "address_line_1",
    "city",
    "state_province",
    "postal_code",
    "pm_parent_property_id",
    "extra_data_field",
    "jurisdiction_tax_lot_id",
]


class PropertyViewTests(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.column_list_factory = FakeColumnListProfileFactory(organization=self.org)
        self.client.login(**user_details)

        # create tree
        self.org.access_level_names = ["1st Gen", "2nd Gen", "3rd Gen"]
        mom_ali = self.org.add_new_access_level_instance(self.org.root.id, "mom")
        self.me_ali = self.org.add_new_access_level_instance(mom_ali.id, "me")
        self.sister_ali = self.org.add_new_access_level_instance(mom_ali.id, "sister")
        self.org.save()

    def test_create_property(self):
        state = self.property_state_factory.get_property_state()
        cycle_id = self.cycle.id

        params = json.dumps({"cycle_id": cycle_id, "state": PropertyStateSerializer(state).data})

        url = reverse("api:v3:properties-list") + f"?organization_id={self.org.pk}"
        response = self.client.post(url, params, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "success")

        property = Property.objects.first()  # first and only
        self.assertEqual(property.access_level_instance, self.org_user.access_level_instance)

    def test_create_property_with_ali(self):
        self.org.access_level_names = ["root", "child"]
        self.org.save()
        child_ali = self.org.add_new_access_level_instance(self.org.root.id, "child")
        child_ali.save()

        state = self.property_state_factory.get_property_state()
        cycle_id = self.cycle.id

        params = json.dumps(
            {
                "cycle_id": cycle_id,
                "state": PropertyStateSerializer(state).data,
                "access_level_instance_id": child_ali.id,
            }
        )

        url = reverse("api:v3:properties-list") + f"?organization_id={self.org.pk}"
        response = self.client.post(url, params, content_type="application/json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "success")

        property = Property.objects.first()  # first and only
        self.assertEqual(property.access_level_instance, child_ali)

    def test_create_property_with_bad_ali(self):
        self.org.access_level_names = ["root", "child"]
        self.org.save()
        child_ali = self.org.add_new_access_level_instance(self.org.root.id, "child")
        self.org_user.access_level_instance = child_ali

        state = self.property_state_factory.get_property_state()
        cycle_id = self.cycle.id

        params = json.dumps(
            {
                "cycle_id": cycle_id,
                "state": PropertyStateSerializer(state).data,
                "access_level_instance_id": self.org.root.id,
            }
        )

        url = reverse("api:v3:properties-list") + f"?organization_id={self.org.pk}"
        response = self.client.post(url, params, content_type="application/json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "success")

    def test_create_property_in_diff_org(self):
        state = self.property_state_factory.get_property_state()
        cycle_id = self.cycle.id
        user_2 = User.objects.create_superuser(username="test_user2@demo.com", password="test_pass", email="test_user2@demo.com")
        org_2, _, _ = create_organization(user_2)

        # verify that user (1) can't post to user_2's org
        params = json.dumps({"cycle_id": cycle_id, "state": PropertyStateSerializer(state).data})
        url = reverse("api:v3:properties-list") + f"?organization_id={org_2.pk}"
        response = self.client.post(url, params, content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Incorrect org id.")

    def test_create_property_with_protected_fields(self):
        state = self.property_state_factory.get_property_state()
        state.normalized_address = "741 Evergreen Terrace"
        state.data_state = 999
        cycle_id = self.cycle.id

        params = json.dumps({"cycle_id": cycle_id, "state": PropertyStateSerializer(state).data})

        url = reverse("api:v3:properties-list") + f"?organization_id={self.org.pk}"
        response = self.client.post(url, params, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "success")

        # verify that the protected fields were not overwritten
        new_state_data = response.json()["view"]["state"]
        self.assertNotEqual(new_state_data["normalized_address"], state.normalized_address)
        self.assertNotEqual(new_state_data["data_state"], state.data_state)
        self.assertEqual(new_state_data["data_state"], DATA_STATE_MATCHING)

        # above was for spot checking, now look at the serializer and make sure that the
        # protected column objects are read_only.
        serializer = PropertyStatePromoteWritableSerializer(new_state_data)
        protected_columns = list(set(Column.EXCLUDED_MAPPING_FIELDS + Column.COLUMN_EXCLUDE_FIELDS))
        # go through each of the Column's class columns and ensure that the serializer is read only
        # map the related object ids to the column names
        protected_columns.pop(protected_columns.index("import_file"))
        protected_columns.pop(protected_columns.index("raw_access_level_instance_id"))  # needs to be set
        protected_columns.pop(protected_columns.index("raw_access_level_instance_error"))  # needs to be set
        protected_columns.pop(protected_columns.index("extra_data"))  # extra_data is allowed
        protected_columns.append("import_file_id")
        protected_columns.append("measures")
        protected_columns.append("scenarios")
        protected_columns.append("files")

        for column in protected_columns:
            self.assertIsNotNone(serializer.fields.get(column), f"Column {column} is not in the serializer")
            self.assertTrue(serializer.fields[column].read_only, f"Column {column} is not read_only in the write serializer")

    def test_get_and_edit_properties(self):
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        view = PropertyView.objects.create(property=prprty, cycle=self.cycle, state=state)
        params = {
            "organization_id": self.org.pk,
            "page": 1,
            "per_page": 999999999,
            "columns": COLUMNS_TO_SEND,
        }

        url = reverse("api:v3:properties-search") + f"?cycle_id={self.cycle.pk}"
        response = self.client.get(url, params)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        result = data[0]
        self.assertEqual(result["state"]["address_line_1"], state.address_line_1)

        db_created_time = result["created"]
        db_updated_time = result["updated"]
        self.assertTrue(db_created_time is not None)
        self.assertTrue(db_updated_time is not None)

        # update the address
        new_data = {"state": {"address_line_1": "742 Evergreen Terrace"}}
        url = reverse("api:v3:properties-detail", args=[view.id]) + f"?organization_id={self.org.pk}"
        response = self.client.put(url, json.dumps(new_data), content_type="application/json")
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")

        # the above call returns data from the PropertyState, need to get the Property --
        # call the get on the same API to retrieve it
        response = self.client.get(url, content_type="application/json")
        data = json.loads(response.content)
        # make sure the address was updated and that the datetimes were modified
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["state"]["address_line_1"], "742 Evergreen Terrace")
        self.assertEqual(
            datetime.strptime(db_created_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(microsecond=0),
            datetime.strptime(data["property"]["created"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(microsecond=0),
        )
        self.assertGreater(
            datetime.strptime(data["property"]["updated"], "%Y-%m-%dT%H:%M:%S.%fZ"),
            datetime.strptime(db_updated_time, "%Y-%m-%dT%H:%M:%S.%fZ"),
        )

    def test_upload_inventory_document_and_delete(self):
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        view = PropertyView.objects.create(property=prprty, cycle=self.cycle, state=state)

        test_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "test-document.pdf")

        url = reverse("api:v3:properties-detail", args=[view.id]) + f"upload_inventory_document/?organization_id={self.org.pk}"

        with open(test_filepath, "rb") as document:
            response = self.client.put(
                path=url,
                data=encode_multipart(data={"file": document, "file_type": "PDF", "name": "unused-name"}, boundary=BOUNDARY),
                content_type=MULTIPART_CONTENT,
            )

        data = response.json()
        self.assertEqual(200, response.status_code)
        self.assertTrue(data["success"])

        # verify that the object in on the property
        url = reverse("api:v3:properties-detail", args=[view.id]) + f"?organization_id={self.org.pk}"
        response = self.client.get(url)
        self.assertEqual(len(response.json()["property"]["inventory_documents"]), 1)
        self.assertEqual(response.json()["property"]["inventory_documents"][0]["filename"], "test-document.pdf")
        self.assertEqual(response.json()["property"]["inventory_documents"][0]["file_type"], "PDF")

    def test_edit_properties_creates_notes_after_initial_edit(self):
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        view = PropertyView.objects.create(property=prprty, cycle=self.cycle, state=state)

        # update the address
        new_data = {"state": {"address_line_1": "742 Evergreen Terrace", "extra_data": {"Some Extra Data": "111"}}}
        url = reverse("api:v3:properties-detail", args=[view.id]) + f"?organization_id={self.org.pk}"
        self.client.put(url, json.dumps(new_data), content_type="application/json")

        self.assertEqual(view.notes.count(), 1)

        # update the address again
        new_data = {"state": {"address_line_1": "123 note street", "extra_data": {"Some Extra Data": "222"}}}
        url = reverse("api:v3:properties-detail", args=[view.id]) + f"?organization_id={self.org.pk}"
        self.client.put(url, json.dumps(new_data), content_type="application/json")

        self.assertEqual(view.notes.count(), 2)
        refreshed_view = PropertyView.objects.get(id=view.id)
        note = refreshed_view.notes.order_by("created").last()

        expected_log_data = [
            {
                "field": "address_line_1",
                "previous_value": "742 Evergreen Terrace",
                "new_value": "123 note street",
                "state_id": refreshed_view.state_id,
            },
            {"field": "Some Extra Data", "previous_value": "111", "new_value": "222", "state_id": refreshed_view.state_id},
        ]
        self.assertEqual(note.note_type, Note.LOG)
        self.assertEqual(note.name, "Automatically Created")
        self.assertCountEqual(note.log_data, expected_log_data)

    def test_first_lat_long_edit(self):
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        view = PropertyView.objects.create(property=prprty, cycle=self.cycle, state=state)

        # update the address
        new_data = {
            "state": {
                "latitude": 39.765251,
                "longitude": -104.986138,
            }
        }
        url = reverse("api:v3:properties-detail", args=[view.id]) + f"?organization_id={self.org.pk}"
        response = self.client.put(url, json.dumps(new_data), content_type="application/json")
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")

        response = self.client.get(url, content_type="application/json")
        data = json.loads(response.content)

        self.assertEqual(data["status"], "success")

        self.assertIsNotNone(data["state"]["long_lat"])
        self.assertIsNotNone(data["state"]["geocoding_confidence"])

    def test_merged_indicators_provided_on_filter_endpoint(self):
        _import_record, import_file_1 = self.create_import_file(self.user, self.org, self.cycle)

        base_details = {
            "custom_id_1": "CustomID123",
            "import_file_id": import_file_1.id,
            "data_state": DATA_STATE_MAPPING,
            "no_default_data": False,
            "raw_access_level_instance_id": self.org.root.id,
        }
        self.property_state_factory.get_property_state(**base_details)

        # set import_file_1 mapping done so that record is "created for users to view".
        import_file_1.mapping_done = True
        import_file_1.save()
        geocode_and_match_buildings_task(import_file_1.id)

        _import_record_2, import_file_2 = self.create_import_file(self.user, self.org, self.cycle)

        url = reverse("api:v3:properties-filter") + f"?cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        response = self.client.post(url, content_type="application/json")
        data = json.loads(response.content)

        self.assertFalse(data["results"][0]["merged_indicator"])

        # make sure merged_indicator is True when merge occurs
        base_details["city"] = "Denver"
        base_details["import_file_id"] = import_file_2.id
        self.property_state_factory.get_property_state(**base_details)

        # set import_file_2 mapping done so that match merging can occur.
        import_file_2.mapping_done = True
        import_file_2.save()
        geocode_and_match_buildings_task(import_file_2.id)

        url = reverse("api:v3:properties-filter") + f"?cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        response = self.client.post(url, content_type="application/json")
        data = json.loads(response.content)

        self.assertTrue(data["results"][0]["merged_indicator"])

        # Create pairings and check if paired object has indicator as well
        taxlot_factory = FakeTaxLotFactory(organization=self.org)
        taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

        taxlot = taxlot_factory.get_taxlot()
        taxlot_state = taxlot_state_factory.get_taxlot_state()
        taxlot_view = TaxLotView.objects.create(taxlot=taxlot, cycle=self.cycle, state=taxlot_state)

        # attach pairing to one and only property_view
        TaxLotProperty(
            primary=True, cycle_id=self.cycle.id, property_view_id=PropertyView.objects.get().id, taxlot_view_id=taxlot_view.id
        ).save()

        url = reverse("api:v3:properties-filter") + f"?cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        response = self.client.post(url, content_type="application/json")
        data = json.loads(response.content)

        related = data["results"][0]["related"][0]

        self.assertTrue("merged_indicator" in related)
        self.assertFalse(related["merged_indicator"])

    def test_list_properties_with_profile_id(self):
        state = self.property_state_factory.get_property_state(extra_data={"field_1": "value_1"})
        prprty = self.property_factory.get_property()
        PropertyView.objects.create(property=prprty, cycle=self.cycle, state=state)

        # save all the columns in the state to the database so we can setup column list settings
        Column.save_column_names(state)
        # get the columnlistprofile (default) for all columns
        columnlistprofile = self.column_list_factory.get_columnlistprofile(columns=["address_line_1", "field_1"])

        params = {
            "organization_id": self.org.pk,
            "profile_id": columnlistprofile.id,
        }
        url = reverse("api:v3:properties-search") + f"?cycle_id={self.cycle.pk}"
        response = self.client.get(url, params)
        data = response.json()
        self.assertEqual(len(data), 1)
        result = data[0]
        self.assertEqual(result["state"]["address_line_1"], state.address_line_1)
        self.assertEqual(result["state"]["extra_data"]["field_1"], "value_1")
        self.assertFalse(result["state"].get("city", None))

    def test_properties_cycles_list(self):
        # Create Property set in cycle 1
        state = self.property_state_factory.get_property_state(extra_data={"field_1": "value_1"})
        prprty = self.property_factory.get_property()
        PropertyView.objects.create(property=prprty, cycle=self.cycle, state=state)

        cycle_2 = self.cycle_factory.get_cycle(start=datetime(2018, 10, 10, tzinfo=get_current_timezone()))
        state_2 = self.property_state_factory.get_property_state(extra_data={"field_1": "value_2"})
        prprty_2 = self.property_factory.get_property()
        PropertyView.objects.create(property=prprty_2, cycle=cycle_2, state=state_2)

        # save all the columns in the state to the database so we can setup column list settings
        Column.save_column_names(state)
        # get the columnlistprofile (default) for all columns
        columnlistprofile = self.column_list_factory.get_columnlistprofile(columns=["address_line_1", "field_1"])

        post_params = json.dumps(
            {"organization_id": self.org.pk, "profile_id": columnlistprofile.id, "cycle_ids": [self.cycle.id, cycle_2.id]}
        )
        url = reverse("api:v3:properties-filter-by-cycle")
        response = self.client.post(url, post_params, content_type="application/json")
        data = response.json()

        address_line_1_key = "address_line_1_" + str(columnlistprofile.columns.get(column_name="address_line_1").id)
        field_1_key = "field_1_" + str(columnlistprofile.columns.get(column_name="field_1").id)

        self.assertEqual(len(data), 2)

        result_1 = data[str(self.cycle.id)]
        self.assertEqual(result_1[0][address_line_1_key], state.address_line_1)
        self.assertEqual(result_1[0][field_1_key], "value_1")
        self.assertEqual(result_1[0]["id"], prprty.id)

        result_2 = data[str(cycle_2.id)]
        self.assertEqual(result_2[0][address_line_1_key], state_2.address_line_1)
        self.assertEqual(result_2[0][field_1_key], "value_2")
        self.assertEqual(result_2[0]["id"], prprty_2.id)

    def test_property_match_merge_link(self):
        base_details = {
            "pm_property_id": "123MatchID",
            "no_default_data": False,
        }

        ps_1 = self.property_state_factory.get_property_state(**base_details)
        prprty = self.property_factory.get_property()
        view_1 = PropertyView.objects.create(property=prprty, cycle=self.cycle, state=ps_1)

        cycle_2 = self.cycle_factory.get_cycle(start=datetime(2018, 10, 10, tzinfo=get_current_timezone()))
        ps_2 = self.property_state_factory.get_property_state(**base_details)
        prprty_2 = self.property_factory.get_property()
        PropertyView.objects.create(property=prprty_2, cycle=cycle_2, state=ps_2)

        url = reverse("api:v3:properties-match-merge-link", args=[view_1.id])
        url += f"?organization_id={self.org.pk}"
        response = self.client.post(url, content_type="application/json")
        summary = response.json()

        expected_summary = {
            "view_id": view_1.id,
            "match_merged_count": 0,
            "match_link_count": 1,
        }
        self.assertEqual(expected_summary, summary)

        refreshed_view_1 = PropertyView.objects.get(state_id=ps_1.id)
        view_2 = PropertyView.objects.get(state_id=ps_2.id)
        self.assertEqual(refreshed_view_1.property_id, view_2.property_id)

    def test_property_match_merge_link_links_different_alis(self):
        base_details = {
            "pm_property_id": "123MatchID",
            "no_default_data": False,
        }

        ps_1 = self.property_state_factory.get_property_state(**base_details)
        prprty = self.property_factory.get_property(access_level_instance=self.me_ali)
        view_1 = PropertyView.objects.create(property=prprty, cycle=self.cycle, state=ps_1)

        cycle_2 = self.cycle_factory.get_cycle(start=datetime(2018, 10, 10, tzinfo=get_current_timezone()))
        ps_2 = self.property_state_factory.get_property_state(**base_details)
        prprty_2 = self.property_factory.get_property(access_level_instance=self.sister_ali)
        PropertyView.objects.create(property=prprty_2, cycle=cycle_2, state=ps_2)

        url = reverse("api:v3:properties-match-merge-link", args=[view_1.id])
        url += f"?organization_id={self.org.pk}"
        response = self.client.post(url, content_type="application/json")

        assert response.status_code == 400
        assert (
            response.json()["message"]
            == "This property shares matching criteria with at least one property in a different ali. This should not happen. Please contact your system administrator."
        )

    def test_property_match_merge_link_merges_but_different_alis(self):
        base_details = {
            "pm_property_id": "123MatchID",
            "no_default_data": False,
        }

        ps_1 = self.property_state_factory.get_property_state(**base_details)
        prprty = self.property_factory.get_property(access_level_instance=self.me_ali)
        view_1 = PropertyView.objects.create(property=prprty, cycle=self.cycle, state=ps_1)

        ps_2 = self.property_state_factory.get_property_state(**base_details)
        prprty_2 = self.property_factory.get_property(access_level_instance=self.sister_ali)
        PropertyView.objects.create(property=prprty_2, cycle=self.cycle, state=ps_2)

        url = reverse("api:v3:properties-match-merge-link", args=[view_1.id])
        url += f"?organization_id={self.org.pk}"
        response = self.client.post(url, content_type="application/json")

        assert response.status_code == 400
        assert (
            response.json()["message"]
            == "This property shares matching criteria with at least one property in a different ali. This should not happen. Please contact your system administrator."
        )

    def test_get_links_for_a_single_property(self):
        # Create 2 linked property sets
        state = self.property_state_factory.get_property_state(extra_data={"field_1": "value_1"})
        prprty = self.property_factory.get_property()
        view_1 = PropertyView.objects.create(property=prprty, cycle=self.cycle, state=state)

        later_cycle = self.cycle_factory.get_cycle(start=datetime(2100, 10, 10, tzinfo=get_current_timezone()))
        state_2 = self.property_state_factory.get_property_state(extra_data={"field_1": "value_2"})
        view_2 = PropertyView.objects.create(property=prprty, cycle=later_cycle, state=state_2)

        url = reverse("api:v3:properties-links", args=[view_1.id])
        url += f"?organization_id={self.org.pk}"
        response = self.client.get(url, content_type="application/json")
        data = response.json()["data"]

        self.assertEqual(len(data), 2)

        # results should be ordered by descending cycle start date
        result_1 = data[1]
        self.assertEqual(result_1["address_line_1"], state.address_line_1)
        self.assertEqual(result_1["extra_data"]["field_1"], "value_1")
        self.assertEqual(result_1["cycle_id"], self.cycle.id)
        self.assertEqual(result_1["view_id"], view_1.id)

        result_2 = data[0]
        self.assertEqual(result_2["address_line_1"], state_2.address_line_1)
        self.assertEqual(result_2["extra_data"]["field_1"], "value_2")
        self.assertEqual(result_2["cycle_id"], later_cycle.id)
        self.assertEqual(result_2["view_id"], view_2.id)

    def test_search_identifier(self):
        self.property_view_factory.get_property_view(cycle=self.cycle, custom_id_1="123456")
        self.property_view_factory.get_property_view(cycle=self.cycle, custom_id_1="987654 Long Street")
        self.property_view_factory.get_property_view(cycle=self.cycle, address_line_1="123 Main Street")
        self.property_view_factory.get_property_view(cycle=self.cycle, address_line_1="Hamilton Road")
        self.property_view_factory.get_property_view(cycle=self.cycle, custom_id_1="long road")

        # Typically looks like this
        # http://localhost:8000/api/v3/properties/search?organization_id=265&cycle=219&identifier=09-IS

        # check for all items
        query_params = f"?cycle={self.cycle.pk}&organization_id={self.org.pk}"
        url = reverse("api:v3:properties-search") + query_params
        response = self.client.get(url)
        results = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual(len(results), 5)

        # check for 2 items with 123
        query_params = f"?cycle={self.cycle.pk}&organization_id={self.org.pk}&identifier={'123'}"
        url = reverse("api:v3:properties-search") + query_params
        response = self.client.get(url)
        results = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        # print out the result of this when there are more than two in an attempt to catch the
        # non-deterministic part of this test
        if len(results) > 2:
            print(results)

        self.assertEqual(len(results), 2)

        # check the combination of both the identifier and the analysis state
        query_params = f"?cycle={self.cycle.pk}&organization_id={self.org.pk}&identifier={'Long'}"
        url = reverse("api:v3:properties-search") + query_params
        response = self.client.get(url)
        results = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual(len(results), 2)

    def test_meters_exist(self):
        # Create a property set with meters
        state_1 = self.property_state_factory.get_property_state()
        property_1 = self.property_factory.get_property()
        property_view_1 = PropertyView.objects.create(property=property_1, cycle=self.cycle, state=state_1)

        import_record = ImportRecord.objects.create(
            owner=self.user, last_modified_by=self.user, super_organization=self.org, access_level_instance=self.org.root
        )
        filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename
        import_file = ImportFile.objects.create(
            import_record=import_record,
            source_type=SEED_DATA_SOURCES[GREEN_BUTTON][1],
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=pathlib.Path(filepath).read_bytes()),
            cycle=self.cycle,
            matching_results_data={"property_id": property_1.id},  # this is how target property is specified
        )
        gb_import_url = reverse("api:v3:import_files-start-save-data", args=[import_file.id])
        gb_import_url += f"?organization_id={self.org.pk}"
        gb_import_post_params = {"cycle_id": self.cycle.pk}
        self.client.post(gb_import_url, gb_import_post_params)

        # Create a property set without meters
        state_2 = self.property_state_factory.get_property_state()
        property_2 = self.property_factory.get_property()
        property_view_2 = PropertyView.objects.create(property=property_2, cycle=self.cycle, state=state_2)

        url = reverse("api:v3:properties-meters-exist")
        url += f"?organization_id={self.org.pk}"

        true_post_params = json.dumps({"property_view_ids": [property_view_2.pk, property_view_1.pk]})
        true_result = self.client.post(url, true_post_params, content_type="application/json")
        self.assertEqual(b"true", true_result.content)

        false_post_params = json.dumps({"property_view_ids": [property_view_2.pk]})
        false_result = self.client.post(url, false_post_params, content_type="application/json")
        self.assertEqual(b"false", false_result.content)


class PropertyViewTestsPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        # create property with label
        self.profile = ColumnMappingProfile.objects.get(profile_type=ColumnMappingProfile.BUILDINGSYNC_DEFAULT)
        self.cycle = self.cycle_factory.get_cycle()
        self.view = self.property_view_factory.get_property_view(cycle=self.cycle)
        self.taxlot_view = self.taxlot_view_factory.get_taxlot_view(cycle=self.cycle)
        self.property = Property.objects.create(organization=self.org, access_level_instance=self.org.root)
        self.label = StatusLabel.objects.create(
            color="red",
            name="test_label",
            super_organization=self.org,
        )
        self.view.labels.add(self.label)
        self.view.property = self.property
        self.view.save()

    def test_property_labels(self):
        url = reverse("api:v3:properties-labels") + f"?organization_id={self.org.pk}"

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, content_type="application/json")
        data = resp.json()
        label_data = next(d for d in data if d["name"] == "test_label")
        assert label_data["is_applied"] == [self.view.pk]

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, content_type="application/json")
        data = resp.json()
        label_data = next(d for d in data if d["name"] == "test_label")
        assert label_data["is_applied"] == []

    def test_property_meter_usage(self):
        url = reverse("api:v3:properties-meter-usage", kwargs={"pk": self.view.id}) + f"?organization_id={self.org.pk}"
        post_params = json.dumps({"interval": "Exact", "excluded_meter_ids": []})

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, post_params, content_type="application/json")
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, post_params, content_type="application/json")
        assert resp.status_code == 404

    def test_property_sensor_usage(self):
        url = reverse("api:v3:property-sensors-usage", kwargs={"property_pk": self.view.id}) + f"?organization_id={self.org.pk}"
        post_params = json.dumps({"interval": "Exact", "excluded_sensor_ids": []})

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, post_params, content_type="application/json")
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, post_params, content_type="application/json")
        assert resp.status_code == 404

    def test_property_sensors(self):
        url = reverse("api:v3:property-sensors-list", kwargs={"property_pk": self.view.id}) + f"?organization_id={self.org.pk}"

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 404

    def test_property_meters_exist(self):
        url = reverse("api:v3:properties-meters-exist") + f"?organization_id={self.org.pk}"
        params = json.dumps({"property_view_ids": [self.view.pk]})

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, params, content_type="application/json")
        assert resp.status_code == 200
        assert resp.content == b"false"

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, params, content_type="application/json")
        assert resp.status_code == 400
        assert resp.json()["status"] == "error"

    def test_properties_merge(self):
        self.state_2 = self.property_state_factory.get_property_state(address_line_1="2 property state")
        self.property_2 = self.property_factory.get_property()
        self.view_2 = PropertyView.objects.create(property=self.property_2, cycle=self.cycle, state=self.state_2)

        # Merge the properties
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps({"property_view_ids": [self.view_2.pk, self.view.pk]})

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, post_params, content_type="application/json")
        assert resp.status_code == 400

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, post_params, content_type="application/json")
        assert resp.status_code == 200

    def test_property_links(self):
        url = reverse("api:v3:properties-links", args=[self.view.id]) + f"?organization_id={self.org.pk}"

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 404

    def test_property_get(self):
        url = reverse("api:v3:properties-detail", args=[self.view.id]) + f"?organization_id={self.org.pk}"

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 404

    def test_property_update(self):
        url = reverse("api:v3:properties-detail", args=[self.view.id]) + f"?organization_id={self.org.pk}"
        param = json.dumps({"state": {"address_line_1": "742 Evergreen Terrace"}})

        # root member can
        self.login_as_root_member()
        resp = self.client.put(url, param, content_type="application/json")
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.put(url, param, content_type="application/json")
        assert resp.status_code == 404

    def test_property_search(self):
        url = reverse("api:v3:properties-search") + f"?cycle_id={self.cycle.pk}&organization_id={self.org.pk}"

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_property_filter(self):
        url = reverse("api:v3:properties-filter") + f"?cycle_id={self.cycle.pk}&organization_id={self.org.pk}"

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, content_type="application/json")
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 1

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, content_type="application/json")
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 0

    def test_property_unmerge(self):
        self.state_2 = self.property_state_factory.get_property_state(address_line_1="2 property state")
        self.property_2 = self.property_factory.get_property()
        self.view_2 = PropertyView.objects.create(property=self.property_2, cycle=self.cycle, state=self.state_2)
        merged_state = merge_properties([self.view.state.pk, self.state_2.pk], self.org.pk, "Manual Match")
        match_merge_link(merged_state, self.org.root, self.cycle)
        view_id = PropertyView.objects.first().id
        url = reverse("api:v3:properties-unmerge", args=[view_id]) + f"?organization_id={self.org.pk}"

        # child member cannot
        self.login_as_child_member()
        response = self.client.put(url, content_type="application/json")
        assert response.status_code == 400

        # root member can
        self.login_as_root_member()
        response = self.client.put(url, content_type="application/json")
        assert response.status_code == 200

    def test_property_match_merge_link(self):
        url = reverse("api:v3:properties-match-merge-link", args=[self.view.id]) + f"?organization_id={self.org.pk}"

        # root member can
        self.login_as_root_member()
        response = self.client.post(url, content_type="application/json")
        assert response.status_code == 200

        # child member cannot
        self.login_as_child_member()
        response = self.client.post(url, content_type="application/json")
        assert response.status_code == 404

    def test_properties_batch_delete(self):
        self.state_2 = self.property_state_factory.get_property_state(address_line_1="2 property state")
        self.property_2 = self.property_factory.get_property(access_level_instance=self.child_level_instance)
        self.view_2 = PropertyView.objects.create(property=self.property_2, cycle=self.cycle, state=self.state_2)

        # Merge the properties
        url = reverse("api:v3:properties-batch-delete") + f"?organization_id={self.org.pk}"
        params = json.dumps({"property_view_ids": [self.view_2.pk, self.view.pk]})

        # child member only deletes the one it has access to.
        self.login_as_child_member()
        resp = self.client.delete(url, params, content_type="application/json")
        assert resp.status_code == 200
        assert resp.json() == {"status": "success", "properties": 1}

    def test_property_building_sync(self):
        url = (
            reverse("api:v3:properties-building-sync", args=[self.view.id])
            + f"?organization_id={self.org.pk}"
            + f"&profile_id={self.profile.id}"
        )

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/xml")
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type="application/xml")
        assert resp.status_code == 404

    def test_property_hpxml(self):
        url = reverse("api:v3:properties-hpxml", args=[self.view.id]) + f"?organization_id={self.org.pk}"

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 404

    def test_property_list(self):
        url = reverse("api:v3:properties-list") + f"?cycle_id={self.cycle.pk}&organization_id={self.org.pk}"

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 1

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 0

    def test_property_filter_by_cycle(self):
        url = reverse("api:v3:properties-filter-by-cycle") + f"?organization_id={self.org.pk}"
        params = json.dumps({"cycle_ids": [self.cycle.id]})

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, params, content_type="application/json")
        assert resp.status_code == 200
        assert len(resp.json()[str(self.cycle.id)]) == 1

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, params, content_type="application/json")
        assert resp.status_code == 200
        assert len(resp.json()[str(self.cycle.id)]) == 0

    def test_properties_get_canonical_properties(self):
        url = reverse("api:v3:properties-get-canonical-properties") + f"?organization_id={self.org.pk}"
        params = json.dumps({"view_ids": [self.view.pk]})

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, params, content_type="application/json")
        assert resp.status_code == 200
        assert resp.json()["properties"] == [self.property.pk]

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, params, content_type="application/json")
        assert resp.status_code == 200
        assert resp.json()["properties"] == []

    def test_property_pair(self):
        url = reverse("api:v3:properties-pair", args=[self.view.id]) + f"?taxlot_id={self.taxlot_view.pk}&organization_id={self.org.pk}"

        # root member can
        self.login_as_root_member()
        resp = self.client.put(url, content_type="application/json")
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.put(url, content_type="application/json")
        assert resp.status_code == 404

    def test_property_delete_inventory_document(self):
        inventory_document = InventoryDocument.objects.create(property=self.property)
        url = (
            reverse("api:v3:properties-delete-inventory-document", args=[self.view.id])
            + f"?organization_id={self.org.pk}"
            + f"&file_id={inventory_document.pk}"
        )

        # child member cannot
        self.login_as_child_member()
        resp = self.client.delete(url, content_type="application/json")
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.delete(url, content_type="application/json")
        assert resp.status_code == 200

    def test_property_unpair(self):
        pair_unpair_property_taxlot(self.view.id, self.taxlot_view.id, self.org.pk, True)
        url = reverse("api:v3:properties-unpair", args=[self.view.id]) + f"?taxlot_id={self.taxlot_view.pk}&organization_id={self.org.pk}"

        # child member cannot
        self.login_as_child_member()
        resp = self.client.put(url, content_type="application/json")
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.put(url, content_type="application/json")
        assert resp.status_code == 200

    def test_property_update_with_building_sync(self):
        filename = os.path.join(BASE_DIR, "seed", "building_sync", "tests", "data", "ex_1.xml")
        url = (
            reverse("api:v3:properties-update-with-building-sync", args=[self.view.id])
            + f"?organization_id={self.org.pk}"
            + f"&cycle_id={self.cycle.pk}"
        )
        with open(filename, "rb") as f:
            data = encode_multipart(
                data={"file": f, "file_type": "BuildingSync", "name": "unused-name"},
                boundary=BOUNDARY,
            )

            # root member can
            self.login_as_root_member()
            resp = self.client.put(url, data=data, content_type=MULTIPART_CONTENT)
            assert resp.status_code == 200

            # child member cannot
            self.login_as_child_member()
            resp = self.client.put(url, data=data, content_type=MULTIPART_CONTENT)
            assert resp.status_code == 404

    def test_property_upload_inventory_document(self):
        location = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        filename = os.path.relpath(os.path.join(location, "data", "test-document.pdf"))
        url = (
            reverse("api:v3:properties-upload-inventory-document", args=[self.view.id])
            + f"?organization_id={self.org.pk}"
            + f"&cycle_id={self.cycle.pk}"
        )
        with open(filename, "rb") as f:
            data = encode_multipart(
                data={"file": f, "file_type": "PDF", "name": "unused-name"},
                boundary=BOUNDARY,
            )

            # root member can
            self.login_as_root_member()
            resp = self.client.put(url, data=data, content_type=MULTIPART_CONTENT)
            assert resp.status_code == 200

            # child member cannot
            self.login_as_child_member()
            resp = self.client.put(url, data=data, content_type=MULTIPART_CONTENT)
            assert resp.status_code == 404

    def test_property_analyses(self):
        url = reverse("api:v3:properties-analyses", args=[self.property.id]) + f"?organization_id={self.org.pk}"

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 200

        # child member cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 404

    def test_update_property_view_with_espm(self):
        """Simple test to verify that the property state is merged with an updated
        ESPM download XLSX file."""
        pm_property_id = "22482007"
        mapping_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "mappings", "espm-single-mapping.csv")
        # need to upload the mappings for the ESPM data to a new profile
        mapping_profile = ColumnMappingProfile.create_from_file(mapping_filepath, self.org, "ESPM", overwrite_if_exists=True)

        test_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", f"portfolio-manager-single-{pm_property_id}.xlsx")

        url = reverse("api:v3:properties-update-with-espm", args=[self.view.id])
        url += f"?organization_id={self.org.id}&cycle_id={self.cycle.id}&mapping_profile_id={mapping_profile.id}"
        with open(test_filepath, "rb") as doc:
            self.login_as_root_member()
            resp = self.client.put(
                path=url,
                data=encode_multipart(data={"file": doc, "file_type": "XLSX", "name": doc.name}, boundary=BOUNDARY),
                content_type=MULTIPART_CONTENT,
            )
            assert resp.status_code == 200

            self.login_as_child_member()
            resp = self.client.put(
                path=url,
                data=encode_multipart(data={"file": doc, "file_type": "XLSX", "name": doc.name}, boundary=BOUNDARY),
                content_type=MULTIPART_CONTENT,
            )
            assert resp.status_code == 404

    def test_properties_can_move_between_alis(self):
        self.property.access_level_instance = self.child_level_instance
        self.property.save()

        url = reverse("api:v3:properties-move-properties-to") + f"?organization_id={self.org.pk}"
        post_params = json.dumps(
            {"property_view_ids": [self.property.views.first().id], "access_level_instance_id": self.root_level_instance.id}
        )

        response = self.client.post(url, post_params, content_type="application/json")

        assert response.status_code == 200
        p = Property.objects.get(pk=self.property.pk)
        assert p.access_level_instance == self.root_level_instance

    def test_properties_cannot_move_between_alis_without_perms(self):
        self.property.access_level_instance = self.child_level_instance
        self.property.save()

        url = (
            reverse("api:v3:properties-move-properties-to")
            + f"?organization_id={self.org.pk}&access_level_instance_id={self.root_level_instance.id}"
        )
        post_params = json.dumps({"property_view_ids": [self.property.views.first().id]})

        self.login_as_child_member()
        response = self.client.post(url, post_params, content_type="application/json")

        assert response.status_code == 404


class PropertyUpdateCausesMergesAndLinkTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))

        self.state_1 = self.property_state_factory.get_property_state(
            address_line_1="1 property state",
            pm_property_id="5766973",  # this allows the Property to be targeted for PM meter additions
        )
        self.property_1 = self.property_factory.get_property()
        self.view_1 = PropertyView.objects.create(property=self.property_1, cycle=self.cycle, state=self.state_1)

        self.state_2 = self.property_state_factory.get_property_state(address_line_1="2 property state")
        self.property_2 = self.property_factory.get_property()
        self.view_2 = PropertyView.objects.create(property=self.property_2, cycle=self.cycle, state=self.state_2)

    def test_properties_update_causes_merge(self):
        url = reverse("api:v3:properties-detail", args=[self.view_2.id]) + f"?organization_id={self.org.pk}"
        param = json.dumps({"state": {"pm_property_id": "5766973"}})

        response = self.client.put(url, param, content_type="application/json")

        assert response.status_code == 200
        assert Property.objects.count() == 1
        assert PropertyView.objects.count() == 1

    def test_properties_update_causes_link(self):
        self.view_1.cycle = self.cycle_factory.get_cycle(start=datetime(2020, 10, 10, tzinfo=get_current_timezone()))
        self.view_1.save()

        url = reverse("api:v3:properties-detail", args=[self.view_2.id]) + f"?organization_id={self.org.pk}"
        param = json.dumps({"state": {"pm_property_id": "5766973"}})

        response = self.client.put(url, param, content_type="application/json")

        assert response.status_code == 200
        assert PropertyView.objects.count() == 2
        assert list(PropertyView.objects.values_list("property", flat=True)) == [self.property_1.id, self.property_1.id]

    def test_properties_update_causes_merge_different_ali(self):
        self.property_1.access_level_instance = self.child_level_instance
        self.property_1.save()

        url = reverse("api:v3:properties-detail", args=[self.view_2.id]) + f"?organization_id={self.org.pk}"
        param = json.dumps({"state": {"pm_property_id": "5766973"}})

        response = self.client.put(url, param, content_type="application/json")

        assert response.status_code == 400
        assert Property.objects.count() == 2
        assert PropertyView.objects.count() == 2

    def test_properties_update_causes_link_different_ali(self):
        self.property_1.access_level_instance = self.child_level_instance
        self.property_1.save()
        self.view_1.cycle = self.cycle_factory.get_cycle(start=datetime(2020, 10, 10, tzinfo=get_current_timezone()))
        self.view_1.save()

        url = reverse("api:v3:properties-detail", args=[self.view_2.id]) + f"?organization_id={self.org.pk}"
        param = json.dumps({"state": {"pm_property_id": "5766973"}})

        response = self.client.put(url, param, content_type="application/json")

        assert response.status_code == 400
        assert PropertyView.objects.count() == 2
        assert list(PropertyView.objects.values_list("property", flat=True)) == [self.property_1.id, self.property_2.id]


class PropertyMergeViewTests(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)

        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.client.login(**user_details)

        self.state_1 = self.property_state_factory.get_property_state(
            address_line_1="1 property state",
            pm_property_id="5766973",  # this allows the Property to be targeted for PM meter additions
        )
        self.property_1 = self.property_factory.get_property()
        self.view_1 = PropertyView.objects.create(property=self.property_1, cycle=self.cycle, state=self.state_1)

        self.state_2 = self.property_state_factory.get_property_state(address_line_1="2 property state")
        self.property_2 = self.property_factory.get_property()
        self.view_2 = PropertyView.objects.create(property=self.property_2, cycle=self.cycle, state=self.state_2)

        self.import_record = ImportRecord.objects.create(
            owner=self.user, last_modified_by=self.user, super_organization=self.org, access_level_instance=self.org.root
        )

        # create tree
        self.org.access_level_names = ["1st Gen", "2nd Gen", "3rd Gen"]
        mom_ali = self.org.add_new_access_level_instance(self.org.root.id, "mom")
        self.me_ali = self.org.add_new_access_level_instance(mom_ali.id, "me")
        self.sister_ali = self.org.add_new_access_level_instance(mom_ali.id, "sister")
        self.org.save()

    def test_properties_merge_without_losing_labels(self):
        # Create 3 Labels
        label_factory = FakeStatusLabelFactory(organization=self.org)

        label_1 = label_factory.get_statuslabel()
        label_2 = label_factory.get_statuslabel()
        label_3 = label_factory.get_statuslabel()

        self.view_1.labels.add(label_1, label_2)
        self.view_2.labels.add(label_2, label_3)

        # Merge the properties
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps({"property_view_ids": [self.view_2.pk, self.view_1.pk]})
        self.client.post(url, post_params, content_type="application/json")

        # The resulting -View should have 3 labels
        view = PropertyView.objects.first()

        self.assertEqual(view.labels.count(), 3)
        label_names = list(view.labels.values_list("name", flat=True))
        self.assertCountEqual(label_names, [label_1.name, label_2.name, label_3.name])

    def test_properties_merge_mismatched_alis(self):
        # set properties alis
        self.property_1.access_level_instance = self.me_ali
        self.property_1.save()
        self.property_2.access_level_instance = self.sister_ali
        self.property_2.save()

        # Merge the properties
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps({"property_view_ids": [self.view_2.pk, self.view_1.pk]})
        response = self.client.post(url, post_params, content_type="application/json")

        assert response.status_code == 400
        assert Property.objects.count() == 2

    def test_properties_merge_causes_link(self):
        self.state_2.custom_id_1 = 1
        self.state_2.save()

        # create a state in a new cycle whose matching_criteria are the combo of state 1 and 2s.
        self.other_cycle = self.cycle_factory.get_cycle(start=datetime(2020, 10, 10, tzinfo=get_current_timezone()))
        self.state_3 = self.property_state_factory.get_property_state()
        self.property_3 = self.property_factory.get_property()
        self.view_3 = PropertyView.objects.create(property=self.property_3, cycle=self.other_cycle, state=self.state_3)
        self.state_3.pm_property_id = self.state_1.pm_property_id
        self.state_3.custom_id_1 = self.state_2.custom_id_1
        self.state_3.save()

        # Merge the properties
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps({"property_view_ids": [self.view_2.pk, self.view_1.pk]})
        response = self.client.post(url, post_params, content_type="application/json")

        assert response.status_code == 200
        assert response.json() == {"status": "success", "match_merged_count": 0, "match_link_count": 1}
        views = PropertyView.objects.all()
        assert views.count() == 2
        assert list(views.values_list("property_id", flat=True)) == [self.property_3.id, self.property_3.id]

    def test_properties_merge_causes_link_mismatched_alis(self):
        self.state_2.custom_id_1 = 1
        self.state_2.save()

        # create a state in a new cycle whose matching_criteria are the combo of state 1 and 2s.
        self.other_cycle = self.cycle_factory.get_cycle(start=datetime(2020, 10, 10, tzinfo=get_current_timezone()))
        self.state_3 = self.property_state_factory.get_property_state()
        self.property_3 = self.property_factory.get_property(access_level_instance=self.sister_ali)
        self.view_3 = PropertyView.objects.create(property=self.property_3, cycle=self.other_cycle, state=self.state_3)
        self.state_3.pm_property_id = self.state_1.pm_property_id
        self.state_3.custom_id_1 = self.state_2.custom_id_1
        self.state_3.save()

        # Merge the properties
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps({"property_view_ids": [self.view_2.pk, self.view_1.pk]})
        response = self.client.post(url, post_params, content_type="application/json")

        assert response.status_code == 400
        views = PropertyView.objects.all()
        assert views.count() == 3

    def test_properties_merge_without_losing_notes(self):
        note_factory = FakeNoteFactory(organization=self.org, user=self.user)

        # Create 3 Notes and distribute them to the two -Views.
        note1 = note_factory.get_note(name="non_default_name_1")
        note2 = note_factory.get_note(name="non_default_name_2")
        self.view_1.notes.add(note1)
        self.view_1.notes.add(note2)

        note3 = note_factory.get_note(name="non_default_name_3")
        self.view_2.notes.add(note2)
        self.view_2.notes.add(note3)

        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps({"property_view_ids": [self.view_2.pk, self.view_1.pk]})
        self.client.post(url, post_params, content_type="application/json")

        # The resulting -View should have 3 notes
        view = PropertyView.objects.first()

        self.assertEqual(view.notes.count(), 3)
        note_names = list(view.notes.values_list("name", flat=True))
        self.assertCountEqual(note_names, [note1.name, note2.name, note3.name])

    def test_properties_merge_without_losing_pairings(self):
        # Create 2 pairings and distribute them to the two -Views.
        taxlot_factory = FakeTaxLotFactory(organization=self.org)
        taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

        taxlot_1 = taxlot_factory.get_taxlot()
        state_1 = taxlot_state_factory.get_taxlot_state()
        taxlot_view_1 = TaxLotView.objects.create(taxlot=taxlot_1, cycle=self.cycle, state=state_1)

        taxlot_2 = taxlot_factory.get_taxlot()
        state_2 = taxlot_state_factory.get_taxlot_state()
        taxlot_view_2 = TaxLotView.objects.create(taxlot=taxlot_2, cycle=self.cycle, state=state_2)

        TaxLotProperty(primary=True, cycle_id=self.cycle.id, property_view_id=self.view_1.id, taxlot_view_id=taxlot_view_1.id).save()

        TaxLotProperty(primary=True, cycle_id=self.cycle.id, property_view_id=self.view_2.id, taxlot_view_id=taxlot_view_2.id).save()

        # Merge the properties
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps(
            {
                "property_view_ids": [self.view_2.pk, self.view_1.pk]  # priority given to view_1
            }
        )
        self.client.post(url, post_params, content_type="application/json")

        # There should still be 2 TaxLotProperties
        self.assertEqual(TaxLotProperty.objects.count(), 2)

        property_view = PropertyView.objects.first()
        paired_taxlotview_ids = list(
            TaxLotProperty.objects.filter(property_view_id=property_view.id).values_list("taxlot_view_id", flat=True)
        )
        self.assertCountEqual(paired_taxlotview_ids, [taxlot_view_1.id, taxlot_view_2.id])

    def test_properties_merge_without_losing_meters_1st_has_meters(self):
        # Assign meters to the first Property
        filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename
        import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type=SEED_DATA_SOURCES[GREEN_BUTTON][1],
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=pathlib.Path(filepath).read_bytes()),
            cycle=self.cycle,
            matching_results_data={"property_id": self.property_1.id},  # this is how target property is specified
        )
        gb_import_url = reverse("api:v3:import_files-start-save-data", args=[import_file.id])
        gb_import_url += f"?organization_id={self.org.pk}"
        gb_import_post_params = {"cycle_id": self.cycle.pk}
        self.client.post(gb_import_url, gb_import_post_params)

        # Merge PropertyStates
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps({"property_view_ids": [self.view_2.pk, self.view_1.pk]})
        self.client.post(url, post_params, content_type="application/json")

        # There should only be one PropertyView
        self.assertEqual(PropertyView.objects.count(), 1)

        self.assertEqual(PropertyView.objects.first().property.meters.count(), 1)
        self.assertEqual(PropertyView.objects.first().property.meters.first().meter_readings.count(), 2)

    def test_properties_merge_without_losing_meters_2nd_has_meters(self):
        # Assign Meters to the second Property
        filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename
        import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type=SEED_DATA_SOURCES[GREEN_BUTTON][1],
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=pathlib.Path(filepath).read_bytes()),
            cycle=self.cycle,
            matching_results_data={"property_id": self.property_2.id},  # this is how target property is specified
        )
        gb_import_url = reverse("api:v3:import_files-start-save-data", args=[import_file.id])
        gb_import_url += f"?organization_id={self.org.pk}"
        gb_import_post_params = {"cycle_id": self.cycle.pk}
        self.client.post(gb_import_url, gb_import_post_params)

        # Merge PropertyStates
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps({"property_view_ids": [self.view_2.pk, self.view_1.pk]})
        self.client.post(url, post_params, content_type="application/json")

        # There should only be one PropertyView
        self.assertEqual(PropertyView.objects.count(), 1)

        self.assertEqual(PropertyView.objects.first().property.meters.count(), 1)
        self.assertEqual(PropertyView.objects.first().property.meters.first().meter_readings.count(), 2)

    def test_properties_merge_without_losing_meters_from_different_sources_nonoverlapping(self):
        # For first Property, PM Meters containing 2 readings for each Electricity and Natural Gas for property_1
        # This file has multiple tabs
        pm_filename = "example-pm-monthly-meter-usage.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + pm_filename
        pm_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type=SEED_DATA_SOURCES[PORTFOLIO_METER_USAGE][1],
            uploaded_filename=pm_filename,
            file=SimpleUploadedFile(name=pm_filename, content=pathlib.Path(filepath).read_bytes()),
            cycle=self.cycle,
        )
        pm_import_url = reverse("api:v3:import_files-start-save-data", args=[pm_import_file.id])
        pm_import_url += f"?organization_id={self.org.pk}"
        pm_import_post_params = {"cycle_id": self.cycle.pk}
        self.client.post(pm_import_url, pm_import_post_params)

        # For second Property, add GreenButton Meters containing 2 readings for Electricity only
        gb_filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + gb_filename
        gb_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type=SEED_DATA_SOURCES[GREEN_BUTTON][1],
            uploaded_filename=gb_filename,
            file=SimpleUploadedFile(name=gb_filename, content=pathlib.Path(filepath).read_bytes()),
            cycle=self.cycle,
            matching_results_data={"property_id": self.property_2.id},  # this is how target property is specified
        )
        gb_import_url = reverse("api:v3:import_files-start-save-data", args=[gb_import_file.id])
        gb_import_url += f"?organization_id={self.org.pk}"
        gb_import_post_params = {"cycle_id": self.cycle.pk}
        self.client.post(gb_import_url, gb_import_post_params)

        # Merge PropertyStates
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps(
            {
                "property_view_ids": [self.view_2.pk, self.view_1.pk]  # priority given to view_1
            }
        )
        self.client.post(url, post_params, content_type="application/json")

        # There should only be one PropertyView
        self.assertEqual(PropertyView.objects.count(), 1)

        # The Property of the (only) -View has all of the Meters now.
        meters = PropertyView.objects.first().property.meters

        self.assertEqual(meters.count(), 3)
        self.assertEqual(meters.get(type=Meter.ELECTRICITY_GRID, source=Meter.GREENBUTTON).meter_readings.count(), 2)
        self.assertEqual(meters.get(type=Meter.ELECTRICITY_GRID, source=Meter.PORTFOLIO_MANAGER).meter_readings.count(), 2)
        self.assertEqual(meters.get(type=Meter.NATURAL_GAS).meter_readings.count(), 2)

        # Old meters deleted, so only merged meters exist
        self.assertEqual(Meter.objects.count(), 3)
        self.assertEqual(MeterReading.objects.count(), 6)

    def test_properties_merge_without_losing_meters_when_some_meters_from_same_source_are_overlapping(self):
        # For first Property, add GreenButton Meters containing 2 readings for Electricity only
        gb_filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + gb_filename
        gb_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type=SEED_DATA_SOURCES[GREEN_BUTTON][1],
            uploaded_filename=gb_filename,
            file=SimpleUploadedFile(name=gb_filename, content=pathlib.Path(filepath).read_bytes()),
            cycle=self.cycle,
            matching_results_data={"property_id": self.property_1.id},  # this is how target property is specified
        )
        gb_import_url = reverse("api:v3:import_files-start-save-data", args=[gb_import_file.id])
        gb_import_url += f"?organization_id={self.org.pk}"
        gb_import_post_params = {"cycle_id": self.cycle.pk}
        self.client.post(gb_import_url, gb_import_post_params)

        # For second Property, add GreenButton Meters containing 2 Electricity readings: 1 overlapping
        gb_overlapping_filename = "example-GreenButton-data-1-overlapping.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + gb_overlapping_filename
        gb_overlapping_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type=SEED_DATA_SOURCES[GREEN_BUTTON][1],
            uploaded_filename=gb_overlapping_filename,
            file=SimpleUploadedFile(name=gb_overlapping_filename, content=pathlib.Path(filepath).read_bytes()),
            cycle=self.cycle,
            matching_results_data={"property_id": self.property_2.id},  # this is how target property is specified
        )
        gb_overlapping_import_url = reverse("api:v3:import_files-start-save-data", args=[gb_overlapping_import_file.id])
        gb_overlapping_import_url += f"?organization_id={self.org.pk}"
        gb_overlapping_import_post_params = {"cycle_id": self.cycle.pk}
        self.client.post(gb_overlapping_import_url, gb_overlapping_import_post_params)

        # Check that there are 2 overlapping readings (that are separate for now) out of 4.
        self.assertEqual(MeterReading.objects.count(), 4)
        tz_obj = timezone(TIME_ZONE)
        start_time_match = make_aware(datetime(2011, 3, 5, 21, 15, 0), timezone=tz_obj)
        end_time_match = make_aware(datetime(2011, 3, 5, 21, 30, 0), timezone=tz_obj)
        same_time_windows = MeterReading.objects.filter(start_time=start_time_match, end_time=end_time_match)
        self.assertEqual(same_time_windows.count(), 2)

        # Capture the overlapping reading of property_1, and ensure it's different from property_2's
        priority_property_id = self.property_1.meters.first().id
        property_1_reading = same_time_windows.get(meter_id=priority_property_id).reading
        property_2_reading = same_time_windows.exclude(meter_id=priority_property_id).get().reading
        self.assertNotEqual(property_1_reading, property_2_reading)

        # Merge PropertyStates
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps(
            {
                "property_view_ids": [self.view_2.pk, self.view_1.pk]  # priority given to view_1
            }
        )
        self.client.post(url, post_params, content_type="application/json")

        # There should only be one PropertyView
        self.assertEqual(PropertyView.objects.count(), 1)

        # The Property of the (only) -View has all of the Meters now.
        meters = PropertyView.objects.first().property.meters
        self.assertEqual(meters.count(), 1)
        self.assertEqual(meters.first().meter_readings.count(), 3)

        # Old meters deleted, so only merged meters exist
        self.assertEqual(Meter.objects.count(), 1)
        self.assertEqual(MeterReading.objects.count(), 3)

        # Check that the resulting reading used belonged to property_1
        merged_reading = MeterReading.objects.filter(start_time=start_time_match, end_time=end_time_match)
        self.assertEqual(merged_reading.count(), 1)
        self.assertEqual(merged_reading.first().reading, property_1_reading)

        # Overlapping reading that wasn't prioritized should not exist
        self.assertFalse(MeterReading.objects.filter(reading=property_2_reading).exists())

    def test_merge_assigns_new_canonical_records_to_each_resulting_record_and_old_canonical_records_are_deleted_when_not_associated_to_other_views(
        self,
    ):
        # Capture old property_ids
        persisting_property_id = self.property_1.id
        deleted_property_id = self.property_2.id

        new_cycle = self.cycle_factory.get_cycle(start=datetime(2011, 10, 10, tzinfo=get_current_timezone()))
        new_property_state = self.property_state_factory.get_property_state()
        PropertyView.objects.create(property_id=persisting_property_id, cycle=new_cycle, state=new_property_state)

        # Merge the properties
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps(
            {
                "property_view_ids": [self.view_2.pk, self.view_1.pk]  # priority given to view_1
            }
        )
        self.client.post(url, post_params, content_type="application/json")

        self.assertFalse(PropertyView.objects.filter(property_id=deleted_property_id).exists())
        self.assertFalse(Property.objects.filter(pk=deleted_property_id).exists())

        self.assertEqual(PropertyView.objects.filter(property_id=persisting_property_id).count(), 1)

    @unittest.skip("TODO: fix merging of PM and BSync meters")
    def test_properties_merge_combining_bsync_and_pm_sources(self):
        # -- SETUP
        # For first Property, PM Meters containing 2 readings for each Electricity and Natural Gas for property_1
        # This file has multiple tabs
        pm_filename = "example-pm-monthly-meter-usage.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + pm_filename
        pm_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type=SEED_DATA_SOURCES[PORTFOLIO_METER_USAGE][1],
            uploaded_filename=pm_filename,
            file=SimpleUploadedFile(name=pm_filename, content=pathlib.Path(filepath).read_bytes()),
            cycle=self.cycle,
        )
        pm_import_url = reverse("api:v3:import_files-start-save-data", args=[pm_import_file.id])
        pm_import_url += f"?organization_id={self.org.pk}"
        pm_import_post_params = {"cycle_id": self.cycle.pk}
        self.client.post(pm_import_url, pm_import_post_params)

        # For second Property, add BuildingSync file containing 6 meters
        bs_filename = "buildingsync_v2_0_bricr_workflow.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/../building_sync/tests/data/" + bs_filename
        uploaded_file = SimpleUploadedFile(filepath, pathlib.Path(filepath).read_bytes())
        bs_buildingfile = BuildingFile.objects.create(
            file=uploaded_file,
            filename=bs_filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )
        p_status, bs_property_state, bs_property_view, _ = bs_buildingfile.process(self.org.pk, self.cycle)
        self.assertTrue(p_status)
        self.assertNotEqual(None, bs_property_view)

        # verify we're starting with the assumed number of meters
        self.assertEqual(2, PropertyView.objects.get(state=self.state_1).property.meters.count())
        bs_scenarios = Scenario.objects.filter(property_state=bs_property_state)
        self.assertEqual(6, Meter.objects.filter(scenario__in=bs_scenarios).count())

        # -- ACT
        # Merge PropertyStates
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps(
            {
                "property_view_ids": [self.view_1.pk, bs_property_view.pk]  # priority given to bs_property_view
            }
        )
        self.client.post(url, post_params, content_type="application/json")

        # -- ASSERT
        # There should only be _two_ PropertyViews
        #  - the merged property view
        #  - our setUp method creates an additional one that's we don't touch in this test)
        self.assertEqual(PropertyView.objects.count(), 2)

        # get the merged property view by excluding the state we didn't touch (only one other view should exist)
        merged_property_view = PropertyView.objects.all().exclude(state__pk=self.state_2.pk)
        self.assertEqual(merged_property_view.count(), 1)
        merged_property_view = merged_property_view[0]

        meters = merged_property_view.property.meters

        self.assertEqual(meters.count(), 8)  # 2 from PM, 6 from BS
        self.assertEqual(meters.filter(type=Meter.ELECTRICITY_GRID, source=Meter.BUILDINGSYNC).count(), 3)
        self.assertEqual(meters.filter(type=Meter.NATURAL_GAS, source=Meter.BUILDINGSYNC).count(), 3)
        self.assertEqual(meters.filter(type=Meter.ELECTRICITY_GRID, source=Meter.PORTFOLIO_MANAGER).count(), 1)
        self.assertEqual(meters.filter(type=Meter.NATURAL_GAS, source=Meter.PORTFOLIO_MANAGER).count(), 1)

        # The BuildingSync data should retain their scenario information
        scenarios = merged_property_view.state.scenarios
        self.assertEqual(scenarios.count(), 3)

        # Old meters deleted, so only merged meters exist
        self.assertEqual(Meter.objects.count(), 8)
        # Combined total of 76 readings
        self.assertEqual(MeterReading.objects.count(), 76)


class PropertyUnmergeViewTests(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)

        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.client.login(**user_details)

        self.state_1 = self.property_state_factory.get_property_state(
            address_line_1="1 property state",
            pm_property_id="5766973",  # this allows the Property to be targeted for PM meter additions
        )
        self.property_1 = self.property_factory.get_property()
        self.view_1 = PropertyView.objects.create(property=self.property_1, cycle=self.cycle, state=self.state_1)

        self.state_2 = self.property_state_factory.get_property_state(address_line_1="2 property state")
        self.property_2 = self.property_factory.get_property()
        self.view_2 = PropertyView.objects.create(property=self.property_2, cycle=self.cycle, state=self.state_2)

        self.import_record = ImportRecord.objects.create(
            owner=self.user, last_modified_by=self.user, super_organization=self.org, access_level_instance=self.org.root
        )

        # Give 2 meters to one of the properties
        gb_filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + gb_filename
        gb_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type=SEED_DATA_SOURCES[GREEN_BUTTON][1],
            uploaded_filename=gb_filename,
            file=SimpleUploadedFile(name=gb_filename, content=pathlib.Path(filepath).read_bytes()),
            cycle=self.cycle,
            matching_results_data={"property_id": self.property_1.id},  # this is how target property is specified
        )
        gb_import_url = reverse("api:v3:import_files-start-save-data", args=[gb_import_file.id])
        gb_import_url += f"?organization_id={self.org.pk}"
        gb_import_post_params = {"cycle_id": self.cycle.pk}
        self.client.post(gb_import_url, gb_import_post_params)

        # Merge the properties
        url = reverse("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        post_params = json.dumps(
            {
                "property_view_ids": [self.view_2.pk, self.view_1.pk]  # priority given to view_1
            }
        )
        self.client.post(url, post_params, content_type="application/json")

    def test_properties_unmerge_without_losing_labels(self):
        # Create 3 Labels - add 2 to view
        label_factory = FakeStatusLabelFactory(organization=self.org)

        label_1 = label_factory.get_statuslabel()
        label_2 = label_factory.get_statuslabel()

        view = PropertyView.objects.first()  # There's only one PropertyView
        view.labels.add(label_1, label_2)

        # Unmerge the properties
        url = reverse("api:v3:properties-unmerge", args=[view.id]) + f"?organization_id={self.org.pk}"
        self.client.put(url, content_type="application/json")

        for new_view in PropertyView.objects.all():
            self.assertEqual(new_view.labels.count(), 2)
            label_names = list(new_view.labels.values_list("name", flat=True))
            self.assertCountEqual(label_names, [label_1.name, label_2.name])

    def test_unmerging_two_properties_with_meters_gives_meters_to_both_of_the_resulting_records(self):
        # Unmerge the properties
        view_id = PropertyView.objects.first().id  # There's only one PropertyView
        url = reverse("api:v3:properties-unmerge", args=[view_id]) + f"?organization_id={self.org.pk}"
        self.client.put(url, content_type="application/json")

        # Verify 2 -Views now exist
        self.assertEqual(PropertyView.objects.count(), 2)

        # Check that meters and readings of each -View exists and verify they are identical.
        reading_sets = []
        for view in PropertyView.objects.all():
            self.assertEqual(view.property.meters.count(), 1)
            self.assertEqual(view.property.meters.first().meter_readings.count(), 2)
            reading_sets.append(
                [
                    {
                        "start_time": reading.start_time,
                        "end_time": reading.end_time,
                        "reading": reading.reading,
                        "source_unit": reading.source_unit,
                        "conversion_factor": reading.conversion_factor,
                    }
                    for reading in view.property.meters.first().meter_readings.all().order_by("start_time")
                ]
            )

        self.assertEqual(reading_sets[0], reading_sets[1])

    def test_unmerging_two_properties_with_notes(self):
        view = PropertyView.objects.first()  # There's only one PropertyView

        # add note
        note_factory = FakeNoteFactory(organization=self.org, user=self.user)
        note1 = note_factory.get_note(name="non_default_name_1")
        view.notes.add(note1)

        # Unmerge the properties
        url = reverse("api:v3:properties-unmerge", args=[view.id]) + f"?organization_id={self.org.pk}"
        self.client.put(url, content_type="application/json")
        view_1, view_2 = PropertyView.objects.all()

        assert view_1.notes.count() == 1
        assert view_2.notes.count() == 2
        assert view_2.notes.first().text == f"This PropertyView was unmerged from PropertyView id {view_1.id}"

    def test_unmerge_results_in_the_use_of_new_canonical_records_and_deletion_of_old_canonical_state_if_unrelated_to_any_views(self):
        # Capture "old" property_id - there's only one PropertyView
        view = PropertyView.objects.first()
        property_id = view.property_id

        # Unmerge the properties
        url = reverse("api:v3:properties-unmerge", args=[view.id]) + f"?organization_id={self.org.pk}"
        self.client.put(url, content_type="application/json")

        self.assertTrue(Property.objects.filter(pk=property_id).exists())
        self.assertEqual(Property.objects.count(), 2)

    def test_unmerge_results_in_the_persistence_of_old_canonical_state_if_related_to_any_views(self):
        # Associate only canonical property with records across Cycle
        view = PropertyView.objects.first()
        property_id = view.property_id

        new_cycle = self.cycle_factory.get_cycle(start=datetime(2011, 10, 10, tzinfo=get_current_timezone()))
        new_property_state = self.property_state_factory.get_property_state()
        PropertyView.objects.create(property_id=property_id, cycle=new_cycle, state=new_property_state)

        # Unmerge the properties
        url = reverse("api:v3:properties-unmerge", args=[view.id]) + f"?organization_id={self.org.pk}"
        self.client.put(url, content_type="application/json")

        self.assertTrue(Property.objects.filter(pk=view.property_id).exists())
        self.assertEqual(Property.objects.count(), 2)


class PropertyViewExportTests(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.column_list_factory = FakeColumnListProfileFactory(organization=self.org)
        self.client.login(**user_details)

    def test_export_bsync_works_with_default_profile(self):
        # -- Setup
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        view = PropertyView.objects.create(property=prprty, cycle=self.cycle, state=state)
        profile = ColumnMappingProfile.objects.get(profile_type=ColumnMappingProfile.BUILDINGSYNC_DEFAULT)

        # -- Act
        url = reverse("api:v3:properties-building-sync", args=[view.id])
        response = self.client.get(url, {"profile_id": profile.id, "organization_id": prprty.organization.id})

        # -- Assert
        self.assertEqual(200, response.status_code, response.content)

    def test_export_bsync_works_with_custom_profile(self):
        """Tests that using a different column mapping profile from the default
        results in a different xml output
        """
        # -- Setup
        # manually set the lat and long
        state = self.property_state_factory.get_property_state()
        orig_lat = 5555
        orig_long = 4444
        state.latitude = orig_lat
        state.longitude = orig_long
        state.save()

        prprty = self.property_factory.get_property()
        view = PropertyView.objects.create(property=prprty, cycle=self.cycle, state=state)

        # create a profile mapping where longitude and latitude are swapped
        profile_mappings = default_buildingsync_profile_mappings()
        for mapping in profile_mappings:
            if mapping["to_field"] == "longitude":
                mapping["to_field"] = "latitude"
            elif mapping["to_field"] == "latitude":
                mapping["to_field"] = "longitude"

        custom_profile_name = "BSync Custom Profile"
        self.org.columnmappingprofile_set.create(
            name=custom_profile_name, mappings=profile_mappings, profile_type=ColumnMappingProfile.BUILDINGSYNC_CUSTOM
        )
        custom_profile = self.org.columnmappingprofile_set.get(name=custom_profile_name)

        # grab the default profile to export with for comparison
        default_profile = self.org.columnmappingprofile_set.get(profile_type=ColumnMappingProfile.BUILDINGSYNC_DEFAULT)

        # -- Act
        url = reverse("api:v3:properties-building-sync", args=[view.id])
        default_export_response = self.client.get(url, {"profile_id": default_profile.id, "organization_id": prprty.organization.id})
        url = reverse("api:v3:properties-building-sync", args=[view.id])
        custom_export_response = self.client.get(url, {"profile_id": custom_profile.id, "organization_id": prprty.organization.id})

        # -- Assert
        self.assertEqual(200, default_export_response.status_code, default_export_response.content)
        self.assertEqual(200, custom_export_response.status_code, custom_export_response.content)

        # check that longitude and latitude were swapped by finding different lines in the results
        default_lines = default_export_response.content.decode().split("\n")
        custom_lines = custom_export_response.content.decode().split("\n")
        diffs = [line.strip() for line in set(default_lines).symmetric_difference(custom_lines)]
        expected_diffs = [
            "<auc:Latitude>5555.0</auc:Latitude>",
            "<auc:Longitude>4444.0</auc:Longitude>",
            "<auc:Latitude>4444.0</auc:Latitude>",
            "<auc:Longitude>5555.0</auc:Longitude>",
        ]
        self.assertCountEqual(expected_diffs, diffs)


class PropertyMeterViewTests(DataMappingBaseTestCase):
    def setUp(self):
        self.user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        self.user = User.objects.create_superuser(email="test_user@demo.com", **self.user_details)
        self.org, _, _ = create_organization(self.user)

        # For some reason, defaults weren't established consistently for each test.
        self.org.display_meter_units = Organization._default_display_meter_units.copy()
        self.org.save()
        self.client.login(**self.user_details)

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        property_details = self.property_state_factory.get_details()
        property_details["organization_id"] = self.org.id

        # pm_property_ids must match those within example-monthly-meter-usage.xlsx
        self.pm_property_id_1 = "5766973"
        self.pm_property_id_2 = "5766975"

        property_details["pm_property_id"] = self.pm_property_id_1
        state_1 = PropertyState(**property_details)
        state_1.save()
        self.state_1 = PropertyState.objects.get(pk=state_1.id)

        property_details["pm_property_id"] = self.pm_property_id_2
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

        self.import_record = ImportRecord.objects.create(
            owner=self.user, last_modified_by=self.user, super_organization=self.org, access_level_instance=self.org.root
        )

        # This file has multiple tabs
        filename = "example-pm-monthly-meter-usage.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type=SEED_DATA_SOURCES[PORTFOLIO_METER_USAGE][1],
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=pathlib.Path(filepath).read_bytes()),
            cycle=self.cycle,
        )

    def test_property_meters_endpoint_returns_a_list_of_meters_of_a_view(self):
        # add meters and readings to property associated to property_view_1
        save_raw_data(self.import_file.id)

        # create GB gas meter
        meter_details = {
            "property_id": self.property_view_1.property.id,
            "type": Meter.NATURAL_GAS,
            "source": Meter.GREENBUTTON,
            "source_id": "/v1/User/000/UsagePoint/123fakeID/MeterReading/000",
        }
        gb_gas_meter = Meter.objects.create(**meter_details)

        url = (
            reverse("api:v3:property-meters-list", kwargs={"property_pk": self.property_view_1.id}) + "?organization_id=" + str(self.org.id)
        )

        result = self.client.get(url)
        result_dict = json.loads(result.content)

        electric_meter = Meter.objects.get(property_id=self.property_view_1.property_id, type=Meter.ELECTRICITY_GRID)
        gas_meter = Meter.objects.get(property_id=self.property_view_1.property_id, type=Meter.NATURAL_GAS, source=Meter.PORTFOLIO_MANAGER)
        expectation = [
            {
                "id": electric_meter.id,
                "property_id": self.property_view_1.property_id,
                "system_id": None,
                "system_name": None,
                "type": "Electric - Grid",
                "source": "Portfolio Manager",
                "source_id": "5766973-0",
                "scenario_id": None,
                "scenario_name": None,
                "is_virtual": False,
                "alias": "Electric - Grid - Portfolio Manager - 5766973-0",
                "config": {
                    "connection": "outside",
                    "direction": "imported",
                    "group_id": None,
                    "service_id": None,
                    "system_id": None,
                    "use": "outside",
                },
                "connection_type": "Imported",
                "service_name": None,
                "service_group": None,
                "service_id": None,
                "property_display_field": self.property_view_1.state.address_line_1,
                "view_id": self.property_view_1.id,
            },
            {
                "id": gas_meter.id,
                "property_id": self.property_view_1.property_id,
                "system_id": None,
                "system_name": None,
                "type": "Natural Gas",
                "source": "Portfolio Manager",
                "source_id": "5766973-1",
                "scenario_id": None,
                "scenario_name": None,
                "is_virtual": False,
                "alias": "Natural Gas - Portfolio Manager - 5766973-1",
                "config": {
                    "connection": "outside",
                    "direction": "imported",
                    "group_id": None,
                    "service_id": None,
                    "system_id": None,
                    "use": "outside",
                },
                "connection_type": "Imported",
                "service_name": None,
                "service_group": None,
                "service_id": None,
                "property_display_field": self.property_view_1.state.address_line_1,
                "view_id": self.property_view_1.id,
            },
            {
                "id": gb_gas_meter.id,
                "property_id": self.property_view_1.property_id,
                "system_id": None,
                "system_name": None,
                "type": "Natural Gas",
                "source": "GreenButton",
                "source_id": "123fakeID",
                "scenario_id": None,
                "scenario_name": None,
                "is_virtual": False,
                "alias": "Natural Gas - GreenButton - 123fakeID",
                "config": {
                    "connection": "outside",
                    "direction": "imported",
                    "group_id": None,
                    "service_id": None,
                    "system_id": None,
                    "use": "outside",
                },
                "connection_type": "Imported",
                "service_name": None,
                "service_group": None,
                "service_id": None,
                "property_display_field": self.property_view_1.state.address_line_1,
                "view_id": self.property_view_1.id,
            },
        ]

        self.assertCountEqual(result_dict, expectation)

    def test_property_meter_usage_returns_meter_readings_and_column_defs_given_property_view_and_nondefault_meter_display_org_settings(
        self,
    ):
        # Update settings for display meter units to change it from the default values.
        self.org.display_meter_units["Electric - Grid"] = "kWh (thousand Watt-hours)"
        self.org.display_meter_units["Natural Gas"] = "kcf (thousand cubic feet)"
        self.org.save()

        # add meters and readings to property associated to property_view_1
        save_raw_data(self.import_file.id)

        meter_details = {
            "source": Meter.GREENBUTTON,
            "source_id": "/v1/User/000/UsagePoint/123fakeID/MeterReading/000",
            "type": Meter.NATURAL_GAS,
            "property_id": self.property_view_1.property.id,
        }
        gb_gas_meter = Meter.objects.create(**meter_details)

        tz_obj = timezone(TIME_ZONE)
        gb_gas_reading_details = {
            "start_time": make_aware(datetime(2016, 1, 1, 0, 0, 0), timezone=tz_obj),
            "end_time": make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=tz_obj),
            "reading": 1000,
            "source_unit": "kBtu (thousand Btu)",
            "conversion_factor": 1,
            "meter_id": gb_gas_meter.id,
        }
        MeterReading.objects.create(**gb_gas_reading_details)

        url = reverse("api:v3:properties-meter-usage", kwargs={"pk": self.property_view_1.id})
        url += f"?organization_id={self.org.pk}"
        post_params = json.dumps(
            {
                "interval": "Exact",
                "excluded_meter_ids": [],
            }
        )
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            "readings": [
                {
                    "start_time": "2016-01-01 00:00:00",
                    "end_time": "2016-02-01 00:00:00",
                    "Electric - Grid - Portfolio Manager - 5766973-0": (597478.9 / 3.41),
                    "Natural Gas - Portfolio Manager - 5766973-1": 576000.2 / 1026,
                    "Natural Gas - GreenButton - 123fakeID": 1000 / 1026,
                },
                {
                    "start_time": "2016-02-01 00:00:00",
                    "end_time": "2016-03-01 00:00:00",
                    "Electric - Grid - Portfolio Manager - 5766973-0": (548603.7 / 3.41),
                    "Natural Gas - Portfolio Manager - 5766973-1": 488000.1 / 1026,
                },
            ],
            "column_defs": [
                {
                    "field": "start_time",
                    "_filter_type": "datetime",
                },
                {
                    "field": "end_time",
                    "_filter_type": "datetime",
                },
                {
                    "field": "Electric - Grid - Portfolio Manager - 5766973-0",
                    "displayName": "Electric - Grid - Portfolio Manager - 5766973-0 (kWh (thousand Watt-hours))",
                    "_filter_type": "reading",
                },
                {
                    "field": "Natural Gas - Portfolio Manager - 5766973-1",
                    "displayName": "Natural Gas - Portfolio Manager - 5766973-1 (kcf (thousand cubic feet))",
                    "_filter_type": "reading",
                },
                {
                    "field": "Natural Gas - GreenButton - 123fakeID",
                    "displayName": "Natural Gas - GreenButton - 123fakeID (kcf (thousand cubic feet))",
                    "_filter_type": "reading",
                },
            ],
        }

        self.assertCountEqual(result_dict["readings"], expectation["readings"])
        self.assertCountEqual(result_dict["column_defs"], expectation["column_defs"])

    def test_property_meter_usage_returns_meter_readings_and_column_defs_when_cost_meter_included(self):
        filename = "example-pm-monthly-meter-usage-2-cost-meters.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        cost_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type=SEED_DATA_SOURCES[PORTFOLIO_METER_USAGE][1],
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=pathlib.Path(filepath).read_bytes()),
            cycle=self.cycle,
        )

        # add meters and readings to property associated to property_view_1
        save_raw_data(cost_import_file.id)

        url = reverse("api:v3:properties-meter-usage", kwargs={"pk": self.property_view_1.id})
        url += f"?organization_id={self.org.pk}"

        post_params = json.dumps(
            {
                "interval": "Exact",
                "excluded_meter_ids": [],
            }
        )
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            "readings": [
                {
                    "start_time": "2016-01-01 00:00:00",
                    "end_time": "2016-02-01 00:00:00",
                    "Electric - Grid - Portfolio Manager - 5766973-0": 597478.9 / 3.41,
                    "Cost - Portfolio Manager - 5766973-0": 100,
                    "Natural Gas - Portfolio Manager - 5766973-1": 576000.2,
                    "Cost - Portfolio Manager - 5766973-1": 300,
                },
                {
                    "start_time": "2016-02-01 00:00:00",
                    "end_time": "2016-03-01 00:00:00",
                    "Electric - Grid - Portfolio Manager - 5766973-0": 548603.7 / 3.41,
                    "Cost - Portfolio Manager - 5766973-0": 200,
                    "Natural Gas - Portfolio Manager - 5766973-1": 488000.1,
                    "Cost - Portfolio Manager - 5766973-1": 400,
                },
            ],
            "column_defs": [
                {
                    "field": "start_time",
                    "_filter_type": "datetime",
                },
                {
                    "field": "end_time",
                    "_filter_type": "datetime",
                },
                {
                    "field": "Electric - Grid - Portfolio Manager - 5766973-0",
                    "displayName": "Electric - Grid - Portfolio Manager - 5766973-0 (kWh (thousand Watt-hours))",
                    "_filter_type": "reading",
                },
                {
                    "field": "Natural Gas - Portfolio Manager - 5766973-1",
                    "displayName": "Natural Gas - Portfolio Manager - 5766973-1 (kBtu (thousand Btu))",
                    "_filter_type": "reading",
                },
                {
                    "field": "Cost - Portfolio Manager - 5766973-0",
                    "displayName": "Cost - Portfolio Manager - 5766973-0 (US Dollars)",
                    "_filter_type": "reading",
                },
                {
                    "field": "Cost - Portfolio Manager - 5766973-1",
                    "displayName": "Cost - Portfolio Manager - 5766973-1 (US Dollars)",
                    "_filter_type": "reading",
                },
            ],
        }

        self.assertCountEqual(result_dict["readings"], expectation["readings"])
        self.assertCountEqual(result_dict["column_defs"], expectation["column_defs"])

    def test_property_meter_usage_returns_meter_readings_according_to_thermal_conversion_preferences_of_an_org_if_applicable_for_display_settings(
        self,
    ):
        # update the org settings thermal preference and display preference
        self.org.thermal_conversion_assumption = Organization.CAN
        self.org.display_meter_units["Diesel"] = "Liters"
        self.org.display_meter_units["Coke"] = "Lbs. (pounds)"
        self.org.save()

        # add meters and readings to property associated to property_view_1
        meter_details = {
            "source": Meter.PORTFOLIO_MANAGER,
            "source_id": "123fakeID",
            "type": Meter.DIESEL,
            "property_id": self.property_view_1.property.id,
        }
        diesel_meter = Meter.objects.create(**meter_details)

        tz_obj = timezone(TIME_ZONE)
        diesel_reading_details = {
            "start_time": make_aware(datetime(2016, 1, 1, 0, 0, 0), timezone=tz_obj),
            "end_time": make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=tz_obj),
            "reading": 10,
            "source_unit": "kBtu (thousand Btu)",
            "conversion_factor": 1,
            "meter_id": diesel_meter.id,
        }
        MeterReading.objects.create(**diesel_reading_details)

        meter_details["type"] = Meter.COKE
        meter_details["source_id"] = "456fakeID"
        coke_meter = Meter.objects.create(**meter_details)

        coke_reading_details = {
            "start_time": make_aware(datetime(2016, 1, 1, 0, 0, 0), timezone=tz_obj),
            "end_time": make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=tz_obj),
            "reading": 100,
            "source_unit": "kBtu (thousand Btu)",
            "conversion_factor": 1,
            "meter_id": coke_meter.id,
        }
        MeterReading.objects.create(**coke_reading_details)

        post_params = json.dumps(
            {
                "interval": "Exact",
                "excluded_meter_ids": [],
            }
        )

        url = reverse("api:v3:properties-meter-usage", kwargs={"pk": self.property_view_1.id})
        url += f"?organization_id={self.org.pk}"
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        display_readings = [
            {
                "start_time": "2016-01-01 00:00:00",
                "end_time": "2016-02-01 00:00:00",
                "Diesel - Portfolio Manager - 123fakeID": 10 / 36.30,
                "Coke - Portfolio Manager - 456fakeID": 100 / 12.39,
            },
        ]

        self.assertCountEqual(result_dict["readings"], display_readings)

    def test_property_meter_usage_can_return_monthly_meter_readings_and_column_defs_with_nondefault_display_setting(self):
        # Update settings for display meter units to change it from the default values.
        self.org.display_meter_units["Electric - Grid"] = "kWh (thousand Watt-hours)"
        self.org.save()

        # add initial meters and readings
        save_raw_data(self.import_file.id)

        # add additional entries for each initial meter
        tz_obj = timezone(TIME_ZONE)
        for meter in Meter.objects.all():
            # March 2016 reading
            reading_details = {
                "meter_id": meter.id,
                "start_time": make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=tz_obj),
                "end_time": make_aware(datetime(2016, 4, 1, 0, 0, 0), timezone=tz_obj),
                "reading": 100,
                "source_unit": "kBtu (thousand Btu)",
                "conversion_factor": 1,
            }
            MeterReading.objects.create(**reading_details)

            # May 2016 reading
            reading_details["start_time"] = make_aware(datetime(2016, 5, 1, 0, 0, 0), timezone=tz_obj)
            reading_details["end_time"] = make_aware(datetime(2016, 6, 1, 0, 0, 0), timezone=tz_obj)
            reading_details["reading"] = 200
            MeterReading.objects.create(**reading_details)

        url = reverse("api:v3:properties-meter-usage", kwargs={"pk": self.property_view_1.id})
        url += f"?organization_id={self.org.pk}"

        post_params = json.dumps(
            {
                "interval": "Month",
                "excluded_meter_ids": [],
            }
        )
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            "readings": [
                {
                    "month": "January 2016",
                    "Electric - Grid - Portfolio Manager - 5766973-0": round(597478.9 / 3.41, 2),
                    "Natural Gas - Portfolio Manager - 5766973-1": 576000.2,
                },
                {
                    "month": "February 2016",
                    "Electric - Grid - Portfolio Manager - 5766973-0": round(548603.7 / 3.41, 2),
                    "Natural Gas - Portfolio Manager - 5766973-1": 488000.1,
                },
                {
                    "month": "March 2016",
                    "Electric - Grid - Portfolio Manager - 5766973-0": round(100 / 3.41, 2),
                    "Natural Gas - Portfolio Manager - 5766973-1": 100,
                },
                {
                    "month": "May 2016",
                    "Electric - Grid - Portfolio Manager - 5766973-0": round(200 / 3.41, 2),
                    "Natural Gas - Portfolio Manager - 5766973-1": 200,
                },
            ],
            "column_defs": [
                {
                    "field": "month",
                    "_filter_type": "datetime",
                },
                {
                    "field": "Electric - Grid - Portfolio Manager - 5766973-0",
                    "displayName": "Electric - Grid - Portfolio Manager - 5766973-0 (kWh (thousand Watt-hours))",
                    "_filter_type": "reading",
                },
                {
                    "field": "Natural Gas - Portfolio Manager - 5766973-1",
                    "displayName": "Natural Gas - Portfolio Manager - 5766973-1 (kBtu (thousand Btu))",
                    "_filter_type": "reading",
                },
            ],
        }

        self.assertCountEqual(result_dict["readings"], expectation["readings"])
        self.assertCountEqual(result_dict["column_defs"], expectation["column_defs"])

    def test_property_meter_usage_can_return_monthly_meter_readings_and_column_defs_for_submonthly_data_with_dst_transitions_and_specific_meters(
        self,
    ):
        # add initial meters and readings
        save_raw_data(self.import_file.id)

        property_1_electric_meter = Meter.objects.get(source_id="5766973-0")
        # add additional sub-monthly entries for each initial meter
        tz_obj = timezone(TIME_ZONE)
        for meter in Meter.objects.all():
            # November 2019 reading between DST transition
            reading_details = {
                "meter_id": meter.id,
                "start_time": make_aware(datetime(2019, 11, 3, 1, 59, 59), timezone=tz_obj, is_dst=True),
                "end_time": make_aware(datetime(2019, 11, 3, 1, 59, 59), timezone=tz_obj, is_dst=False),
                "reading": 100,
                "source_unit": "kBtu (thousand Btu)",
                "conversion_factor": 1,
            }
            MeterReading.objects.create(**reading_details)

            # November 2019 reading after DST transition
            reading_details["start_time"] = make_aware(datetime(2019, 11, 3, 2, 0, 0), timezone=tz_obj)
            reading_details["end_time"] = make_aware(datetime(2019, 11, 3, 3, 0, 0), timezone=tz_obj)
            reading_details["reading"] = 200
            MeterReading.objects.create(**reading_details)

            # Create a reading for only one of the meters that will be filtered out completely
            if meter.source_id == property_1_electric_meter.id:
                reading_details["start_time"] = make_aware(datetime(2020, 11, 3, 2, 0, 0), timezone=tz_obj)
                reading_details["end_time"] = make_aware(datetime(2020, 11, 3, 3, 0, 0), timezone=tz_obj)
                reading_details["reading"] = 10000000
                MeterReading.objects.create(**reading_details)

        url = reverse("api:v3:properties-meter-usage", kwargs={"pk": self.property_view_1.id})
        url += f"?organization_id={self.org.pk}"

        post_params = json.dumps(
            {
                "interval": "Month",
                "excluded_meter_ids": [property_1_electric_meter.id],
            }
        )
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            "readings": [
                {
                    "month": "January 2016",
                    "Natural Gas - Portfolio Manager - 5766973-1": 576000.2,
                },
                {
                    "month": "February 2016",
                    "Natural Gas - Portfolio Manager - 5766973-1": 488000.1,
                },
                {
                    "month": "November 2019",
                    "Natural Gas - Portfolio Manager - 5766973-1": 300,
                },
            ],
            "column_defs": [
                {
                    "field": "month",
                    "_filter_type": "datetime",
                },
                {
                    "field": "Natural Gas - Portfolio Manager - 5766973-1",
                    "displayName": "Natural Gas - Portfolio Manager - 5766973-1 (kBtu (thousand Btu))",
                    "_filter_type": "reading",
                },
            ],
        }

        self.assertCountEqual(result_dict["readings"], expectation["readings"])
        self.assertCountEqual(result_dict["column_defs"], expectation["column_defs"])

    def test_property_meter_usage_can_return_annual_meter_readings_and_column_defs_while_handling_a_nondefault_display_setting(self):
        # Update settings for display meter units to change it from the default values.
        self.org.display_meter_units["Electric - Grid"] = "kWh (thousand Watt-hours)"
        self.org.save()

        # add initial meters and readings
        save_raw_data(self.import_file.id)

        # add additional 2018 entries for each initial meter
        tz_obj = timezone(TIME_ZONE)
        for meter in Meter.objects.all():
            # March 2018 reading
            reading_details = {
                "meter_id": meter.id,
                "start_time": make_aware(datetime(2018, 3, 1, 0, 0, 0), timezone=tz_obj),
                "end_time": make_aware(datetime(2018, 4, 1, 0, 0, 0), timezone=tz_obj),
                "reading": 100,
                "source_unit": "kBtu (thousand Btu)",
                "conversion_factor": 1,
            }
            MeterReading.objects.create(**reading_details)

            # May 2018 reading
            reading_details["start_time"] = make_aware(datetime(2018, 5, 1, 0, 0, 0), timezone=tz_obj)
            reading_details["end_time"] = make_aware(datetime(2018, 6, 1, 0, 0, 0), timezone=tz_obj)
            reading_details["reading"] = 200
            MeterReading.objects.create(**reading_details)

        url = reverse("api:v3:properties-meter-usage", kwargs={"pk": self.property_view_1.id})
        url += f"?organization_id={self.org.pk}"

        post_params = json.dumps(
            {
                "interval": "Year",
                "excluded_meter_ids": [],
            }
        )
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            "readings": [
                {
                    "year": 2016,
                    "Electric - Grid - Portfolio Manager - 5766973-0": (597478.9 + 548603.7) / 3.41,
                    "Natural Gas - Portfolio Manager - 5766973-1": 576000.2 + 488000.1,
                },
                {
                    "year": 2018,
                    "Electric - Grid - Portfolio Manager - 5766973-0": (100 + 200) / 3.41,
                    "Natural Gas - Portfolio Manager - 5766973-1": 100 + 200,
                },
            ],
            "column_defs": [
                {
                    "field": "year",
                    "_filter_type": "datetime",
                },
                {
                    "field": "Electric - Grid - Portfolio Manager - 5766973-0",
                    "displayName": "Electric - Grid - Portfolio Manager - 5766973-0 (kWh (thousand Watt-hours))",
                    "_filter_type": "reading",
                },
                {
                    "field": "Natural Gas - Portfolio Manager - 5766973-1",
                    "displayName": "Natural Gas - Portfolio Manager - 5766973-1 (kBtu (thousand Btu))",
                    "_filter_type": "reading",
                },
            ],
        }

        self.assertCountEqual(result_dict["readings"], expectation["readings"])
        self.assertCountEqual(result_dict["column_defs"], expectation["column_defs"])

    def test_property_meter_usage_can_filter_when_usages_span_a_single_month(self):
        save_raw_data(self.import_file.id)

        # add additional entries for the Electricity meter
        tz_obj = timezone(TIME_ZONE)
        meter = Meter.objects.get(property_id=self.property_view_1.property.id, type=Meter.type_lookup["Electric - Grid"])

        # 2020 January-February reading has 1 full day in January 1 full day in February.
        # The reading should be split 1/2 January (50) and 1/2 February (50)
        reading_details = {
            "meter_id": meter.id,
            "start_time": make_aware(datetime(2020, 1, 31, 0, 0, 0), timezone=tz_obj),
            "end_time": make_aware(datetime(2020, 2, 2, 0, 0, 0), timezone=tz_obj),
            "reading": 100 * 3.41,
            "source_unit": "kBtu (thousand Btu)",
            "conversion_factor": 1,
        }
        MeterReading.objects.create(**reading_details)

        # 2020 March to April reading has 1 day in march, and 2 days in april.
        # The reading should be split 1/3 march (100) and 2/3 april (200)
        reading_details = {
            "meter_id": meter.id,
            "start_time": make_aware(datetime(2020, 3, 31, 0, 0, 0), timezone=tz_obj),
            "end_time": make_aware(datetime(2020, 4, 3, 0, 0, 0), timezone=tz_obj),
            "reading": 300 * 3.41,
            "source_unit": "kBtu (thousand Btu)",
            "conversion_factor": 1,
        }
        MeterReading.objects.create(**reading_details)

        # 2020 May to July shows readings can span multiple months.
        # The reading should be split 1/32 May (10), 30/32 June (300), 1/32 July (10)
        reading_details = {
            "meter_id": meter.id,
            "start_time": make_aware(datetime(2020, 5, 31, 0, 0, 0), timezone=tz_obj),
            "end_time": make_aware(datetime(2020, 7, 2, 0, 0, 0), timezone=tz_obj),
            "reading": 320 * 3.41,
            "source_unit": "kBtu (thousand Btu)",
            "conversion_factor": 1,
        }
        MeterReading.objects.create(**reading_details)

        url = reverse("api:v3:properties-meter-usage", kwargs={"pk": self.property_view_1.id})
        url += f"?organization_id={self.org.pk}"

        post_params = json.dumps(
            {
                "interval": "Month",
                "excluded_meter_ids": [],
            }
        )
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            "readings": [
                {
                    "Electric - Grid - Portfolio Manager - 5766973-0": 175213.75,
                    "Natural Gas - Portfolio Manager - 5766973-1": 576000.2,
                    "month": "January 2016",
                },
                {
                    "Electric - Grid - Portfolio Manager - 5766973-0": 160880.85,
                    "Natural Gas - Portfolio Manager - 5766973-1": 488000.1,
                    "month": "February 2016",
                },
                {
                    "month": "January 2020",
                    "Electric - Grid - Portfolio Manager - 5766973-0": 50,
                },
                {
                    "month": "February 2020",
                    "Electric - Grid - Portfolio Manager - 5766973-0": 50,
                },
                {
                    "month": "March 2020",
                    "Electric - Grid - Portfolio Manager - 5766973-0": 100,
                },
                {
                    "month": "April 2020",
                    "Electric - Grid - Portfolio Manager - 5766973-0": 200,
                },
                {
                    "month": "May 2020",
                    "Electric - Grid - Portfolio Manager - 5766973-0": 10,
                },
                {
                    "month": "June 2020",
                    "Electric - Grid - Portfolio Manager - 5766973-0": 300,
                },
                {
                    "month": "July 2020",
                    "Electric - Grid - Portfolio Manager - 5766973-0": 10,
                },
            ],
            "column_defs": [
                {
                    "field": "month",
                    "_filter_type": "datetime",
                },
                {
                    "field": "Electric - Grid - Portfolio Manager - 5766973-0",
                    "displayName": "Electric - Grid - Portfolio Manager - 5766973-0 (kWh (thousand Watt-hours))",
                    "_filter_type": "reading",
                },
                {
                    "field": "Natural Gas - Portfolio Manager - 5766973-1",
                    "displayName": "Natural Gas - Portfolio Manager - 5766973-1 (kBtu (thousand Btu))",
                    "_filter_type": "reading",
                },
            ],
        }

        self.assertCountEqual(result_dict["readings"], expectation["readings"])
        self.assertCountEqual(result_dict["column_defs"], expectation["column_defs"])


class PropertyViewUpdateWithESPMTests(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        selfvars = self.set_up(PORTFOLIO_RAW, user_details["username"], user_details["password"])
        self.user, self.org, self.import_file_1, self.import_record_1, self.cycle_1 = selfvars

        # create the test factories
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.column_list_factory = FakeColumnListProfileFactory(organization=self.org)

        # log into the client
        self.client.login(**user_details)

    def test_update_property_view_with_espm(self):
        """Simple test to verify that the property state is merged with an updated
        ESPM download XLSX file."""
        pm_property_id = "22482007"
        pv = self.property_view_factory.get_property_view(cycle=self.cycle_1, pm_property_id=pm_property_id)
        self.assertTrue(pv.state.pm_property_id, pm_property_id)

        # save some of the pv state's data to verify merging
        pv_city = pv.state.city
        pv_address_line_1 = pv.state.address_line_1
        pv_site_eui = pv.state.site_eui

        mapping_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "mappings", "espm-single-mapping.csv")

        # need to upload the mappings for the ESPM data to a new profile
        mapping_profile = ColumnMappingProfile.create_from_file(mapping_filepath, self.org, "ESPM", overwrite_if_exists=True)

        test_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", f"portfolio-manager-single-{pm_property_id}.xlsx")

        url = reverse("api:v3:properties-update-with-espm", args=[pv.id])
        url += f"?organization_id={self.org.id}&cycle_id={self.cycle_1.id}&mapping_profile_id={mapping_profile.id}"
        with open(test_filepath, "rb") as doc:
            # need to encode the data as multipart form data since this is a PUT. A
            # POST in the client defaults to multipart, so in a PUT we have to construct it.
            response = self.client.put(
                path=url,
                data=encode_multipart(data={"file": doc, "file_type": "XLSX", "name": doc.name}, boundary=BOUNDARY),
                content_type=MULTIPART_CONTENT,
            )
            self.assertEqual(response.status_code, 200)

        # now spot check that some of fields were updated
        pv.refresh_from_db()
        self.assertNotEqual(pv.state.city, pv_city)
        self.assertNotEqual(pv.state.address_line_1, pv_address_line_1)
        # site_eui should not have changed
        self.assertEqual(pv.state.site_eui.magnitude, pv_site_eui)

        # check that the values are what is in the XLSX file
        self.assertEqual(pv.state.city, "WASHINGTON")
        self.assertEqual(pv.state.address_line_1, "2425 N STREET NW")

        # verify that the property has meters too, which came from the XLSX file
        self.assertEqual(pv.property.meters.count(), 2)

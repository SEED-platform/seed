"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import base64
import json
import time
from datetime import datetime
from random import randint

import pytest
import pytz
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from xlrd import open_workbook

from seed.landing.models import SEEDUser as User
from seed.lib.progress_data.progress_data import ProgressData
from seed.models import (
    Column,
    Cycle,
    DerivedColumn,
    Note,
    PropertyView,
    TaxLotProperty,
    TaxLotView,
)
from seed.serializers.pint import DEFAULT_UNITS
from seed.tasks import set_update_to_now
from seed.test_helpers.fake import (
    FakeDerivedColumnFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeStatusLabelFactory,
    FakeTaxLotPropertyFactory,
    FakeTaxLotStateFactory,
    FakeTaxLotViewFactory,
)
from seed.tests.util import AccessLevelBaseTestCase, DataMappingBaseTestCase
from seed.utils.organizations import create_organization


class TestTaxLotProperty(DataMappingBaseTestCase):
    """Tests for exporting data to various formats."""

    def setUp(self):
        self.properties = []
        self.maxDiff = None
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        self.user = User.objects.create_superuser(email="test_user@demo.com", **user_details)
        self.org, _, _ = create_organization(self.user)
        # create a default cycle
        self.cycle = Cycle.objects.filter(organization_id=self.org).first()
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org, user=self.user)
        self.taxlot_view_factory = FakeTaxLotViewFactory(organization=self.org, user=self.user)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)
        self.taxlot_property_factory = FakeTaxLotPropertyFactory(organization=self.org, user=self.user)
        self.label_factory = FakeStatusLabelFactory(organization=self.org)
        self.property_view = self.property_view_factory.get_property_view()
        self.urls = ["http://example.com", "http://example.org"]
        self.client.login(**user_details)

        self.derived_col_factory = FakeDerivedColumnFactory(organization=self.org, inventory_type=DerivedColumn.PROPERTY_TYPE)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)

    def test_tax_lot_property_get_related(self):
        """Test to make sure get_related returns the fields"""
        for i in range(50):
            p = self.property_view_factory.get_property_view()
            self.properties.append(p.id)

        qs_filter = {"pk__in": self.properties}
        qs = PropertyView.objects.filter(**qs_filter)

        columns = [
            "address_line_1",
            "generation_date",
            "energy_alerts",
            "space_alerts",
            "building_count",
            "owner",
            "source_eui",
            "jurisdiction_tax_lot_id",
            "city",
            "district",
            "site_eui",
            "building_certification",
            "modified",
            "match_type",
            "source_eui_weather_normalized",
            "id",
            "property_name",
            "conditioned_floor_area",
            "pm_property_id",
            "use_description",
            "source_type",
            "year_built",
            "release_date",
            "gross_floor_area",
            "owner_city_state",
            "owner_telephone",
            "recent_sale_date",
        ]
        columns_from_database = Column.retrieve_all(self.org.id, "property", False)
        data = TaxLotProperty.serialize(qs, columns, columns_from_database)

        self.assertEqual(len(data), 50)
        self.assertEqual(len(data[0]["related"]), 0)

    def test_taxlot_property_returns_derived_data(self):
        derived_column = self.derived_col_factory.get_derived_column(expression="$gross_floor_area + 1", name="my_derived_column")
        column = Column.objects.get(derived_column=derived_column)

        property_view = self.property_view_factory.get_property_view()
        columns_from_database = Column.retrieve_all(self.org.id, "property", False)

        # -- Action
        data = TaxLotProperty.serialize([property_view], [column.id], columns_from_database)

        # -- Assertion
        assert "my_derived_column_" + str(column.id) in data[0]

    def test_csv_export(self):
        """Test to make sure get_related returns the fields"""
        for i in range(50):
            p = self.property_view_factory.get_property_view()
            self.properties.append(p.id)

        columns = []
        for c in Column.retrieve_all(self.org.id, "property", False):
            columns.append(c["name"])

        # call the API
        url = reverse_lazy("api:v3:tax_lot_properties-export")
        response = self.client.post(
            f"{url}?organization_id={self.org.pk}&inventory_type=properties",
            data=json.dumps({"columns": columns, "export_type": "csv"}),
            content_type="application/json",
        )

        # parse the content as array
        data = json.loads(response.content.decode("utf-8"))["message"].split("\n")

        self.assertTrue("Address Line 1" in data[0].split(","))
        self.assertTrue("Property Labels\r" in data[0].split(","))

        self.assertEqual(len(data), 53)
        # last row should be blank
        self.assertEqual(data[52], "")

    def test_paired_export(self):
        """Ensure paired inventory is exported correctly"""
        col_names = ["address_line_1", "jurisdiction_tax_lot_id", "pm_property_id", "id"]

        p_details = [
            {"pm_property_id": 1, "address_line_1": "1 Main St"},
            {"pm_property_id": 2, "address_line_1": "2 Main St"},
            {"pm_property_id": 3, "address_line_1": "3 Main St"},
        ]
        t_details = [
            {"jurisdiction_tax_lot_id": "111", "address_line_1": "111 Main St"},
            {"jurisdiction_tax_lot_id": "222", "address_line_1": "222 Main St"},
            {"jurisdiction_tax_lot_id": "333", "address_line_1": "333 Main St"},
        ]
        pss = [self.property_state_factory.get_property_state(**details) for details in p_details]
        tss = [self.taxlot_state_factory.get_taxlot_state(**details) for details in t_details]

        pvs = [self.property_view_factory.get_property_view(state=ps) for ps in pss]
        tvs = [self.taxlot_view_factory.get_taxlot_view(state=ts) for ts in tss]

        # all properties are paired with the first taxlot
        # all taxlots are paired with the first property
        self.taxlot_property_factory.get_taxlot_property(property_view=pvs[0], taxlot_view=tvs[0])
        self.taxlot_property_factory.get_taxlot_property(property_view=pvs[0], taxlot_view=tvs[1])
        self.taxlot_property_factory.get_taxlot_property(property_view=pvs[0], taxlot_view=tvs[2])
        self.taxlot_property_factory.get_taxlot_property(property_view=pvs[1], taxlot_view=tvs[0])
        self.taxlot_property_factory.get_taxlot_property(property_view=pvs[2], taxlot_view=tvs[0])

        pv_ids = [pv.id for pv in pvs]
        tv_ids = [tv.id for tv in tvs]

        # Property export
        url = reverse_lazy("api:v3:tax_lot_properties-export") + f"?organization_id={self.org.id!s}&inventory_type=properties"
        data = json.dumps({"columns": col_names, "export_type": "csv", "ids": pv_ids})
        response = self.client.post(url, data=data, content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))["message"].split("\n")
        headers = data[0].split(",")
        idx_adr = headers.index("Address Line 1 (Tax Lot)")
        idx_jtl = headers.index("Jurisdiction Tax Lot ID (Tax Lot)")
        row1 = data[1].split(",")
        exp_address_set = {"111 Main St", "222 Main St", "333 Main St"}
        exp_id_set = {"111", "222", "333"}
        self.assertEqual(set(row1[idx_adr].split("; ")), exp_address_set)
        self.assertEqual(set(row1[idx_jtl].split("; ")), exp_id_set)

        # Taxlot export
        url = reverse_lazy("api:v3:tax_lot_properties-export") + f"?organization_id={self.org.id!s}&inventory_type=taxlots"
        data = json.dumps({"columns": col_names, "export_type": "csv", "ids": tv_ids})
        response = self.client.post(url, data=data, content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))["message"].split("\n")
        headers = data[0].split(",")
        idx_adr = headers.index("Address Line 1 (Property)")
        row1 = data[1].split(",")
        exp_address_set = {"1 Main St", "2 Main St", "3 Main St"}
        self.assertEqual(set(row1[idx_adr].split("; ")), exp_address_set)

    def test_csv_export_with_notes(self):
        multi_line_note = self.property_view.notes.create(name="Manually Created", note_type=Note.NOTE, text="multi\nline\nnote")
        single_line_note = self.property_view.notes.create(name="Manually Created", note_type=Note.NOTE, text="single line")

        self.properties.append(self.property_view.id)

        columns = []
        for c in Column.retrieve_all(self.org.id, "property", False):
            columns.append(c["name"])

        # call the API
        url = reverse_lazy("api:v3:tax_lot_properties-export")
        response = self.client.post(
            f"{url}?organization_id={self.org.pk}&inventory_type=properties",
            data=json.dumps({"columns": columns, "export_type": "csv"}),
            content_type="application/json",
        )

        # parse the content as array
        data = json.loads(response.content.decode("utf-8"))["message"].split("\r\n")
        notes_string = (
            multi_line_note.created.astimezone().strftime("%Y-%m-%d %I:%M:%S %p")
            + "\n"
            + multi_line_note.text
            + "\n----------\n"
            + single_line_note.created.astimezone().strftime("%Y-%m-%d %I:%M:%S %p")
            + "\n"
            + single_line_note.text
        )

        self.assertEqual(len(data), 3)
        self.assertTrue("Property Notes" in data[0].split(","))

        self.assertTrue(notes_string in data[1])

    def test_xlsx_export(self):
        for i in range(50):
            p = self.property_view_factory.get_property_view()
            self.properties.append(p.id)

        columns = []
        for c in Column.retrieve_all(self.org.id, "property", False):
            columns.append(c["name"])

        # call the API
        url = reverse_lazy("api:v3:tax_lot_properties-export")
        response = self.client.post(
            f"{url}?organization_id={self.org.pk}&inventory_type=properties",
            data=json.dumps({"columns": columns, "export_type": "xlsx"}),
            content_type="application/json",
        )

        # parse & decode the content as array
        file_contents = json.loads(response.content)["message"]
        xlsx_bytes = base64.b64decode(file_contents)
        wb = open_workbook(file_contents=xlsx_bytes)

        data = [row.value for row in wb.sheet_by_index(0).row(0)]

        self.assertTrue("Address Line 1" in data)
        self.assertTrue("Property Labels" in data)

        self.assertEqual(len(list(wb.sheet_by_index(0).get_rows())), 52)

    def test_json_export(self):
        """Test to make sure get_related returns the fields"""
        for i in range(50):
            p = self.property_view_factory.get_property_view()
            self.properties.append(p.id)

        columns = []
        for c in Column.retrieve_all(self.org.id, "property", False):
            columns.append(c["name"])

        # call the API
        url = reverse_lazy("api:v3:tax_lot_properties-export")
        response = self.client.post(
            f"{url}?organization_id={self.org.pk}&inventory_type=properties",
            data=json.dumps({"columns": columns, "export_type": "geojson"}),
            content_type="application/json",
        )

        # parse the content as dictionary
        progress_data = json.loads(response.content)
        features = progress_data["message"]
        record_level_keys = list(features[0]["properties"].keys())

        self.assertIn("Address Line 1", record_level_keys)
        self.assertIn("Gross Floor Area", record_level_keys)

        # ids 52 up to and including 102
        self.assertEqual(len(features), 51)

    def test_set_update_to_now(self):
        property_view_ids = [self.property_view_factory.get_property_view().id for _ in range(50)]
        taxlot_view_ids = [self.taxlot_view_factory.get_taxlot_view().id for _ in range(50)]
        before_refresh = datetime.now(pytz.UTC)

        time.sleep(1)

        progress_data = ProgressData(func_name="set_update_to_now", unique_id=f"metadata{randint(10000, 99999)}")
        set_update_to_now(property_view_ids, taxlot_view_ids, progress_data.key)

        for pv in PropertyView.objects.filter(id__in=property_view_ids):
            self.assertGreater(pv.state.updated, before_refresh)
            self.assertGreater(pv.property.updated, before_refresh)

        for tv in TaxLotView.objects.filter(id__in=taxlot_view_ids):
            self.assertGreater(tv.state.updated, before_refresh)
            self.assertGreater(tv.taxlot.updated, before_refresh)

    def test_extra_data_unit_conversion(self):
        def create_column(column_name):
            Column.objects.create(
                is_extra_data=True,
                column_name=column_name,
                organization=self.org,
                table_name="PropertyState",
                data_type="area",
            )

        column_names = ["area_int", "area_float", "area_bool", "area_none", "area_str", "area_str_int", "area_str_float"]
        mapping = {}
        units = {}
        for column_name in column_names:
            create_column(column_name)
            mapping[column_name] = column_name
            units[column_name] = DEFAULT_UNITS["area"]

        state = self.property_view.state
        state.extra_data["area_int"] = 123
        state.extra_data["area_float"] = 12.3
        state.extra_data["area_bool"] = True
        state.extra_data["area_none"] = None
        state.extra_data["area_str"] = "string"
        state.extra_data["area_str_int"] = "123"
        state.extra_data["area_str_float"] = "12.3"
        state.save()

        obj_dict = TaxLotProperty.extra_data_to_dict_with_mapping(state.extra_data, mapping, fields=list(mapping.keys()), units=units)
        self.assertEqual(obj_dict["area_int"].m, 123)
        self.assertEqual(str(obj_dict["area_int"].u), "foot ** 2")
        self.assertEqual(obj_dict["area_float"].m, 12.3)
        self.assertEqual(str(obj_dict["area_float"].u), "foot ** 2")
        self.assertEqual(obj_dict["area_bool"], True)
        self.assertIsNone(obj_dict["area_none"])
        self.assertEqual(obj_dict["area_str"], "string")
        self.assertEqual(obj_dict["area_str_int"].m, 123)
        self.assertEqual(str(obj_dict["area_str_int"].u), "foot ** 2")
        self.assertEqual(obj_dict["area_str_float"].m, 12.3)
        self.assertEqual(str(obj_dict["area_str_float"].u), "foot ** 2")

    def tearDown(self):
        for x in self.properties:
            PropertyView.objects.get(pk=x).delete()


class TestTaxLotPropertyAccessLevel(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.cycle = self.cycle_factory.get_cycle()

        self.root_property = self.property_factory.get_property(access_level_instance=self.root_level_instance)
        self.root_property_view = self.property_view_factory.get_property_view(prprty=self.root_property)

        self.root_taxlot = self.taxlot_factory.get_taxlot(access_level_instance=self.root_level_instance)
        self.root_taxlot_view = self.taxlot_view_factory.get_taxlot_view(taxlot=self.root_taxlot)

        TaxLotProperty(
            primary=True, cycle_id=self.cycle.id, property_view_id=self.root_property_view.id, taxlot_view_id=self.root_taxlot_view.id
        ).save()

        self.columns = [Column.objects.get(organization=self.org, table_name="PropertyState", column_name="address_line_1").column_name]

    def test_tax_lot_and_property_in_different_ali(self):
        child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)
        child_property_view = self.property_view_factory.get_property_view(prprty=child_property)

        with pytest.raises(ValidationError):
            TaxLotProperty(
                primary=True, cycle_id=self.cycle.id, property_view_id=child_property_view.id, taxlot_view_id=self.root_taxlot_view.id
            ).save()

    def test_change_properties_ali(self):
        with pytest.raises(ValidationError):  # noqa: PT012
            self.root_property.access_level_instance = self.child_level_instance
            self.root_property.save()

    def test_change_tax_lot_ali(self):
        with pytest.raises(ValidationError):  # noqa: PT012
            self.root_taxlot.access_level_instance = self.child_level_instance
            self.root_taxlot.save()

    def test_property_export(self):
        url = reverse_lazy("api:v3:tax_lot_properties-export")
        url += f"?organization_id={self.org.pk}&inventory_type=properties"
        params = json.dumps({"columns": self.columns, "export_type": "csv"})

        self.login_as_root_member()
        response = self.client.post(url, data=params, content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))["message"].split("\n")
        assert len(data) == 3

        self.login_as_child_member()
        response = self.client.post(url, data=params, content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))["message"].split("\n")
        assert len(data) == 2

    def test_taxlot_export(self):
        url = reverse_lazy("api:v3:tax_lot_properties-export")
        url += f"?organization_id={self.org.pk}&inventory_type=taxlots"
        params = json.dumps({"columns": self.columns, "export_type": "csv"})

        self.login_as_root_member()
        response = self.client.post(url, data=params, content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))["message"].split("\n")
        assert len(data) == 3

        self.login_as_child_member()
        response = self.client.post(url, data=params, content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))["message"].split("\n")
        assert len(data) == 2

    def test_set_update_to_now(self):
        start_of_test = datetime.now(pytz.UTC)
        time.sleep(1)

        progress_data = ProgressData(func_name="set_update_to_now", unique_id=f"metadata{randint(10000, 99999)}")
        url = reverse_lazy("api:v3:tax_lot_properties-set-update-to-now")
        url += f"?organization_id={self.org.pk}"
        params = json.dumps(
            {"property_views": [self.root_property_view.pk], "taxlot_views": [self.root_taxlot_view.pk], "progress_key": progress_data.key}
        )

        self.login_as_child_member()
        self.client.post(url, data=params, content_type="application/json")
        assert PropertyView.objects.get(pk=self.root_property_view.pk).state.updated < start_of_test
        assert PropertyView.objects.get(pk=self.root_property_view.pk).property.updated < start_of_test
        assert TaxLotView.objects.get(pk=self.root_taxlot_view.pk).taxlot.updated < start_of_test
        assert TaxLotView.objects.get(pk=self.root_taxlot_view.pk).state.updated < start_of_test

        self.login_as_root_member()
        self.client.post(url, data=params, content_type="application/json")
        assert PropertyView.objects.get(pk=self.root_property_view.pk).state.updated > start_of_test
        assert PropertyView.objects.get(pk=self.root_property_view.pk).property.updated > start_of_test
        assert TaxLotView.objects.get(pk=self.root_taxlot_view.pk).taxlot.updated > start_of_test
        assert TaxLotView.objects.get(pk=self.root_taxlot_view.pk).state.updated > start_of_test

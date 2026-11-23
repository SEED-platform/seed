"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
import math
import random
from datetime import UTC, date, datetime
from urllib.parse import urlencode

from django.db.models import Value
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import (
    get_current_timezone,
)
from quantityfield.units import ureg

from seed.data_importer.tasks import geocode_and_match_buildings_task
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    DATA_STATE_MAPPING,
    VIEW_DETAIL,
    VIEW_LIST_TAXLOT,
    Column,
    ColumnMappingProfile,
    DerivedColumn,
    Property,
    PropertyState,
    PropertyView,
    StatusLabel,
    TaxLot,
    TaxLotProperty,
    TaxLotState,
    TaxLotView,
)
from seed.serializers.columns import ColumnSerializer
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeColumnListProfileFactory,
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeTaxLotFactory,
    FakeTaxLotPropertyFactory,
    FakeTaxLotStateFactory,
    FakeTaxLotViewFactory,
)
from seed.tests.util import AccessLevelBaseTestCase, DataMappingBaseTestCase
from seed.utils.organizations import create_organization
from seed.utils.v4.inventory_filter import round_half_even

# from seed.utils.v4.inventory_filter import generate_Q_filters


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


class TaxLotPropertyViewTests(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.taxlot_view_factory = FakeTaxLotViewFactory(organization=self.org)
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.column_list_factory = FakeColumnListProfileFactory(organization=self.org)
        self.client.login(**user_details)

        # create tree
        self.org.access_level_names = ["1st Gen", "2nd Gen", "3rd Gen"]
        mom_ali = self.org.add_new_access_level_instance(self.org.root.id, "mom")
        self.me_ali = self.org.add_new_access_level_instance(mom_ali.id, "me")
        self.sister_ali = self.org.add_new_access_level_instance(mom_ali.id, "sister")
        self.org.save()

        _, import_file_1 = self.create_import_file(self.user, self.org, self.cycle)
        self.base_details = {
            "custom_id_1": "CustomID123",
            "import_file_id": import_file_1.id,
            "data_state": DATA_STATE_MAPPING,
            "no_default_data": False,
            "raw_access_level_instance_id": self.org.root.id,
        }
        self.property_state_factory.get_property_state(**self.base_details)

        # set import_file_1 mapping done so that record is "created for users to view".
        import_file_1.mapping_done = True
        import_file_1.save()
        geocode_and_match_buildings_task(import_file_1.id)

    def test_inventory_filter(self):
        url = (
            reverse("api:v4:tax_lot_properties-filter")
            + f"?inventory_type=property&cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        )
        response = self.client.post(url, content_type="application/json")
        data = json.loads(response.content)
        self.assertEqual(list(data.keys()), ["pagination", "cycle_id", "results", "column_defs"])
        pagination = data["pagination"]
        results = data["results"]
        column_defs = data["column_defs"]

        self.assertEqual(pagination["total"], 1)
        self.assertEqual(len(results), 1)
        # with the server's filter types (the grid doesn't filter), and other inventory columns aren't sortable
        self.assertEqual(list(column_defs[0].keys()), ["field", "headerName", "context"])
        self.assertEqual(list(column_defs[-1].keys()), ["field", "headerName", "sortable", "context"])
        self.assertIn(column_defs[0]["context"]["filterType"], {"text", "number", "date", "boolean"})

    def test_inventory_filter_column_defs_use_only_organization_profiles(self):
        url = (
            reverse("api:v4:tax_lot_properties-filter")
            + f"?inventory_type=property&cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        )

        def column_headers(profile_id=None, query_profile_id=None):
            data = {} if profile_id is None else {"profile_id": profile_id}
            query = "" if query_profile_id is None else f"&profile_id={query_profile_id}"
            response = self.client.post(url + query, data=data, content_type="application/json")
            self.assertEqual(response.status_code, 200)
            # the column queries are unordered
            return sorted(c["headerName"] for c in response.json()["column_defs"])

        all_column_headers = column_headers()

        # the organization's list profile limits the columns, in the body or the query string
        profile = self.column_list_factory.get_columnlistprofile(columns=["address_line_1", "city"])
        self.assertEqual(column_headers(profile.id), ["Address Line 1", "City"])
        self.assertEqual(column_headers(query_profile_id=profile.id), ["Address Line 1", "City"])

        # the shown columns only use list profiles of the inventory type, so the column definitions don't use other profiles
        detail_profile = self.column_list_factory.get_columnlistprofile(location=VIEW_DETAIL, columns=["address_line_1"])
        taxlot_profile = self.column_list_factory.get_columnlistprofile(
            inventory_type=VIEW_LIST_TAXLOT, table_name="TaxLotState", columns=["jurisdiction_tax_lot_id"]
        )

        # another organization's profile, a missing profile, other profiles, and -1 (all columns) fall back to all columns
        other_org, _, _ = create_organization(self.user, "other org")
        other_profile = self.column_list_factory.get_columnlistprofile(organization=other_org, columns=["address_line_1"])
        for profile_id in (other_profile.id, other_profile.id + 1000, detail_profile.id, taxlot_profile.id, -1):
            self.assertEqual(column_headers(profile_id), all_column_headers)
        self.assertEqual(column_headers(query_profile_id=-1), all_column_headers)

        # a query string profile_id must be an integer
        response = self.client.post(url + "&profile_id=abc", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "profile_id must be an integer")

    def test_merged_indicators_provided_on_filter_endpoint(self):
        url = (
            reverse("api:v4:tax_lot_properties-filter")
            + f"?inventory_type=property&cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        )
        response = self.client.post(url, content_type="application/json")
        data = json.loads(response.content)
        self.assertFalse(data["results"][0]["merged_indicator"])

        _, import_file_2 = self.create_import_file(self.user, self.org, self.cycle)

        url = (
            reverse("api:v4:tax_lot_properties-filter")
            + f"?inventory_type=property&cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        )
        response = self.client.post(url, content_type="application/json")
        data = json.loads(response.content)

        self.assertFalse(data["results"][0]["merged_indicator"])

        # make sure merged_indicator is True when merge occurs
        self.base_details["city"] = "Denver"
        self.base_details["import_file_id"] = import_file_2.id
        self.property_state_factory.get_property_state(**self.base_details)

        # set import_file_2 mapping done so that match merging can occur.
        import_file_2.mapping_done = True
        import_file_2.save()
        geocode_and_match_buildings_task(import_file_2.id)

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

        url = (
            reverse("api:v4:tax_lot_properties-filter")
            + f"?inventory_type=property&cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        )
        response = self.client.post(url, content_type="application/json")
        data = json.loads(response.content)
        self.assertTrue(data["results"][0]["merged_indicator"])

        url = (
            reverse("api:v4:tax_lot_properties-filter")
            + f"?inventory_type=property&cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        )
        response = self.client.post(url, content_type="application/json")
        data = json.loads(response.content)
        related = data["results"][0]["related"][0]
        self.assertTrue("merged_indicator" in related)
        self.assertFalse(related["merged_indicator"])

    def test_record_count(self):
        cycle2 = self.cycle_factory.get_cycle()
        # create 100 properties for each cycle, 50 taxlots in first cycle
        for i in range(100):
            self.property_view_factory.get_property_view(cycle=self.cycle)
            self.property_view_factory.get_property_view(cycle=cycle2)
            if i < 50:
                self.taxlot_view_factory.get_taxlot_view(cycle=self.cycle)

        url = (
            reverse("api:v4:tax_lot_properties-record-count")
            + f"?organization_id={self.org.pk}&cycle_id={self.cycle.pk}&inventory_type=properties"
        )
        response = self.client.get(url)
        data = json.loads(response.content)
        self.assertEqual(data["data"], 101)

        url = (
            reverse("api:v4:tax_lot_properties-record-count")
            + f"?organization_id={self.org.pk}&cycle_id={self.cycle.pk}&inventory_type=taxlots"
        )
        response = self.client.get(url)
        data = json.loads(response.content)
        self.assertEqual(data["data"], 50)


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

    def test_property_filter(self):
        url = (
            reverse("api:v4:tax_lot_properties-filter") + f"?inventory_type=property&cycle_id={self.cycle.pk}&organization_id={self.org.pk}"
        )

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["pagination"]["total"], 1)

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["pagination"]["total"], 0)

    def test_property_filter_invalid_cycle(self):
        other_org, _, _ = create_organization(self.superuser, "other org")
        other_cycle = FakeCycleFactory(organization=other_org, user=self.superuser).get_cycle()
        self.login_as_root_member()

        for cycle_id in [other_cycle.pk, "abc"]:
            url = reverse("api:v4:tax_lot_properties-filter") + f"?inventory_type=property&cycle={cycle_id}&organization_id={self.org.pk}"
            resp = self.client.post(url, content_type="application/json")
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp.json(), {"status": "error", "message": "No such cycle."})

    def test_record_count(self):
        child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)
        self.property_view_factory.get_property_view(prprty=child_property, cycle=self.cycle)
        child_taxlot = self.taxlot_factory.get_taxlot(access_level_instance=self.child_level_instance)
        self.taxlot_view_factory.get_taxlot_view(taxlot=child_taxlot, cycle=self.cycle)

        def record_count(inventory_type):
            url = (
                reverse("api:v4:tax_lot_properties-record-count")
                + "?"
                + urlencode({"organization_id": self.org.pk, "cycle_id": self.cycle.pk, "inventory_type": inventory_type})
            )
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            return resp.json()["data"]

        # root member counts every record
        self.login_as_root_member()
        self.assertEqual(record_count("properties"), 2)
        self.assertEqual(record_count("taxlots"), 2)

        # child member only counts the records in its subtree
        self.login_as_child_member()
        self.assertEqual(record_count("properties"), 1)
        self.assertEqual(record_count("taxlots"), 1)


class FilterTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.root_owner_user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

        # cycles
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2001, 1, 1), end=datetime(2002, 1, 1))
        # columns with column name as formatted by frontend: {column_name}_{column_id}
        Column.objects.create(table_name="PropertyState", column_name="extra_eui", organization=self.org, is_extra_data=True)

        def get_column_name(column_name):
            return ColumnSerializer(Column.objects.filter(column_name=column_name).first()).data["name"]

        self.al1_name = get_column_name("address_line_1")
        self.cid1_name = get_column_name("custom_id_1")
        self.pmpid_name = get_column_name("pm_property_id")
        self.gfa_name = get_column_name("gross_floor_area")
        self.extra_eui_name = get_column_name("extra_eui")

        columns = Column.objects.filter(organization=self.org)
        self.extra_data_column_names = list(columns.filter(is_extra_data=True).values_list("column_name", flat=True))

        other_columns = columns.filter(table_name="TaxLotState").values("column_name", "id")
        self.other_column_names_with_id = [f"{c['column_name']}_{c['id']}" for c in other_columns]

        # create a 100 properties
        def get_property_details(i):
            return {
                "address_line_1": f"address{i}" if i % 2 != 0 else "",  # evens blank
                "custom_id_1": f"custom_id{i}" if i % 5 != 0 else None,  # 5s and 10s None
                "gross_floor_area": 1000 + i,
                "pm_property_id": f"pm-{i}",
                "extra_data": {"extra_eui": 100 + i},
            }

        for i in range(100):
            self.property_view_factory.get_property_view(cycle=self.cycle, **get_property_details(i))

        # shortcuts
        self.query_string = {
            "cycle": self.cycle.id,
            "ids_only": False,
            "inventory_type": "property",
            "include_related": False,
            "organization_id": self.org.id,
            "page": 1,
            "per_page": 100,
        }

    def get_filter(self, filter_type, filter_val=None):
        # As AG Grid sends them: comparisons from number filters, and the rest from text filters
        kind = "number" if filter_type in {"greaterThan", "greaterThanOrEqual", "lessThan", "lessThanOrEqual", "inRange"} else "text"
        filter_dict = {"filterType": kind, "type": filter_type}
        if filter_val:
            filter_dict["filter"] = filter_val
        return filter_dict

    def get_request_results(self, filters, sorts=None):
        data = {"filters": filters, "sorts": sorts}
        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(self.query_string)
        response = self.client.post(url, data=data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        return data["results"]

    def test_contains(self):
        contains = {self.pmpid_name: self.get_filter("contains", "0")}
        not_contain = {self.pmpid_name: self.get_filter("notContains", "0")}
        contains_2x = {self.pmpid_name: self.get_filter("contains", "1"), self.gfa_name: self.get_filter("contains", 2)}
        c_or_nc = {
            self.pmpid_name: {
                "filterType": "text",
                "operator": "OR",
                "conditions": [self.get_filter("contains", "10"), self.get_filter("notContains", "1")],
            }
        }
        c_and_nc = {
            self.pmpid_name: {
                "filterType": "text",
                "operator": "AND",
                "conditions": [self.get_filter("contains", "1"), self.get_filter("notContains", "2")],
            }
        }

        self.assertEqual(len(self.get_request_results(contains)), 10)  # 10s
        self.assertEqual(len(self.get_request_results(not_contain)), 90)  # not 10s
        self.assertEqual(len(self.get_request_results(contains_2x)), 2)  # 12 and 21
        self.assertEqual(len(self.get_request_results(c_or_nc)), 82)  # not 1, 11-19, 21, 31, ...91
        self.assertEqual(len(self.get_request_results(c_and_nc)), 17)  # 1, 10, 11, 13, ...21, 31, ...91

    def test_equals(self):
        equal = {self.pmpid_name: self.get_filter("equals", "pm-1")}
        not_equal = {self.pmpid_name: self.get_filter("notEqual", "pm-1")}
        equal_2x = {self.pmpid_name: self.get_filter("equals", "pm-1"), self.gfa_name: self.get_filter("equals", 1002)}

        self.assertEqual(len(self.get_request_results(equal)), 1)
        self.assertEqual(len(self.get_request_results(not_equal)), 99)
        self.assertEqual(len(self.get_request_results(equal_2x)), 0)

    def test_starts_with(self):
        starts = {self.pmpid_name: self.get_filter("startsWith", "pm-1")}
        ends = {self.pmpid_name: self.get_filter("endsWith", "1")}
        starts_or_ends = {
            self.pmpid_name: {
                "filterType": "text",
                "operator": "OR",
                "conditions": [self.get_filter("startsWith", "pm-1"), self.get_filter("endsWith", "2")],
            }
        }
        starts_and_ends = {
            self.pmpid_name: {
                "filterType": "text",
                "operator": "AND",
                "conditions": [self.get_filter("startsWith", "pm-1"), self.get_filter("endsWith", "2")],
            }
        }

        self.assertEqual(len(self.get_request_results(starts)), 11)  # 1, 10-19
        self.assertEqual(len(self.get_request_results(ends)), 10)  # 1, 11, 21, ...91
        self.assertEqual(len(self.get_request_results(starts_or_ends)), 20)  # 1-11 and 12, 22, 32, ...92
        self.assertEqual(len(self.get_request_results(starts_and_ends)), 1)  # 12

    def test_blank(self):
        blank_str = {self.al1_name: self.get_filter("blank")}
        blank_null = {self.cid1_name: self.get_filter("blank")}
        not_blank_str = {self.al1_name: self.get_filter("notBlank")}
        not_blank_null = {self.cid1_name: self.get_filter("notBlank")}
        blank_and_blank = {self.cid1_name: self.get_filter("blank"), self.al1_name: self.get_filter("blank")}

        self.assertEqual(len(self.get_request_results(blank_str)), 50)  # evens
        self.assertEqual(len(self.get_request_results(blank_null)), 20)  # 5s & 10s
        self.assertEqual(len(self.get_request_results(not_blank_str)), 50)  # odds
        self.assertEqual(len(self.get_request_results(not_blank_null)), 80)  # not 5s or 10s
        self.assertEqual(len(self.get_request_results(blank_and_blank)), 10)  # 10s

    def test_range(self):
        # >, >=, <, <=, between
        gt = {self.gfa_name: self.get_filter("greaterThan", 1010)}
        gte = {self.gfa_name: self.get_filter("greaterThanOrEqual", 1010)}
        lt = {self.gfa_name: self.get_filter("lessThan", 1010)}
        lte = {self.gfa_name: self.get_filter("lessThanOrEqual", 1010)}
        between = {self.gfa_name: {"filter": 1010, "filterTo": 1020, "filterType": "number", "type": "inRange"}}

        self.assertEqual(len(self.get_request_results(gt)), 89)  # 11-99
        self.assertEqual(len(self.get_request_results(gte)), 90)  # 10-99
        self.assertEqual(len(self.get_request_results(lt)), 10)  # 0-9
        self.assertEqual(len(self.get_request_results(lte)), 11)  # 0-10
        self.assertEqual(len(self.get_request_results(between)), 9)  # 11-19

    def test_extra_data(self):
        gt = {self.extra_eui_name: self.get_filter("greaterThan", 120)}
        lt = {self.extra_eui_name: self.get_filter("lessThan", 120)}

        self.assertEqual(len(self.get_request_results(gt)), 79)  # 21-99
        self.assertEqual(len(self.get_request_results(lt)), 20)  # 0-19

    def test_derived_column(self):
        derived_column = DerivedColumn.objects.create(
            name="Energy Use Intensity (kBtu/ft²)", expression="$a / 2", organization=self.org, inventory_type=DerivedColumn.PROPERTY_TYPE
        )
        derived_name = ColumnSerializer(derived_column.column).data["name"]

        # 0, 4, 8, ... can't be computed (null), 1, 5, 9, ... are missing, and the rest have values
        def get_value(i):
            return 50 + i if i % 4 > 1 else None

        states = list(PropertyState.objects.filter(propertyview__cycle=self.cycle))
        for state in states:
            i = int(state.pm_property_id.removeprefix("pm-"))
            if i % 4 != 1:
                state.derived_data = {derived_column.name: get_value(i)}
        PropertyState.objects.bulk_update(states, ["derived_data"])

        blank = {derived_name: self.get_filter("blank")}
        not_blank = {derived_name: self.get_filter("notBlank")}
        number_blank = {derived_name: {"filterType": "number", "type": "blank"}}
        number_not_blank = {derived_name: {"filterType": "number", "type": "notBlank"}}
        gt = {derived_name: self.get_filter("greaterThan", 100)}

        self.assertEqual(len(self.get_request_results(blank)), 50)
        self.assertEqual(len(self.get_request_results(not_blank)), 50)
        self.assertEqual(len(self.get_request_results(number_blank)), 50)
        self.assertEqual(len(self.get_request_results(number_not_blank)), 50)
        self.assertEqual(len(self.get_request_results(gt)), 25)  # 51-99

        def get_sorted_values(sort):
            results = self.get_request_results(None, [sort])
            values = [get_value(int(r[self.pmpid_name].removeprefix("pm-"))) for r in results]
            return [v for v in values if v is not None]

        self.assertEqual(get_sorted_values(derived_name), sorted(get_value(i) for i in range(100) if i % 4 > 1))
        self.assertEqual(get_sorted_values(f"-{derived_name}"), sorted((get_value(i) for i in range(100) if i % 4 > 1), reverse=True))

    def get_name(self, column_name):
        column = Column.objects.get(organization=self.org, table_name="PropertyState", column_name=column_name)
        return ColumnSerializer(column).data["name"]

    def test_blank_on_number_and_date_columns(self):
        site_eui_name = self.get_name("site_eui")
        year_ending_name = self.get_name("year_ending")
        states = PropertyState.objects.filter(propertyview__cycle=self.cycle)
        states.filter(pm_property_id__in=[f"pm-{i}" for i in range(0, 100, 2)]).update(site_eui=None)  # evens
        states.filter(pm_property_id__in=[f"pm-{i}" for i in range(0, 100, 4)]).update(year_ending=date(2020, 12, 31))  # 4s

        # Blank is null (or empty text) for any filter type, e.g., in filters saved before the server chose the types
        for filter_type in ["text", "number"]:
            blank = {site_eui_name: {"filterType": filter_type, "type": "blank"}}
            not_blank = {site_eui_name: {"filterType": filter_type, "type": "notBlank"}}
            self.assertEqual(len(self.get_request_results(blank)), 50)
            self.assertEqual(len(self.get_request_results(not_blank)), 50)

        # Number filters exclude blanks from notEqual, and text filters include them
        number_not_equal = {site_eui_name: {"filterType": "number", "type": "notEqual", "filter": -1}}
        text_not_equal = {site_eui_name: self.get_filter("notEqual", "-1")}
        self.assertEqual(len(self.get_request_results(number_not_equal)), 50)
        self.assertEqual(len(self.get_request_results(text_not_equal)), 100)

        blank_or_not = {
            site_eui_name: {"filterType": "text", "operator": "OR", "conditions": [self.get_filter("blank"), self.get_filter("notBlank")]}
        }
        self.assertEqual(len(self.get_request_results(blank_or_not)), 100)

        date_blank = {year_ending_name: {"filterType": "date", "type": "blank"}}
        date_not_blank = {year_ending_name: {"filterType": "date", "type": "notBlank"}}
        self.assertEqual(len(self.get_request_results(date_blank)), 75)
        self.assertEqual(len(self.get_request_results(date_not_blank)), 25)

        # Text filters on other columns compare their values as text
        self.assertEqual(len(self.get_request_results({site_eui_name: self.get_filter("equals", "abc")})), 0)

    def test_text_filters(self):
        Column.objects.create(table_name="PropertyState", column_name="Parcel", organization=self.org, is_extra_data=True)
        parcel_name = self.get_name("Parcel")
        states = list(PropertyState.objects.filter(propertyview__cycle=self.cycle))
        for state in states:
            # JSON numbers, the same as text, other text, and missing
            i = int(state.pm_property_id.removeprefix("pm-"))
            if i < 30:
                state.extra_data = {**state.extra_data, "Parcel": [100, "100", "ABC-1"][i // 10]}
        PropertyState.objects.bulk_update(states, ["extra_data"])

        # Case-insensitively
        self.assertEqual(len(self.get_request_results({self.pmpid_name: self.get_filter("equals", "PM-1")})), 1)
        self.assertEqual(len(self.get_request_results({self.pmpid_name: self.get_filter("notEqual", "PM-1")})), 99)
        self.assertEqual(len(self.get_request_results({parcel_name: self.get_filter("equals", "abc-1")})), 10)
        self.assertEqual(len(self.get_request_results({parcel_name: self.get_filter("startsWith", "Abc")})), 10)
        # On the text of JSON values, and negated conditions include blanks
        self.assertEqual(len(self.get_request_results({parcel_name: self.get_filter("equals", "100")})), 20)
        self.assertEqual(len(self.get_request_results({parcel_name: self.get_filter("notEqual", "100")})), 80)
        self.assertEqual(len(self.get_request_results({parcel_name: self.get_filter("notContains", "abc")})), 90)

    def test_number_filters_on_text_and_json_values(self):
        Column.objects.create(
            table_name="PropertyState", column_name="Floor Count", organization=self.org, is_extra_data=True, data_type="number"
        )
        name = self.get_name("Floor Count")
        values = [5, "12", "1,234", "n/a", None, True]
        states = list(PropertyState.objects.filter(propertyview__cycle=self.cycle))
        for state in states:
            # 17 each of the first four values, and 16 each of the others
            i = int(state.pm_property_id.removeprefix("pm-"))
            state.extra_data = {**state.extra_data, "Floor Count": values[i % 6]}
        PropertyState.objects.bulk_update(states, ["extra_data"])

        def count(filter_type, value=None, value_to=None):
            return len(
                self.get_request_results({name: {"filterType": "number", "type": filter_type, "filter": value, "filterTo": value_to}})
            )

        # Not text, nulls, or booleans, which aren't numbers
        self.assertEqual(count("greaterThan", 10), 34)
        self.assertEqual(count("lessThan", 10), 17)
        self.assertEqual(count("equals", 1234), 17)
        self.assertEqual(count("equals", "1,234"), 17)
        self.assertEqual(count("inRange", 5, 1234), 17)
        self.assertEqual(count("notEqual", 5), 67)  # not blanks, but values that aren't numbers
        self.assertEqual(count("blank"), 16)
        self.assertEqual(count("notBlank"), 84)

    def test_integer_filters_are_not_truncated(self):
        year_built_name = self.get_name("year_built")
        PropertyState.objects.filter(propertyview__cycle=self.cycle, pm_property_id__in=["pm-1", "pm-2"]).update(year_built=1999)

        def count(filter_type, value):
            return len(self.get_request_results({year_built_name: {"filterType": "number", "type": filter_type, "filter": value}}))

        self.assertEqual(count("equals", 1999), 2)
        self.assertEqual(count("equals", 1999.5), 0)

    def test_number_filters_use_display_units(self):
        # Gross floor areas are 1000-1099 ft², shown in whole m²
        self.org.display_units_area = "m**2"
        self.org.display_decimal_places = 0
        self.org.save()
        shown = [round((1000 + i) * 0.09290304) for i in range(100)]

        def count(filter_type, value):
            return len(self.get_request_results({self.gfa_name: {"filterType": "number", "type": filter_type, "filter": value}}))

        self.assertEqual(count("equals", 93), shown.count(93))
        self.assertEqual(count("greaterThan", 100), sum(area > 100 for area in shown))
        self.assertEqual(count("lessThanOrEqual", 95), sum(area <= 95 for area in shown))

    def test_number_filters_round_as_shown(self):
        # Halfway values, including those stored just below or above halfway (e.g., 2.675 is 2.67499...), and one shown in m²
        areas = [0.5, 1.5, 2.5, -0.5, -1.5, -2.5, 2.675, -2.675, 1.005, 12.345, 45.125, -0.125, 1234.565, 7812.5]
        views = list(PropertyView.objects.filter(cycle=self.cycle).order_by("id")[: len(areas)])
        for view, area in zip(views, areas, strict=True):
            PropertyState.objects.filter(pk=view.state_id).update(gross_floor_area=area)

        def matches(filter_type, value):
            filters = {self.gfa_name: {"filterType": "number", "type": filter_type, "filter": value}}
            return {row["property_view_id"] for row in self.get_request_results(filters)}

        for units, places in [("ft**2", 0), ("ft**2", 2), ("m**2", 2)]:
            self.org.display_units_area = units
            self.org.display_decimal_places = places
            self.org.save()
            shown = {row["property_view_id"]: row[self.gfa_name] for row in self.get_request_results({})}
            for view, area in zip(views, areas, strict=True):
                value = shown[view.id]
                # As the serializer rounds (half to even, on the stored binary value)
                self.assertEqual(value, round((area * ureg("ft**2")).to(units).magnitude, places))
                step = 10**-places
                self.assertIn(view.id, matches("equals", value), (area, units, places))
                self.assertNotIn(view.id, matches("equals", round(value + step, places)), (area, units, places))
                self.assertNotIn(view.id, matches("equals", round(value - step, places)), (area, units, places))
                self.assertNotIn(view.id, matches("greaterThan", value), (area, units, places))
                self.assertIn(view.id, matches("lessThanOrEqual", value), (area, units, places))

    def test_json_keys_like_indexes_or_lookups(self):
        for column_name in ["2019", "a__b"]:
            Column.objects.create(table_name="PropertyState", column_name=column_name, organization=self.org, is_extra_data=True)
        states = list(PropertyState.objects.filter(propertyview__cycle=self.cycle))
        for state in states:
            if int(state.pm_property_id.removeprefix("pm-")) < 10:
                state.extra_data = {**state.extra_data, "2019": "x", "a__b": "y"}
        PropertyState.objects.bulk_update(states, ["extra_data"])

        self.assertEqual(len(self.get_request_results({self.get_name("2019"): self.get_filter("notBlank")})), 10)
        self.assertEqual(len(self.get_request_results({self.get_name("a__b"): self.get_filter("equals", "Y")})), 10)

    def test_invalid_filters(self):
        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(self.query_string)
        for filter_dict in [
            {"filterType": "text", "type": "greaterThan", "filter": 1},
            {"filterType": "number", "type": "contains", "filter": 1},
            {"filterType": "number", "type": "equals", "filter": "abc"},
            {"filterType": "number", "type": "inRange", "filter": 1},
            {"filterType": "text", "type": "equals"},
            {"filterType": "set", "type": "equals", "filter": "a"},
        ]:
            response = self.client.post(url, data={"filters": {self.gfa_name: filter_dict}}, content_type="application/json")
            self.assertEqual(response.status_code, 400, filter_dict)

        # Filters of a filter group saved by the legacy UI apply, as in reports
        self.assertEqual(len(self.get_request_results({f"{self.al1_name}__icontains": "address"})), 50)

    def test_boolean_filters(self):
        Column.objects.create(
            table_name="PropertyState", column_name="Has Solar", organization=self.org, is_extra_data=True, data_type="boolean"
        )
        name = self.get_name("Has Solar")
        states = list(PropertyState.objects.filter(propertyview__cycle=self.cycle))
        for state in states:
            # 34 true, 33 false, and 33 null
            state.extra_data = {**state.extra_data, "Has Solar": [True, False, None][int(state.pm_property_id.removeprefix("pm-")) % 3]}
        PropertyState.objects.bulk_update(states, ["extra_data"])

        # AG Grid's text filter options for boolean values: "Choose one" (no filter), True, and False
        def count(condition):
            return len(self.get_request_results({name: {"filterType": "text", "type": condition}}))

        self.assertEqual(count("true"), 34)
        self.assertEqual(count("false"), 33)
        self.assertEqual(count("empty"), 100)

        # The grid's type for the column, which shows checkboxes and these options
        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(self.query_string)
        column_defs = self.client.post(url, content_type="application/json").json()["column_defs"]
        self.assertEqual(next(c for c in column_defs if c["field"] == name)["context"], {"filterType": "boolean"})

    def test_filters_with_another_filter_types_values(self):
        # AG Grid keeps a filter's values when it changes its type, e.g., for a filter saved when the grid inferred it
        year_ending_name = self.get_name("year_ending")
        PropertyState.objects.filter(propertyview__cycle=self.cycle, pm_property_id__in=["pm-1", "pm-2"]).update(
            year_ending=date(2002, 12, 31)
        )

        date_with_text_value = {year_ending_name: {"filterType": "date", "type": "equals", "filter": "2002-12-31"}}
        text_with_date_value = {year_ending_name: {"filterType": "text", "type": "equals", "dateFrom": "2002-12-31 00:00:00"}}
        self.assertEqual(len(self.get_request_results(date_with_text_value)), 2)
        self.assertEqual(len(self.get_request_results(text_with_date_value)), 2)

    @staticmethod
    def date_filter(name, filter_type, date_from=None, date_to=None):
        """A filter as AG Grid's date filter sends it, with `dateFrom` and `dateTo` formatted as YYYY-MM-DD hh:mm:ss"""
        return {name: {"filterType": "date", "type": filter_type, "dateFrom": date_from, "dateTo": date_to}}

    def test_date_filters(self):
        year_ending_name = self.get_name("year_ending")
        states = list(PropertyState.objects.filter(propertyview__cycle=self.cycle))
        for state in states:
            # 15 each in 2001-2004, and 40 blank
            i = int(state.pm_property_id.removeprefix("pm-"))
            state.year_ending = date(2001 + i % 4, 12, 31) if i < 60 else None
        PropertyState.objects.bulk_update(states, ["year_ending"])

        def count(filter_type, date_from=None, date_to=None):
            return len(self.get_request_results(self.date_filter(year_ending_name, filter_type, date_from, date_to)))

        self.assertEqual(count("equals", "2002-12-31 00:00:00"), 15)
        self.assertEqual(count("equals", "2002-12-31T00:00:00"), 15)  # as the floating filter sends it
        self.assertEqual(count("notEqual", "2002-12-31 00:00:00"), 45)  # not blanks
        self.assertEqual(count("greaterThan", "2002-12-31 00:00:00"), 30)
        self.assertEqual(count("lessThan", "2002-12-31 00:00:00"), 15)
        self.assertEqual(count("lessThan", "9999-12-31 00:00:00"), 60)
        self.assertEqual(count("inRange", "2001-12-31 00:00:00", "2004-12-31 00:00:00"), 30)  # excludes its ends
        self.assertEqual(count("blank"), 40)
        self.assertEqual(count("notBlank"), 60)

        first_or_last = {
            year_ending_name: {
                "filterType": "date",
                "operator": "OR",
                "conditions": [
                    self.date_filter(year_ending_name, "equals", "2001-12-31 00:00:00")[year_ending_name],
                    self.date_filter(year_ending_name, "equals", "2004-12-31 00:00:00")[year_ending_name],
                ],
            }
        }
        self.assertEqual(len(self.get_request_results(first_or_last)), 30)

        # Not dates the grid sends, or not date columns
        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(self.query_string)
        for filters in [
            self.date_filter(year_ending_name, "equals", "not a date"),
            self.date_filter(year_ending_name, "equals", "2002-12-31T00:00:00Z"),
            self.date_filter(year_ending_name, "inRange", "2001-12-31 00:00:00"),
            self.date_filter(self.get_name("year_built"), "equals", "2002-12-31 00:00:00"),
        ]:
            response = self.client.post(url, data={"filters": filters}, content_type="application/json")
            self.assertEqual(response.status_code, 400)

    def test_date_filters_on_text_columns(self):
        # e.g., date filters saved before the server chose filter types, which AG Grid inferred from dates
        custom_id_1_name = self.get_name("custom_id_1")
        states = PropertyState.objects.filter(propertyview__cycle=self.cycle)
        states.filter(pm_property_id__in=[f"pm-{i}" for i in range(0, 100, 10)]).update(custom_id_1="2019-12-31")
        states.filter(pm_property_id__in=[f"pm-{i}" for i in range(5, 100, 10)]).update(custom_id_1="")

        def count(filter_type, date_from=None):
            return len(self.get_request_results(self.date_filter(custom_id_1_name, filter_type, date_from)))

        self.assertEqual(count("equals", "2019-12-31 00:00:00"), 10)
        self.assertEqual(count("notEqual", "2019-12-31 00:00:00"), 80)  # other text, but not blanks
        self.assertEqual(count("greaterThan", "2019-12-30 00:00:00"), 10)
        self.assertEqual(count("blank"), 10)
        self.assertEqual(count("notBlank"), 90)

    def test_date_time_filters_on_repeated_clock_times(self):
        # 1:30 AM happens twice in Los Angeles on 2020-11-01, and both show that day
        recent_sale_date_name = self.get_name("recent_sale_date")
        states = PropertyState.objects.filter(propertyview__cycle=self.cycle)
        states.filter(pm_property_id="pm-0").update(recent_sale_date=datetime(2020, 11, 1, 8, 30, tzinfo=UTC))
        states.filter(pm_property_id="pm-1").update(recent_sale_date=datetime(2020, 11, 1, 9, 30, tzinfo=UTC))

        with timezone.override("America/Los_Angeles"):
            equals = self.get_request_results(self.date_filter(recent_sale_date_name, "equals", "2020-11-01 00:00:00"))
            after = self.get_request_results(self.date_filter(recent_sale_date_name, "greaterThan", "2020-11-01 00:00:00"))
        self.assertEqual(sorted(r[self.pmpid_name] for r in equals), ["pm-0", "pm-1"])
        self.assertEqual(after, [])

    def test_date_time_filters(self):
        recent_sale_date_name = self.get_name("recent_sale_date")
        updated_name = self.get_name("updated")
        states = PropertyState.objects.filter(propertyview__cycle=self.cycle)
        states.filter(pm_property_id__in=[f"pm-{i}" for i in range(0, 50, 2)]).update(
            recent_sale_date=datetime(2020, 6, 1, 9, tzinfo=get_current_timezone())
        )
        states.filter(pm_property_id__in=[f"pm-{i}" for i in range(1, 50, 2)]).update(
            recent_sale_date=datetime(2020, 6, 1, 15, tzinfo=get_current_timezone())
        )
        # Serialized (and shown) in UTC, unlike the other date times: 2020-06-02, but 2020-06-01 in the Americas
        states.filter(pm_property_id__in=[f"pm-{i}" for i in range(10)]).update(updated=datetime(2020, 6, 2, 3, tzinfo=UTC))

        def count(name, filter_type, date_from=None, date_to=None):
            return len(self.get_request_results(self.date_filter(name, filter_type, date_from, date_to)))

        # Date times compare by the day shown, ignoring a filter's time
        self.assertEqual(count(recent_sale_date_name, "equals", "2020-06-01 00:00:00"), 50)
        self.assertEqual(count(recent_sale_date_name, "equals", "2020-06-01 12:34:56"), 50)
        self.assertEqual(count(recent_sale_date_name, "equals", "2020-06-02 00:00:00"), 0)
        self.assertEqual(count(recent_sale_date_name, "notEqual", "2020-06-02 00:00:00"), 50)
        self.assertEqual(count(recent_sale_date_name, "greaterThan", "2020-05-31 00:00:00"), 50)
        self.assertEqual(count(recent_sale_date_name, "lessThan", "2020-06-01 00:00:00"), 0)
        self.assertEqual(count(recent_sale_date_name, "inRange", "2020-05-31 00:00:00", "2020-06-02 00:00:00"), 50)
        self.assertEqual(count(recent_sale_date_name, "blank"), 50)
        self.assertEqual(count(updated_name, "equals", "2020-06-02 00:00:00"), 10)
        self.assertEqual(count(updated_name, "lessThan", "2020-06-02 00:00:00"), 0)

    def test_json_date_filters(self):
        Column.objects.create(table_name="PropertyState", column_name="Inspection Date", organization=self.org, is_extra_data=True)
        name = self.get_name("Inspection Date")
        # Days 2019-12-31, 2019-12-30, 2020-01-01, 2019-12-31, and 2019-12-31, then text that isn't a date, and blank
        values = [
            "2019-12-31 00:00:00",
            "2019-12-30T10:00:00",
            "2020-01-01",
            "2019-12-31 10:00",
            "2019-12-31 (est.)",
            "n/a",
            "2019-13-01",
            None,
        ]
        states = list(PropertyState.objects.filter(propertyview__cycle=self.cycle))
        for state in states:
            # 12 of the first value, 11 each of the others, and 11 missing
            i = int(state.pm_property_id.removeprefix("pm-"))
            if i % 9 < len(values):
                state.extra_data = {**state.extra_data, "Inspection Date": values[i % 9]}
        PropertyState.objects.bulk_update(states, ["extra_data"])

        def count(filter_type, date_from=None, date_to=None):
            return len(self.get_request_results(self.date_filter(name, filter_type, date_from, date_to)))

        self.assertEqual(count("equals", "2019-12-31 00:00:00"), 34)
        self.assertEqual(count("equals", "2020-01-01 00:00:00"), 11)
        self.assertEqual(count("greaterThan", "2019-12-31 00:00:00"), 11)
        self.assertEqual(count("lessThan", "2019-12-31 00:00:00"), 11)
        self.assertEqual(count("inRange", "2019-12-30 00:00:00", "2020-01-01 00:00:00"), 34)
        self.assertEqual(count("notEqual", "2019-12-31 00:00:00"), 44)  # not blanks, but text that isn't a date
        self.assertEqual(count("blank"), 22)
        self.assertEqual(count("notBlank"), 78)

        # Text filters include blanks in notEqual
        not_equal = {name: self.get_filter("notEqual", "n/a")}
        self.assertEqual(len(self.get_request_results(not_equal)), 89)

    def test_unknown_columns_are_ignored(self):
        unknown_filters = [
            {"deleted_column_999999999": self.get_filter("notBlank")},
            {"not_a_column": self.get_filter("notBlank")},
        ]
        for filters in unknown_filters:
            self.assertEqual(len(self.get_request_results(filters)), 100)

        self.assertEqual(len(self.get_request_results(None, ["-deleted_column_999999999", "not_a_column"])), 100)

    def test_extra_data_column_with_canonical_name_on_other_table(self):
        Column.objects.create(table_name="TaxLotState", column_name="gross_floor_area", organization=self.org, is_extra_data=True)
        self.query_string["include_related"] = True

        gt = {self.gfa_name: self.get_filter("greaterThan", 1010)}
        self.assertEqual(len(self.get_request_results(gt)), 89)  # 11-99


class RelatedTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.root_owner_user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_factory = FakeTaxLotFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)
        self.taxlot_view_factory = FakeTaxLotViewFactory(organization=self.org)
        self.taxlot_property_factory = FakeTaxLotPropertyFactory(organization=self.org, user=self.superuser)

        # cycles
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2001, 1, 1), end=datetime(2002, 1, 1))

        # create related taxlot and property views
        tlv1 = self.taxlot_view_factory.get_taxlot_view(cycle=self.cycle, jurisdiction_tax_lot_id="jt-1")  # multiple properties
        tlv2a = self.taxlot_view_factory.get_taxlot_view(cycle=self.cycle, jurisdiction_tax_lot_id="jt-2a")
        tlv2b = self.taxlot_view_factory.get_taxlot_view(cycle=self.cycle, jurisdiction_tax_lot_id="jt-2b")
        self.taxlot_view_factory.get_taxlot_view(cycle=self.cycle, jurisdiction_tax_lot_id="jt-3")  # no properties

        pv1a = self.property_view_factory.get_property_view(cycle=self.cycle, pm_property_id="pm-1a", site_eui=10)
        pv1b = self.property_view_factory.get_property_view(cycle=self.cycle, pm_property_id="pm-1b", site_eui=11)
        pv2 = self.property_view_factory.get_property_view(cycle=self.cycle, pm_property_id="pm-2", site_eui=20)  # multiple taxlots
        self.property_view_factory.get_property_view(cycle=self.cycle, pm_property_id="pm-3", site_eui=30)  # no taxlots

        self.taxlot_property_factory.get_taxlot_property(cycle=self.cycle, property_view=pv1a, taxlot_view=tlv1)
        self.taxlot_property_factory.get_taxlot_property(cycle=self.cycle, property_view=pv1b, taxlot_view=tlv1)
        self.taxlot_property_factory.get_taxlot_property(cycle=self.cycle, property_view=pv2, taxlot_view=tlv2a)
        self.taxlot_property_factory.get_taxlot_property(cycle=self.cycle, property_view=pv2, taxlot_view=tlv2b)

        def get_column_name(column_name):
            return ColumnSerializer(Column.objects.filter(column_name=column_name).first()).data["name"]

        self.pmpid_name = get_column_name("pm_property_id")
        self.seui_name = get_column_name("site_eui")
        self.jtlid_name = get_column_name("jurisdiction_tax_lot_id")

        self.extra_data_column_names = list(
            Column.objects.filter(organization=self.org, is_extra_data=True).values_list("column_name", flat=True)
        )

        # shortcut
        self.pv_filter = PropertyView.objects.filter

    def get_filter(self, filter_type, filter_val=None):
        # As AG Grid sends them: comparisons from number filters, and the rest from text filters
        kind = "number" if filter_type in {"greaterThan", "greaterThanOrEqual", "lessThan", "lessThanOrEqual", "inRange"} else "text"
        filter_dict = {"filterType": kind, "type": filter_type}
        if filter_val:
            filter_dict["filter"] = filter_val
        return filter_dict

    def test_related_results(self):
        query_string = {
            "cycle": self.cycle.id,
            "ids_only": False,
            "inventory_type": "property",
            "include_related": True,
            "organization_id": self.org.id,
            "page": 1,
            "per_page": 100,
        }

        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(query_string)
        response = self.client.post(url)
        data = response.json()
        results = data["results"]
        self.assertEqual(len(results), 4)

        pv1a = next(p for p in results if p.get(self.pmpid_name) == "pm-1a")
        pv2 = next(p for p in results if p.get(self.pmpid_name) == "pm-2")
        pv3 = next(p for p in results if p.get(self.pmpid_name) == "pm-3")

        self.assertEqual(pv1a.get(self.jtlid_name), "jt-1")
        self.assertEqual(pv2.get(self.jtlid_name), "jt-2a; jt-2b")
        self.assertEqual(pv3.get(self.jtlid_name), None)

        query_string["inventory_type"] = "taxlot"
        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(query_string)
        response = self.client.post(url)
        data = response.json()
        results = data["results"]

        tlv1 = next(t for t in results if t.get(self.jtlid_name) == "jt-1")
        tlv2a = next(t for t in results if t.get(self.jtlid_name) == "jt-2a")
        tlv3 = next(t for t in results if t.get(self.jtlid_name) == "jt-3")

        self.assertEqual(tlv1.get(self.pmpid_name), "pm-1a; pm-1b")
        self.assertEqual(tlv2a.get(self.pmpid_name), "pm-2")
        self.assertEqual(tlv3.get(self.pmpid_name), None)

    def test_related_filter(self):
        # filter on taxlot given properties
        query_string = {
            "cycle": self.cycle.id,
            "ids_only": False,
            "inventory_type": "property",
            "include_related": True,
            "organization_id": self.org.id,
            "page": 1,
            "per_page": 100,
        }
        filter = {self.jtlid_name: self.get_filter("contains", "jt")}
        data = {"filters": filter}

        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(query_string)
        response = self.client.post(url, data=data, content_type="application/json")
        data = response.json()
        results = data["results"]
        # of the 4 properties, only 3 are associated with taxlots
        self.assertEqual(len(results), 3)

        filter = {self.jtlid_name: self.get_filter("contains", "2")}
        data = {"filters": filter}

        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(query_string)
        response = self.client.post(url, data=data, content_type="application/json")
        data = response.json()
        results = data["results"]
        # while there are multiple taxlots with j-ids with '2', only one property is associated with them
        self.assertEqual(len(results), 1)

    def get_property_results(self, filters=None, sorts=None):
        query_string = {"cycle": self.cycle.id, "inventory_type": "property", "include_related": True, "organization_id": self.org.id}
        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(query_string)
        response = self.client.post(url, data={"filters": filters, "sorts": sorts}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        return sorted(r[self.pmpid_name] for r in response.json()["results"])

    def get_results(self, inventory_type, filters=None):
        query_string = {"cycle": self.cycle.id, "inventory_type": inventory_type, "include_related": True, "organization_id": self.org.id}
        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(query_string)
        response = self.client.post(url, data={"filters": filters}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        return response.json()["results"]

    def get_name(self, table_name, column_name):
        return ColumnSerializer(Column.objects.get(organization=self.org, table_name=table_name, column_name=column_name)).data["name"]

    def test_related_booleans_are_text(self):
        # Related values show joined, e.g., "False; True"
        Column.objects.create(
            table_name="TaxLotState", column_name="Corner Lot", organization=self.org, is_extra_data=True, data_type="boolean"
        )
        query_string = {"cycle": self.cycle.id, "inventory_type": "property", "include_related": True, "organization_id": self.org.id}
        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(query_string)
        column_defs = self.client.post(url, content_type="application/json").json()["column_defs"]
        name = self.get_name("TaxLotState", "Corner Lot")
        self.assertEqual(next(c for c in column_defs if c["field"] == name)["context"], {"filterType": "text"})

    def test_related_dates_show_and_filter_as_shown(self):
        # Tax lots, by their properties' year ending
        name = self.get_name("PropertyState", "year_ending")
        PropertyState.objects.filter(pm_property_id="pm-1a").update(year_ending=date(2001, 12, 31))
        PropertyState.objects.filter(pm_property_id="pm-1b").update(year_ending=date(2002, 12, 31))

        def taxlots(filters=None):
            return {row[self.jtlid_name]: row.get(name) for row in self.get_results("taxlot", filters)}

        self.assertEqual(taxlots()["jt-1"], "2001-12-31; 2002-12-31")
        equals = {name: {"filterType": "date", "type": "equals", "dateFrom": "2002-12-31 00:00:00", "dateTo": None}}
        self.assertEqual(list(taxlots(equals)), ["jt-1"])
        self.assertEqual(sorted(taxlots({name: self.get_filter("blank")})), ["jt-2a", "jt-2b", "jt-3"])

    def test_related_timestamps_are_the_related_records(self):
        # As the grid shows them, the related Property's or TaxLot's time stamps, not their states'
        def equals(name, day):
            return {name: {"filterType": "date", "type": "equals", "dateFrom": f"{day} 00:00:00", "dateTo": None}}

        updated_name = self.get_name("PropertyState", "updated")
        Property.objects.filter(views__state__pm_property_id="pm-2").update(updated=datetime(2020, 6, 2, 3, tzinfo=UTC))
        PropertyState.objects.filter(pm_property_id="pm-2").update(updated=datetime(2019, 1, 1, tzinfo=UTC))

        def taxlots(filters=None):
            return {row[self.jtlid_name]: row.get(updated_name) for row in self.get_results("taxlot", filters)}

        self.assertEqual(taxlots()["jt-2a"], "2020-06-02T03:00:00Z")
        self.assertEqual(sorted(taxlots(equals(updated_name, "2020-06-02"))), ["jt-2a", "jt-2b"])
        self.assertEqual(taxlots(equals(updated_name, "2019-01-01")), {})

        created_name = self.get_name("TaxLotState", "created")
        TaxLot.objects.filter(views__state__jurisdiction_tax_lot_id="jt-1").update(created=datetime(2020, 6, 2, 3, tzinfo=UTC))
        TaxLotState.objects.filter(jurisdiction_tax_lot_id="jt-1").update(created=datetime(2019, 1, 1, tzinfo=UTC))
        properties = {
            row[self.pmpid_name]: row.get(created_name) for row in self.get_results("property", equals(created_name, "2020-06-02"))
        }
        self.assertEqual(properties, {"pm-1a": "2020-06-02T03:00:00Z", "pm-1b": "2020-06-02T03:00:00Z"})
        self.assertEqual(self.get_results("property", equals(created_name, "2019-01-01")), [])

    def test_related_derived_column_filter(self):
        derived_column = DerivedColumn.objects.create(
            name="Tax Lot EUI", expression="$a / 2", organization=self.org, inventory_type=DerivedColumn.TAXLOT_TYPE
        )
        derived_name = ColumnSerializer(derived_column.column).data["name"]
        TaxLotState.objects.filter(jurisdiction_tax_lot_id="jt-1").update(derived_data={derived_column.name: 5})

        not_blank = {derived_name: self.get_filter("notBlank")}
        blank = {derived_name: self.get_filter("blank")}
        self.assertEqual(self.get_property_results(not_blank), ["pm-1a", "pm-1b"])
        self.assertEqual(self.get_property_results(blank), ["pm-2", "pm-3"])

    def test_related_not_blank_with_a_blank_related_value(self):
        address_column = Column.objects.get(organization=self.org, table_name="TaxLotState", column_name="address_line_1")
        address_name = ColumnSerializer(address_column).data["name"]
        TaxLotState.objects.filter(jurisdiction_tax_lot_id="jt-1").update(address_line_1="1 Main St")
        TaxLotState.objects.filter(jurisdiction_tax_lot_id="jt-2a").update(address_line_1="2 Main St")
        TaxLotState.objects.filter(jurisdiction_tax_lot_id__in=["jt-2b", "jt-3"]).update(address_line_1=None)

        # pm-2 shows jt-2a's address, though jt-2b has none
        for filter_type in ["text", "number"]:
            not_blank = {address_name: {"filterType": filter_type, "type": "notBlank"}}
            self.assertEqual(self.get_property_results(not_blank), ["pm-1a", "pm-1b", "pm-2"])

    def test_related_text_blank_on_number_column(self):
        query_string = {"cycle": self.cycle.id, "inventory_type": "taxlot", "include_related": True, "organization_id": self.org.id}
        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(query_string)
        data = {"filters": {self.seui_name: self.get_filter("notBlank")}}
        response = self.client.post(url, data=data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        # jt-3 has no properties
        self.assertEqual(sorted(r[self.jtlid_name] for r in response.json()["results"]), ["jt-1", "jt-2a", "jt-2b"])

    def test_related_conditions_match_any_related_record(self):
        # pm-2 shows "jt-2a; jt-2b", and pm-3 has no tax lots
        self.assertEqual(self.get_property_results({self.jtlid_name: self.get_filter("equals", "JT-2A")}), ["pm-2"])
        # Negated conditions match if no related record does
        self.assertEqual(self.get_property_results({self.jtlid_name: self.get_filter("notEqual", "jt-2a")}), ["pm-1a", "pm-1b", "pm-3"])
        self.assertEqual(self.get_property_results({self.jtlid_name: self.get_filter("notContains", "2")}), ["pm-1a", "pm-1b", "pm-3"])

        # Each condition can match a different related record, as in the cell
        both = {
            "filterType": "text",
            "operator": "AND",
            "conditions": [self.get_filter("equals", "jt-2a"), self.get_filter("equals", "jt-2b")],
        }
        self.assertEqual(self.get_property_results({self.jtlid_name: both}), ["pm-2"])
        address_column = Column.objects.get(organization=self.org, table_name="TaxLotState", column_name="address_line_1")
        address_name = ColumnSerializer(address_column).data["name"]
        TaxLotState.objects.filter(jurisdiction_tax_lot_id="jt-2a").update(address_line_1="2 Main St")
        TaxLotState.objects.filter(jurisdiction_tax_lot_id="jt-2b").update(address_line_1=None)
        different_records = {self.jtlid_name: self.get_filter("equals", "jt-2b"), address_name: self.get_filter("contains", "main")}
        self.assertEqual(self.get_property_results(different_records), ["pm-2"])

    def test_legacy_related_filters(self):
        # e.g., a legacy filter group's: pm-3 has no tax lots, and jt-3 no properties
        def taxlots(filters):
            return sorted(r[self.jtlid_name] for r in self.get_results("taxlot", filters))

        self.assertEqual(self.get_property_results({f"{self.jtlid_name}__icontains": "jt-2"}), ["pm-2"])
        self.assertEqual(self.get_property_results({f"{self.jtlid_name}__exact": ""}), ["pm-3"])
        self.assertEqual(taxlots({f"{self.pmpid_name}__ne": "pm-1a", f"{self.seui_name}__lt": "20"}), ["jt-1"])
        # One property must match them all (jt-1's pm-1a has a site EUI of 10, and its pm-1b is 11)
        self.assertEqual(taxlots({f"{self.pmpid_name}__exact": "pm-1a", f"{self.seui_name}__gt": "10"}), [])
        self.assertEqual(taxlots({f"{self.pmpid_name}__exact": ""}), ["jt-3"])
        self.assertEqual(
            taxlots({f"{self.seui_name}__gt": "10", self.jtlid_name: self.get_filter("contains", "jt")}), ["jt-1", "jt-2a", "jt-2b"]
        )

        # Values that a related column's field can't compare are invalid, as for a record's own (e.g., after a data type change)
        Column.objects.filter(organization=self.org, table_name="PropertyState", column_name="site_eui").update(data_type="string")
        query_string = {"cycle": self.cycle.id, "inventory_type": "taxlot", "organization_id": self.org.id}
        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(query_string)
        response = self.client.post(url, data={"filters": {f"{self.seui_name}__gt": "abc"}}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_related_extra_data_quantities_compare_as_shown(self):
        # Unlike its own quantities, a record's related extra data shows as stored, not in the display units
        self.org.display_units_area = "m**2"
        self.org.save()
        column = Column.objects.create(
            table_name="TaxLotState", column_name="Lot Area", organization=self.org, is_extra_data=True, data_type="area"
        )
        TaxLotState.objects.filter(jurisdiction_tax_lot_id="jt-1").update(extra_data={"Lot Area": 5000})

        over_1000 = {ColumnSerializer(column).data["name"]: {"filterType": "number", "type": "greaterThan", "filter": 1000}}
        self.assertEqual(self.get_property_results(over_1000), ["pm-1a", "pm-1b"])

    def test_related_sort_is_ignored(self):
        # Related columns aren't sortable, and PropertyState has no jurisdiction_tax_lot_id
        self.assertEqual(self.get_property_results(sorts=[f"-{self.jtlid_name}"]), ["pm-1a", "pm-1b", "pm-2", "pm-3"])


class RoundHalfEvenTests(TestCase):
    def test_rounds_as_python(self):
        org = Organization.objects.create(name="Rounding")
        rng = random.Random(0)
        for places in range(5):
            values = []
            for k in range(-60, 61):
                half = (k + 0.5) / 10**places
                values += [half, math.nextafter(half, -math.inf), math.nextafter(half, math.inf)]
            values += [rng.uniform(-1e6, 1e6) for _ in range(100)]
            values += [round(rng.uniform(-1e4, 1e4), places + 1) for _ in range(100)]
            # Around where `round` leaves numbers as they are, and too large for the error term
            limit = 2**53 / 10**places
            values += [limit * factor for factor in [-4, -1.5, -1, -0.75, 0.75, 1, 1.5, 4]] + [1.5e300, -1e308]

            annotations = {f"v{i}": round_half_even(Value(value), places) for i, value in enumerate(values)}
            rounded = Organization.objects.filter(pk=org.pk).annotate(**annotations).values(*annotations).get()
            for i, value in enumerate(values):
                self.assertEqual(rounded[f"v{i}"], round(value, places), (value, places))

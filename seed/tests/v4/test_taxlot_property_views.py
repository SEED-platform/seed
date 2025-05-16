"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime
from urllib.parse import urlencode

from django.urls import reverse
from django.utils.timezone import (
    get_current_timezone,
)

from seed.data_importer.tasks import geocode_and_match_buildings_task
from seed.landing.models import SEEDUser as User
from seed.models import (
    DATA_STATE_MAPPING,
    Column,
    ColumnMappingProfile,
    Property,
    PropertyView,
    StatusLabel,
    TaxLotProperty,
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
        self.assertEqual(list(column_defs[0].keys()), ["field", "headerName"])
        self.assertEqual(list(column_defs[-1].keys()), ["field", "headerName", "sortable"])  # other inventory columns are not sortable

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
        filter_dict = {"filterType": "text", "type": filter_type}
        if filter_val:
            filter_dict["filter"] = filter_val
        return filter_dict

    def get_request_results(self, filters):
        data = {"filters": filters}
        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(self.query_string)
        response = self.client.post(url, data=data, content_type="application/json")
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
        filter_dict = {"filterType": "text", "type": filter_type}
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

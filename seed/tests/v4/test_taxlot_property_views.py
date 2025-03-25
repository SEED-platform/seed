"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime

from django.urls import reverse
from django.utils.timezone import (
    get_current_timezone,
)
from django.db.models import Q

from seed.data_importer.tasks import geocode_and_match_buildings_task
from seed.landing.models import SEEDUser as User
from seed.models import (
    DATA_STATE_MAPPING,
    Column,
    ColumnMappingProfile,
    Property,
    PropertyState,
    PropertyView,
    StatusLabel,
    TaxLotProperty,
    TaxLotView,
)
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeColumnListProfileFactory,
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeTaxLotFactory,
    FakeTaxLotStateFactory,
)
from seed.serializers.columns import ColumnSerializer
from seed.tests.util import AccessLevelBaseTestCase, DataMappingBaseTestCase
from seed.utils.organizations import create_organization
from seed.utils.v4.inventory_filter import generate_Q_filters




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
        self.assertEqual(list(column_defs[-1].keys()), ["field", "headerName"])

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
        self.cycle1 = self.cycle_factory.get_cycle(start=datetime(2001, 1, 1), end=datetime(2002, 1, 1))
        # columns with column name as formatted by frontend: {column_name}_{column_id}
        Column.objects.create(table_name="PropertyState", column_name="extra_eui", organization=self.org, is_extra_data=True)
        def get_column_name(column_name):
            return ColumnSerializer(Column.objects.filter(column_name=column_name).first()).data["name"]
        self.al1_name = get_column_name("address_line_1")
        self.cid1_name = get_column_name("custom_id_1")
        self.pmpid_name = get_column_name("pm_property_id")
        self.gfa_name = get_column_name("gross_floor_area")
        self.extra_eui_name = get_column_name("extra_eui")

        # create a 100 properties
        property_details = self.property_state_factory.get_details()
        def get_property_details(i):
            
            property_details.update({
                "address_line_1": f"address{i}" if i % 2 != 0 else "",
                "custom_id_1": f"custom_id{i}" if i % 5 != 0 else None,
                "gross_floor_area": 1000 + i,
                "pm_property_id": f"pm-{i}",
                "extra_data": {"extra_eui": 100 + i},
            })
            return property_details

        for i in range(100):
            property = self.property_factory.get_property()
            state = self.property_state_factory.get_property_state(**get_property_details(i))
            self.property_view_factory.get_property_view(prprty=property, cycle=self.cycle1, state=state)

        # shortcut
        self.pv_filter = PropertyView.objects.filter

    def get_filter(self, type, filter=None):
        filter_dict = {"filterType": "text", "type": type}
        if filter:
            filter_dict["filter"] = filter
        return filter_dict

    def test_contains(self):
        c = { self.pmpid_name: self.get_filter("contains", "0")}
        nc = { self.pmpid_name: self.get_filter("notContains", "0")}
        c2x = { self.pmpid_name: self.get_filter("contains", "1"), self.gfa_name: self.get_filter("contains", 2)}
        c_or_nc = { self.pmpid_name: { "filterType": 'text', "operator": "OR", "conditions": [
                self.get_filter("contains", "10"), 
                self.get_filter("notContains", "1")
        ]}}
        c_and_nc = { self.pmpid_name: { "filterType": 'text', "operator": "AND", "conditions": [
                self.get_filter("contains", "1"), 
                self.get_filter("notContains", "2")
        ]}}

        contain = generate_Q_filters(c)
        not_contain = generate_Q_filters(nc)
        contain_2x = generate_Q_filters(c2x)
        contain_or_not_contain = generate_Q_filters(c_or_nc)
        contain_and_not_contain = generate_Q_filters(c_and_nc)


        self.assertEqual(self.pv_filter(contain).count(), 10)
        self.assertEqual(self.pv_filter(not_contain).count(), 90)
        self.assertEqual(self.pv_filter(contain_2x).count(), 2) # 12 and 21
        self.assertEqual(self.pv_filter(contain_or_not_contain).count(), 82) # not 1, 11-19, 21, 31, ...91
        self.assertEqual(self.pv_filter(contain_and_not_contain).count(), 17) # 1, 10, 11, 13, ...21, 31, ...91


    def test_equals(self):
        e = { self.pmpid_name: self.get_filter("equals", "pm-1")}
        ne = { self.pmpid_name: self.get_filter("notEqual", "pm-1")}
        e2x = { self.pmpid_name: self.get_filter("equals", "pm-1"), self.gfa_name: self.get_filter("equals", 1002)}

        equal = generate_Q_filters(e)
        not_equal = generate_Q_filters(ne)
        equal_2x = generate_Q_filters(e2x)

        self.assertEqual(self.pv_filter(equal).count(), 1)
        self.assertEqual(self.pv_filter(not_equal).count(), 99)
        self.assertEqual(self.pv_filter(equal_2x).count(), 0)

    def test_starts_with(self):
        bw = { self.pmpid_name: self.get_filter("startsWith", "pm-1")}
        ew = { self.pmpid_name: self.get_filter("endsWith", "1")}
        bw_or_ew = { self.pmpid_name: { "filterType": 'text', "operator": "OR", "conditions": [
                self.get_filter("startsWith", "pm-1"), 
                self.get_filter("endsWith", "2")
        ]}}
        bw_and_ew = { self.pmpid_name: { "filterType": 'text', "operator": "AND", "conditions": [
                self.get_filter("startsWith", "pm-1"), 
                self.get_filter("endsWith", "2")
        ]}}

        begins_with = generate_Q_filters(bw)
        ends_with = generate_Q_filters(ew)
        begins_with_or_ends_with = generate_Q_filters(bw_or_ew)
        begins_with_and_ends_with = generate_Q_filters(bw_and_ew)

        self.assertEqual(self.pv_filter(begins_with).count(), 11)
        self.assertEqual(self.pv_filter(ends_with).count(), 10)
        self.assertEqual(self.pv_filter(begins_with_or_ends_with).count(), 20)
        self.assertEqual(self.pv_filter(begins_with_and_ends_with).count(), 1)
    
    def test_blank(self):
        b_str = { self.al1_name: self.get_filter("blank")}
        b_null = { self.cid1_name: self.get_filter("blank")}
        nb_str = { self.al1_name: self.get_filter("notBlank")}
        nb_null = { self.cid1_name: self.get_filter("notBlank")}
        bs_and_bn = { self.cid1_name: self.get_filter("blank"), self.al1_name: self.get_filter("blank")}

        blank_str = generate_Q_filters(b_str)
        blank_null = generate_Q_filters(b_null)
        not_blank_str = generate_Q_filters(nb_str)
        not_blank_null = generate_Q_filters(nb_null)
        blank_str_and_blank_null = generate_Q_filters(bs_and_bn)

        self.assertEqual(self.pv_filter(blank_str).count(), 50) # evens
        self.assertEqual(self.pv_filter(blank_null).count(), 20) # 5s & 10s
        self.assertEqual(self.pv_filter(not_blank_str).count(), 50) # odds
        self.assertEqual(self.pv_filter(not_blank_null).count(), 80) # not 5s or 10s
        self.assertEqual(self.pv_filter(blank_str_and_blank_null).count(), 10) # 10s

    def test_range(self):
        # >, >=, <, <=, between
        gt = { self.gfa_name: self.get_filter("greaterThan", 1010)}
        gte = { self.gfa_name: self.get_filter("greaterThanOrEqual", 1010)}
        lt = { self.gfa_name: self.get_filter("lessThan", 1010)}
        lte = { self.gfa_name: self.get_filter("lessThanOrEqual", 1010)}
        bt = { self.gfa_name: { "filter": 1010, "filterTo": 1020, "filterType": 'number', "type": "inRange" }}

        greater_than = generate_Q_filters(gt)
        greater_than_or_equal = generate_Q_filters(gte)
        less_than = generate_Q_filters(lt)
        less_than_or_equal = generate_Q_filters(lte)
        between = generate_Q_filters(bt)

        self.assertEqual(self.pv_filter(greater_than).count(), 89) # 11-99
        self.assertEqual(self.pv_filter(greater_than_or_equal).count(), 90) # 10-99
        self.assertEqual(self.pv_filter(less_than).count(), 10) # 0-9
        self.assertEqual(self.pv_filter(less_than_or_equal).count(), 11) # 0-10
        self.assertEqual(self.pv_filter(between).count(), 9) # 11-19
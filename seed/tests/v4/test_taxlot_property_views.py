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
    FakeTaxLotPropertyFactory,
    FakeTaxLotViewFactory,
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


        columns = Column.objects.filter(organization=self.org)
        self.extra_data_column_names = list(columns.filter(is_extra_data=True).values_list("column_name", flat=True))
        
        other_columns = columns.filter(table_name="TaxLotState").values("column_name", "id")
        self.other_column_names_with_id = [f"{c['column_name']}_{c['id']}" for c in other_columns]

        # create a 100 properties
        def get_property_details(i):
            return {
                "address_line_1": f"address{i}" if i % 2 != 0 else "", # evens blank
                "custom_id_1": f"custom_id{i}" if i % 5 != 0 else None, # 5s and 10s None
                "gross_floor_area": 1000 + i,
                "pm_property_id": f"pm-{i}",
                "extra_data": {"extra_eui": 100 + i},
            }
        
        for i in range(100):
            self.property_view_factory.get_property_view(cycle=self.cycle1, **get_property_details(i))


        # shortcuts
        self.q_args = ['property', self.extra_data_column_names, self.other_column_names_with_id]
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



        contain = generate_Q_filters(c, *self.q_args)
        not_contain = generate_Q_filters(nc, *self.q_args)
        contain_2x = generate_Q_filters(c2x, *self.q_args)
        contain_or_not_contain = generate_Q_filters(c_or_nc, *self.q_args)
        contain_and_not_contain = generate_Q_filters(c_and_nc, *self.q_args)

        self.assertEqual(self.pv_filter(contain).count(), 10)
        self.assertEqual(self.pv_filter(not_contain).count(), 90)
        self.assertEqual(self.pv_filter(contain_2x).count(), 2) # 12 and 21
        self.assertEqual(self.pv_filter(contain_or_not_contain).count(), 82) # not 1, 11-19, 21, 31, ...91
        self.assertEqual(self.pv_filter(contain_and_not_contain).count(), 17) # 1, 10, 11, 13, ...21, 31, ...91


    def test_equals(self):
        e = { self.pmpid_name: self.get_filter("equals", "pm-1")}
        ne = { self.pmpid_name: self.get_filter("notEqual", "pm-1")}
        e2x = { self.pmpid_name: self.get_filter("equals", "pm-1"), self.gfa_name: self.get_filter("equals", 1002)}

        equal = generate_Q_filters(e, *self.q_args)
        not_equal = generate_Q_filters(ne, *self.q_args)
        equal_2x = generate_Q_filters(e2x, *self.q_args)

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

        begins_with = generate_Q_filters(bw, *self.q_args)
        ends_with = generate_Q_filters(ew, *self.q_args)
        begins_with_or_ends_with = generate_Q_filters(bw_or_ew, *self.q_args)
        begins_with_and_ends_with = generate_Q_filters(bw_and_ew, *self.q_args)

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

        blank_str = generate_Q_filters(b_str, *self.q_args)
        blank_null = generate_Q_filters(b_null, *self.q_args)
        not_blank_str = generate_Q_filters(nb_str, *self.q_args)
        not_blank_null = generate_Q_filters(nb_null, *self.q_args)
        blank_str_and_blank_null = generate_Q_filters(bs_and_bn, *self.q_args)

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

        greater_than = generate_Q_filters(gt, *self.q_args)
        greater_than_or_equal = generate_Q_filters(gte, *self.q_args)
        less_than = generate_Q_filters(lt, *self.q_args)
        less_than_or_equal = generate_Q_filters(lte, *self.q_args)
        between = generate_Q_filters(bt, *self.q_args)

        self.assertEqual(self.pv_filter(greater_than).count(), 89) # 11-99
        self.assertEqual(self.pv_filter(greater_than_or_equal).count(), 90) # 10-99
        self.assertEqual(self.pv_filter(less_than).count(), 10) # 0-9
        self.assertEqual(self.pv_filter(less_than_or_equal).count(), 11) # 0-10
        self.assertEqual(self.pv_filter(between).count(), 9) # 11-19

    def test_extra_data(self):
        gt = { self.extra_eui_name: self.get_filter("greaterThan", 120)}
        lt = { self.extra_eui_name: self.get_filter("lessThan", 120)}
        greater_than = generate_Q_filters(gt, *self.q_args)
        less_than = generate_Q_filters(lt, *self.q_args)

        self.assertEqual(self.pv_filter(greater_than).count(), 79) # 21-99
        self.assertEqual(self.pv_filter(less_than).count(), 20) # 0-19

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
        tlv1 = self.taxlot_view_factory.get_taxlot_view(cycle=self.cycle, jurisdiction_tax_lot_id="jt-1") # multiple properties
        tlv2a = self.taxlot_view_factory.get_taxlot_view(cycle=self.cycle, jurisdiction_tax_lot_id="jt-2a")
        tlv2b = self.taxlot_view_factory.get_taxlot_view(cycle=self.cycle, jurisdiction_tax_lot_id="jt-2b")
        self.taxlot_view_factory.get_taxlot_view(cycle=self.cycle, jurisdiction_tax_lot_id="jt-3") # no properties

        pv1a = self.property_view_factory.get_property_view(cycle=self.cycle, pm_property_id="pm-1a", site_eui=10)
        pv1b = self.property_view_factory.get_property_view(cycle=self.cycle, pm_property_id="pm-1b", site_eui=11)
        pv2 = self.property_view_factory.get_property_view(cycle=self.cycle, pm_property_id="pm-2", site_eui=20) # multiple taxlots
        self.property_view_factory.get_property_view(cycle=self.cycle, pm_property_id="pm-3", site_eui=30) # no taxlots

        self.taxlot_property_factory.get_taxlot_property(cycle=self.cycle, property_view=pv1a, taxlot_view=tlv1)
        self.taxlot_property_factory.get_taxlot_property(cycle=self.cycle, property_view=pv1b, taxlot_view=tlv1)
        self.taxlot_property_factory.get_taxlot_property(cycle=self.cycle, property_view=pv2, taxlot_view=tlv2a)
        self.taxlot_property_factory.get_taxlot_property(cycle=self.cycle, property_view=pv2, taxlot_view=tlv2b)


        def get_column_name(column_name):
            return ColumnSerializer(Column.objects.filter(column_name=column_name).first()).data["name"]
        
        self.pmpid_name = get_column_name("pm_property_id")
        self.seui_name = get_column_name("site_eui")
        self.jtlid_name = get_column_name("jurisdiction_tax_lot_id")

        self.extra_data_column_names = list(Column.objects.filter(organization=self.org, is_extra_data=True).values_list("column_name", flat=True))

        # shortcut
        self.pv_filter = PropertyView.objects.filter

    def get_filter(self, type, filter=None):
        filter_dict = {"filterType": "text", "type": type}
        if filter:
            filter_dict["filter"] = filter
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
        results = data['results']
        self.assertEqual(len(results), 4)

        pv1a = [p for p in results if p.get(self.pmpid_name) == 'pm-1a'][0]
        pv2 = [p for p in results if p.get(self.pmpid_name) == 'pm-2'][0]
        pv3 = [p for p in results if p.get(self.pmpid_name) == 'pm-3'][0]

        self.assertEqual(pv1a.get(self.jtlid_name), 'jt-1')
        self.assertEqual(pv2.get(self.jtlid_name), 'jt-2a; jt-2b')
        self.assertEqual(pv3.get(self.jtlid_name), None)

        query_string["inventory_type"] = "taxlot"
        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(query_string)
        response = self.client.post(url)
        data = response.json()
        results = data['results']

        tlv1 = [t for t in results if t.get(self.jtlid_name) == 'jt-1'][0]
        tlv2a = [t for t in results if t.get(self.jtlid_name) == 'jt-2a'][0]
        tlv3 = [t for t in results if t.get(self.jtlid_name) == 'jt-3'][0]

        self.assertEqual(tlv1.get(self.pmpid_name), 'pm-1a; pm-1b')
        self.assertEqual(tlv2a.get(self.pmpid_name), 'pm-2')
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
        filter = { self.jtlid_name: self.get_filter("contains", "jt")}
        data = { "filters": filter }

        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(query_string)
        response = self.client.post(url, data=data, content_type='application/json')
        data = response.json()
        results = data['results']
        self.assertEqual(len(results), 4)
    
        filter = { self.jtlid_name: self.get_filter("contains", "2")}
        data = { "filters": filter }

        url = reverse("api:v4:tax_lot_properties-filter") + "?" + urlencode(query_string)
        response = self.client.post(url, data=data, content_type='application/json')
        data = response.json()
        results = data['results']
        self.assertEqual(len(results), 2)
    
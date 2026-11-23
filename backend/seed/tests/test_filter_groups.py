"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import UTC, date, datetime
from urllib.parse import urlencode

import pytest
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils.timezone import get_current_timezone

from seed.landing.models import SEEDUser as User
from seed.models import (
    VIEW_LIST_PROPERTY,
    VIEW_LIST_TAXLOT,
    Column,
    DerivedColumn,
    FilterGroup,
    PropertyState,
    PropertyView,
    StatusLabel,
    TaxLotState,
)
from seed.serializers.columns import ColumnSerializer
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeTaxLotPropertyFactory,
)
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization
from seed.utils.search import FilterError


class FilterGroupsTests(TransactionTestCase):
    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",  # the username needs to be in the form of an email.
            "password": "test_pass",
            "email": "test_user@demo.com",
            "first_name": "Jaqen",
            "last_name": "H'ghar",
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user, "test-organization-a")
        self.other_org, _, _ = create_organization(self.user, "test-organization-b")
        self.client.login(**user_details)

        self.status_label = StatusLabel.objects.create(name="test", super_organization=self.org)

        self.filter_group = FilterGroup.objects.create(
            name="test_filter_group",
            organization_id=self.org.id,
            inventory_type=1,  # Tax Lot
            query_dict={"year_built__lt": ["1950"]},
        )
        self.filter_group.and_labels.add(self.status_label.id)
        self.filter_group.save()

    def test_create_filter_group(self):
        # Action
        response = self.client.post(
            reverse("api:v3:filter_groups-list") + f"?organization_id={self.org.id}",
            data=json.dumps(
                {
                    "name": "new_filter_group",
                    "inventory_type": "Tax Lot",
                    "query_dict": {"year_built__lt": ["1950"]},
                    "exclude_labels": [self.status_label.id],
                }
            ),
            content_type="application/json",
        )

        # Assertion
        self.assertEqual(201, response.status_code)
        self.assertEqual(response.json()["status"], "success")

        data = response.json()["data"]
        self.assertIsInstance(data["id"], int)
        self.assertEqual("new_filter_group", data["name"])
        self.assertEqual(self.org.id, data["organization_id"])
        self.assertEqual("Tax Lot", data["inventory_type"])
        self.assertEqual({"year_built__lt": ["1950"]}, data["query_dict"])
        self.assertEqual([self.status_label.id], data["exclude_labels"])

    def test_create_filter_group_no_name(self):
        # Action
        response = self.client.post(
            reverse("api:v3:filter_groups-list") + f"?organization_id={self.org.id}",
            data=json.dumps(
                {
                    "inventory_type": "Tax Lot",
                    "query_dict": {"year_built__lt": ["1950"]},
                }
            ),
            content_type="application/json",
        )

        # Assertion
        self.assertEqual(400, response.status_code)

    def test_create_filter_group_bad_name(self):
        # Action
        response = self.client.post(
            reverse("api:v3:filter_groups-list") + f"?organization_id={self.org.id}",
            data=json.dumps(
                {
                    "name": self.filter_group.name,
                    "inventory_type": "Tax Lot",
                    "query_dict": {"year_built__lt": ["1950"]},
                }
            ),
            content_type="application/json",
        )

        # Assertion
        self.assertEqual(400, response.status_code)

    def test_create_filter_group_no_inventory_type(self):
        # Action
        response = self.client.post(
            reverse("api:v3:filter_groups-list") + f"?organization_id={self.org.id}",
            data=json.dumps(
                {
                    "name": "new_filter_group",
                    "query_dict": {"year_built__lt": ["1950"]},
                }
            ),
            content_type="application/json",
        )

        # Assertion
        self.assertEqual(400, response.status_code)

    def test_create_filter_group_bad_inventory_type(self):
        # Action
        response = self.client.post(
            reverse("api:v3:filter_groups-list") + f"?organization_id={self.org.id}",
            data=json.dumps(
                {
                    "name": "new_filter_group",
                    "inventory_type": "bad inventory type",
                    "query_dict": {"year_built__lt": ["1950"]},
                }
            ),
            content_type="application/json",
        )

        # Assertion
        self.assertEqual(400, response.status_code)

    def test_create_filter_group_label_doesnt_exist(self):
        # Action
        response = self.client.post(
            reverse("api:v3:filter_groups-list") + f"?organization_id={self.org.id}",
            data=json.dumps({"name": "new_filter_group", "inventory_type": "Tax Lot", "and_labels": [-1, -2, self.status_label.id]}),
            content_type="application/json",
        )

        # Assertion
        self.assertEqual(201, response.status_code)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["warnings"], "labels with ids do not exist: -1, -2")

        data = response.json()["data"]
        self.assertEqual([self.status_label.id], data["and_labels"])

    def test_filter_group_rejects_other_organization_labels(self):
        other_label = StatusLabel.objects.create(name="other", super_organization=self.other_org)

        # Create: the other organization's label is ignored with a warning
        response = self.client.post(
            reverse("api:v3:filter_groups-list") + f"?organization_id={self.org.id}",
            data=json.dumps(
                {"name": "new_filter_group", "inventory_type": "Tax Lot", "and_labels": [other_label.id, self.status_label.id]}
            ),
            content_type="application/json",
        )
        self.assertEqual(201, response.status_code)
        self.assertEqual(response.json()["warnings"], f"labels with ids do not exist: {other_label.id}")
        self.assertEqual([self.status_label.id], response.json()["data"]["and_labels"])

        # Update: the other organization's label is rejected
        url = reverse("api:v3:filter_groups-detail", args=[self.filter_group.id]) + f"?organization_id={self.org.id}"
        response = self.client.put(url, data=json.dumps({"or_labels": [other_label.id]}), content_type="application/json")
        self.assertEqual(400, response.status_code)
        self.assertEqual([self.status_label.id], list(self.filter_group.and_labels.values_list("id", flat=True)))
        self.assertFalse(self.filter_group.or_labels.exists())

        # The organization's own labels are still accepted
        response = self.client.put(url, data=json.dumps({"or_labels": [self.status_label.id]}), content_type="application/json")
        self.assertEqual(200, response.status_code)
        self.assertEqual([self.status_label.id], response.json()["data"]["or_labels"])

    def test_get_filter_group(self):
        # Action
        response = self.client.get(
            reverse("api:v3:filter_groups-detail", args=[self.filter_group.id]) + f"?organization_id={self.org.id}",
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "status": "success",
                "data": {
                    "id": self.filter_group.id,
                    "name": "test_filter_group",
                    "organization_id": self.org.id,
                    "inventory_type": "Tax Lot",
                    "query_dict": {"year_built__lt": ["1950"]},
                    "and_labels": [self.status_label.id],
                    "or_labels": [],
                    "exclude_labels": [],
                },
            },
            response.json(),
        )

    def test_get_all_filter_group(self):
        # Setup
        # second, as self.filter_group is the first
        second_filter_group = FilterGroup.objects.create(
            name="second_test_filter_group",
            organization_id=self.org.id,
            inventory_type=1,  # Taxlot
            query_dict={"year_built__lt": ["1950"]},
        )

        # wrong org, shouldn't show up
        FilterGroup.objects.create(
            name="wrong org",
            organization_id=self.other_org.id,
            inventory_type=1,  # Taxlot
            query_dict={"year_built__lt": ["1950"]},
        )

        # wrong inventory type, shouldn't show up
        FilterGroup.objects.create(
            name="wrong inventory type",
            organization_id=self.org.id,
            inventory_type=0,  # Property
            query_dict={"year_built__lt": ["1950"]},
        )

        # Action
        response = self.client.get(
            reverse("api:v3:filter_groups-list") + "?inventory_type=Tax Lot" + f"&organization_id={self.org.id}",
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "data": [
                    {
                        "id": self.filter_group.id,
                        "inventory_type": "Tax Lot",
                        "name": "test_filter_group",
                        "organization_id": self.org.id,
                        "query_dict": {"year_built__lt": ["1950"]},
                        "and_labels": [self.status_label.id],
                        "or_labels": [],
                        "exclude_labels": [],
                    },
                    {
                        "id": second_filter_group.id,
                        "inventory_type": "Tax Lot",
                        "name": "second_test_filter_group",
                        "organization_id": self.org.id,
                        "query_dict": {"year_built__lt": ["1950"]},
                        "and_labels": [],
                        "or_labels": [],
                        "exclude_labels": [],
                    },
                ],
                "pagination": {"end": 2, "has_next": False, "has_previous": False, "num_pages": 1, "page": 1, "start": 1, "total": 2},
                "status": "success",
            },
            response.json(),
        )

    def test_update_filter_group_name(self):
        # Action
        response = self.client.put(
            reverse("api:v3:filter_groups-detail", args=[self.filter_group.id]) + f"?organization_id={self.org.id}",
            data=json.dumps({"name": "new_name"}),
            content_type="application/json",
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "status": "success",
                "data": {
                    "id": self.filter_group.id,
                    "name": "new_name",
                    "organization_id": self.org.id,
                    "inventory_type": "Tax Lot",
                    "query_dict": {"year_built__lt": ["1950"]},
                    "and_labels": [self.status_label.id],
                    "or_labels": [],
                    "exclude_labels": [],
                },
            },
            response.json(),
        )

    def test_update_filter_group_labels(self):
        # Setup
        first_label = StatusLabel.objects.create(name="1", super_organization=self.org)
        second_label = StatusLabel.objects.create(name="2", super_organization=self.org)

        # Action
        response = self.client.put(
            reverse("api:v3:filter_groups-detail", args=[self.filter_group.id]) + f"?organization_id={self.org.id}",
            data=json.dumps(
                {
                    "and_labels": [first_label.id, second_label.id],
                }
            ),
            content_type="application/json",
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "status": "success",
                "data": {
                    "id": self.filter_group.id,
                    "name": "test_filter_group",
                    "organization_id": self.org.id,
                    "inventory_type": "Tax Lot",
                    "query_dict": {"year_built__lt": ["1950"]},
                    "and_labels": [first_label.id, second_label.id],
                    "or_labels": [],
                    "exclude_labels": [],
                },
            },
            response.json(),
        )

        # Action
        response = self.client.put(
            reverse("api:v3:filter_groups-detail", args=[self.filter_group.id]) + f"?organization_id={self.org.id}",
            data=json.dumps({"or_labels": [first_label.id], "exclude_labels": [second_label.id]}),
            content_type="application/json",
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "status": "success",
                "data": {
                    "id": self.filter_group.id,
                    "name": "test_filter_group",
                    "organization_id": self.org.id,
                    "inventory_type": "Tax Lot",
                    "query_dict": {"year_built__lt": ["1950"]},
                    "and_labels": [],
                    "or_labels": [first_label.id],
                    "exclude_labels": [second_label.id],
                },
            },
            response.json(),
        )

    def test_update_filter_group_bad_labels(self):
        # Setup
        first_label = StatusLabel.objects.create(name="1", super_organization=self.org)

        # Action
        response = self.client.put(
            reverse("api:v3:filter_groups-detail", args=[self.filter_group.id]) + f"?organization_id={self.org.id}",
            data=json.dumps(
                {
                    "and_labels": [first_label.id, -1],
                    "or_labels": [first_label.id, -1],
                }
            ),
            content_type="application/json",
        )

        # Assertion
        self.assertEqual(400, response.status_code)

        # Action
        response = self.client.get(
            reverse("api:v3:filter_groups-detail", args=[self.filter_group.id]) + f"?organization_id={self.org.id}",
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "status": "success",
                "data": {
                    "id": self.filter_group.id,
                    "name": "test_filter_group",
                    "organization_id": self.org.id,
                    "inventory_type": "Tax Lot",
                    "query_dict": {"year_built__lt": ["1950"]},
                    "and_labels": [self.status_label.id],
                    "or_labels": [],
                    "exclude_labels": [],
                },
            },
            response.json(),
        )

    def test_delete_filter_group(self):
        # Setup
        filter_group = FilterGroup.objects.create(
            name="new_filter_group",
            organization_id=self.org.id,
            inventory_type=1,  # Tax Lot
            query_dict={"year_built__lt": ["1950"]},
        )

        filter_group_id = filter_group.id

        # Action
        response = self.client.delete(
            reverse("api:v3:filter_groups-detail", args=[filter_group_id]) + f"?organization_id={self.org.id}",
        )

        # Assertion
        self.assertEqual(204, response.status_code)
        result = FilterGroup.objects.filter(id=filter_group_id)
        self.assertFalse(result.exists())

    def test_delete_filter_group_does_not_exist(self):
        # Action
        response = self.client.delete(
            reverse("api:v3:filter_groups-detail", args=["not_a_valid_id"]) + f"?organization_id={self.org.id}",
        )

        # Assertion
        self.assertEqual(404, response.status_code)


class FilterGroupsPermissionsTests(AccessLevelBaseTestCase, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.filter_group = FilterGroup.objects.create(
            name="test_filter_group",
            organization_id=self.org.id,
            inventory_type=1,  # Tax Lot
            query_dict={"year_built__lt": ["1950"]},
        )
        self.status_label = StatusLabel.objects.create(name="test", super_organization=self.org)

    def test_filter_group_delete(self):
        url = reverse("api:v3:filter_groups-detail", args=[self.filter_group.id]) + f"?organization_id={self.org.id}"

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403

        # root user can
        self.login_as_root_member()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204

    def test_filter_group_create(self):
        url = reverse("api:v3:filter_groups-list") + f"?organization_id={self.org.id}"
        post_params = json.dumps(
            {
                "name": "new_filter_group",
                "inventory_type": "Tax Lot",
                "query_dict": {"year_built__lt": ["1950"]},
                "label_logic": "exclude",
                "labels": [self.status_label.id],
            }
        )

        # root user can
        self.login_as_root_member()
        response = self.client.post(url, post_params, content_type="application/json")
        assert response.status_code == 201

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, post_params, content_type="application/json")
        assert response.status_code == 403

    def test_filter_group_update(self):
        url = reverse("api:v3:filter_groups-detail", args=[self.filter_group.id]) + f"?organization_id={self.org.id}"
        params = json.dumps({"name": "new_name"})

        # root user can
        self.login_as_root_member()
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 200

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 403

    def test_filter_group_update_other_organization(self):
        other_org, _, _ = create_organization(self.superuser, "other-org")
        other_filter_group = FilterGroup.objects.create(name="other_filter_group", organization_id=other_org.id, inventory_type=1)
        url = reverse("api:v3:filter_groups-detail", args=[other_filter_group.id]) + f"?organization_id={self.org.id}"

        self.login_as_root_member()
        response = self.client.put(url, json.dumps({"name": "new_name"}), content_type="application/json")
        assert response.status_code == 404
        other_filter_group.refresh_from_db()
        assert other_filter_group.name == "other_filter_group"


class FilterGroupsViewTests(AccessLevelBaseTestCase, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.cycle1 = FakeCycleFactory(organization=self.org, user=self.superuser).get_cycle(
            name="Cycle A", end=datetime(2022, 1, 1, tzinfo=UTC)
        )

        # generate columns
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)

        # generate two different types of properties
        self.office1 = self.property_factory.get_property(access_level_instance=self.child_level_instance)
        self.office2 = self.property_factory.get_property(access_level_instance=self.root_level_instance)

        # generate property states that are either 'Office' or 'Retail' for filter groups
        # generate property views that are attached to a property and a property-state
        self.state10 = self.property_state_factory.get_property_state(property_name="state10", property_type="office", site_eui=0)
        self.state11 = self.property_state_factory.get_property_state(property_name="state11", property_type="office", site_eui=12)

        self.view10 = PropertyView.objects.create(property=self.office1, cycle=self.cycle1, state=self.state10)
        self.view11 = PropertyView.objects.create(property=self.office2, cycle=self.cycle1, state=self.state11)

        property_type_id = Column.objects.get(table_name="PropertyState", column_name="property_type", organization_id=self.org.id).id
        self.office_filter_group = FilterGroup.objects.create(
            name="office",
            organization_id=self.org.id,
            inventory_type=0,  # Property
            query_dict={f"property_type_{property_type_id}__exact": "office"},
        )
        self.office_filter_group.save()

    def test_filter_returns_all_views_without_ali(self):
        base_views = PropertyView.objects.select_related("property", "state").filter(property__organization_id=self.org.id)
        pv = self.office_filter_group.views(base_views)

        self.assertEqual(len(pv), 2)

    def test_filter_with_child_ali_returns_only_child_property_views(self):
        self.office_filter_group.query_dict["child__icontains"] = "child"
        base_views = PropertyView.objects.select_related("property", "state").filter(property__organization_id=self.org.id)
        pv = self.office_filter_group.views(base_views)

        self.assertEqual(len(pv), 1)


def text(filter_type, value=None):
    return {"filterType": "text", "type": filter_type, **({"filter": value} if value is not None else {})}


def number(filter_type, value=None, value_to=None):
    return {"filterType": "number", "type": filter_type, "filter": value, "filterTo": value_to}


def date_filter(filter_type, date_from=None, date_to=None):
    # As AG Grid's date filter sends them
    date_from, date_to = (d and f"{d} 00:00:00" for d in (date_from, date_to))
    return {"filterType": "date", "type": filter_type, "dateFrom": date_from, "dateTo": date_to}


class FilterGroupGridFilterTests(AccessLevelBaseTestCase):
    """Filter groups saved by the inventory grid (as AG Grid filter models) match the properties that the grid shows"""

    def setUp(self):
        super().setUp()
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2001, 1, 1, tzinfo=UTC), end=datetime(2002, 1, 1, tzinfo=UTC))
        Column.objects.create(table_name="PropertyState", column_name="extra_eui", organization=self.org, is_extra_data=True)
        derived_column = DerivedColumn.objects.create(
            name="Derived EUI", expression="$a / 2", organization=self.org, inventory_type=DerivedColumn.PROPERTY_TYPE
        )

        self.views_by_index = {}
        for i in range(20):
            access_level_instance = self.child_level_instance if i >= 15 else self.root_level_instance
            self.views_by_index[i] = self.property_view_factory.get_property_view(
                prprty=self.property_factory.get_property(access_level_instance=access_level_instance),
                cycle=self.cycle,
                pm_property_id=f"pm-{i}",
                address_line_1=f"address{i}" if i % 2 else "",  # evens blank
                gross_floor_area=1000 + i,
                site_eui=50 + i if i % 3 else None,  # 0, 3, 6, ... null
                year_ending=date(2001 + i % 4, 12, 31) if i < 16 else None,  # 4 each in 2001-2004, 16-19 null
                recent_sale_date=datetime(2020, 6, 1 + i % 2, 12, tzinfo=get_current_timezone()) if i < 10 else None,
                extra_data={"extra_eui": 100 + i},
            )
            # 0, 2, ... 8 have values, 1, 3, ... 9 can't be computed (null), and 10-19 are missing
            if i < 10:
                PropertyState.objects.filter(propertyview=self.views_by_index[i]).update(
                    derived_data={derived_column.name: i * 10 if i % 2 == 0 else None}
                )

        # pm-0 and pm-1 share a tax lot, and pm-2 has two
        taxlot_property_factory = FakeTaxLotPropertyFactory(organization=self.org, user=self.superuser)
        taxlot_views = {
            jurisdiction_tax_lot_id: self.taxlot_view_factory.get_taxlot_view(
                cycle=self.cycle, jurisdiction_tax_lot_id=jurisdiction_tax_lot_id
            )
            for jurisdiction_tax_lot_id in ["jt-1", "jt-2a", "jt-2b"]
        }
        for i, jurisdiction_tax_lot_id in [(0, "jt-1"), (1, "jt-1"), (2, "jt-2a"), (2, "jt-2b")]:
            taxlot_property_factory.get_taxlot_property(
                cycle=self.cycle, property_view=self.views_by_index[i], taxlot_view=taxlot_views[jurisdiction_tax_lot_id]
            )
        self.taxlot_views = taxlot_views

        # 3 and 4 have both labels
        self.label_a = StatusLabel.objects.create(name="a", super_organization=self.org)
        self.label_b = StatusLabel.objects.create(name="b", super_organization=self.org)
        for i in range(8):
            self.views_by_index[i].labels.add(*([self.label_a] if i < 5 else []), *([self.label_b] if i > 2 else []))

        def name(column_name, table_name="PropertyState"):
            column = Column.objects.get(organization=self.org, table_name=table_name, column_name=column_name)
            return ColumnSerializer(column).data["name"]

        self.pm_property_id = name("pm_property_id")
        self.address_line_1 = name("address_line_1")
        self.gross_floor_area = name("gross_floor_area")
        self.site_eui = name("site_eui")
        self.year_ending = name("year_ending")
        self.recent_sale_date = name("recent_sale_date")
        self.extra_eui = name("extra_eui")
        self.derived_eui = ColumnSerializer(derived_column.column).data["name"]
        self.jurisdiction_tax_lot_id = name("jurisdiction_tax_lot_id", "TaxLotState")
        self.taxlot_address_line_1 = name("address_line_1", "TaxLotState")

    def filter_group(self, query_dict, inventory_type=VIEW_LIST_PROPERTY, **labels):
        filter_group = FilterGroup.objects.create(
            name=f"group {FilterGroup.objects.count()}", organization=self.org, inventory_type=inventory_type, query_dict=query_dict
        )
        for field, label_list in labels.items():
            getattr(filter_group, field).set(label_list)
        return filter_group

    def group_ids(self, query_dict, **labels):
        """The IDs of the cycle's property views that a filter group matches, unsorted to show any repeats"""
        views = PropertyView.objects.filter(property__organization=self.org, cycle=self.cycle)
        return [view.id for view in self.filter_group(query_dict, **labels).views(views)]

    def post_grid_filters(self, filters):
        query_string = urlencode({"cycle": self.cycle.id, "ids_only": True, "inventory_type": "property", "organization_id": self.org.id})
        url = reverse("api:v4:tax_lot_properties-filter") + "?" + query_string
        return self.client.post(url, data={"filters": filters}, content_type="application/json")

    def grid_ids(self, filters):
        """The IDs of the property views that the inventory grid shows with the filters"""
        response = self.post_grid_filters(filters)
        self.assertEqual(response.status_code, 200)
        return sorted(response.json()["results"])

    def ids(self, indexes):
        return sorted(self.views_by_index[i].id for i in indexes)

    def assert_matches(self, filters, indexes):
        """A filter group with the grid's filters matches the properties at the indexes once each, as the grid does"""
        expected = self.ids(indexes)
        self.assertEqual(sorted(self.group_ids(filters)), expected)
        self.assertEqual(self.grid_ids(filters), expected)

    def test_text_filters(self):
        self.assert_matches({self.pm_property_id: text("contains", "1")}, [1, *range(10, 20)])
        self.assert_matches({self.pm_property_id: text("notContains", "1")}, [0, *range(2, 10)])
        self.assert_matches({self.pm_property_id: text("equals", "pm-3")}, [3])
        self.assert_matches({self.pm_property_id: text("notEqual", "pm-3")}, [i for i in range(20) if i != 3])
        self.assert_matches({self.pm_property_id: text("startsWith", "PM-1")}, [1, *range(10, 20)])
        self.assert_matches({self.pm_property_id: text("endsWith", "5")}, [5, 15])
        self.assert_matches(
            {self.pm_property_id: text("startsWith", "pm-1"), self.address_line_1: text("contains", "address")}, [1, 11, 13, 15, 17, 19]
        )

    def test_number_filters(self):
        self.assert_matches({self.gross_floor_area: number("greaterThan", 1015)}, range(16, 20))
        self.assert_matches({self.gross_floor_area: number("greaterThanOrEqual", 1015)}, range(15, 20))
        self.assert_matches({self.gross_floor_area: number("lessThanOrEqual", 1002)}, range(3))
        self.assert_matches({self.gross_floor_area: number("equals", 1004)}, [4])
        # AG Grid's ranges exclude their ends
        self.assert_matches({self.gross_floor_area: number("inRange", 1005, 1010)}, range(6, 10))

    def test_date_filters(self):
        self.assert_matches({self.year_ending: date_filter("equals", "2002-12-31")}, [1, 5, 9, 13])
        self.assert_matches({self.year_ending: date_filter("greaterThan", "2002-12-31")}, [2, 3, 6, 7, 10, 11, 14, 15])
        self.assert_matches({self.year_ending: date_filter("inRange", "2001-12-31", "2004-12-31")}, [1, 2, 5, 6, 9, 10, 13, 14])
        # Date times compare by second, as the grid does (these are at noon)
        self.assert_matches({self.recent_sale_date: date_filter("lessThan", "2020-06-02")}, range(0, 10, 2))

    def test_blank_filters(self):
        self.assert_matches({self.address_line_1: text("blank")}, range(0, 20, 2))
        self.assert_matches({self.address_line_1: text("notBlank")}, range(1, 20, 2))
        # AG Grid infers text filters for columns whose first values are null
        for filter_type in ["text", "number"]:
            self.assert_matches({self.site_eui: {"filterType": filter_type, "type": "blank"}}, range(0, 20, 3))
            self.assert_matches({self.site_eui: {"filterType": filter_type, "type": "notBlank"}}, [i for i in range(20) if i % 3])
        self.assert_matches({self.year_ending: date_filter("blank")}, range(16, 20))
        self.assert_matches({self.year_ending: date_filter("notBlank")}, range(16))

    def test_conditions(self):
        either = {"filterType": "text", "operator": "OR", "conditions": [text("equals", "pm-1"), text("equals", "pm-2")]}
        both = {"filterType": "number", "operator": "AND", "conditions": [number("greaterThan", 1005), number("lessThan", 1008)]}
        self.assert_matches({self.pm_property_id: either}, [1, 2])
        self.assert_matches({self.gross_floor_area: both}, [6, 7])
        self.assert_matches({self.pm_property_id: either, self.gross_floor_area: both}, [])

    def test_extra_data_and_derived_columns(self):
        self.assert_matches({self.extra_eui: number("greaterThan", 115)}, range(16, 20))
        self.assert_matches({self.extra_eui: text("contains", "11")}, range(10, 20))  # 110-119
        self.assert_matches({self.derived_eui: text("notBlank")}, range(0, 10, 2))
        self.assert_matches({self.derived_eui: number("blank")}, [*range(1, 10, 2), *range(10, 20)])
        self.assert_matches({self.derived_eui: number("greaterThan", 40)}, [6, 8])

    def test_related_columns(self):
        self.assert_matches({self.jurisdiction_tax_lot_id: text("contains", "jt")}, [0, 1, 2])
        # pm-2's two tax lots match, but it is returned once
        self.assert_matches({self.jurisdiction_tax_lot_id: text("startsWith", "jt-2")}, [2])

    def test_access_level_filters(self):
        self.assert_matches({"child": text("contains", "chi")}, range(15, 20))
        self.assert_matches({"child": text("blank")}, range(15))
        either = {"filterType": "text", "operator": "OR", "conditions": [text("equals", "CHILD"), text("blank")]}
        self.assert_matches({"child": either}, range(20))

    def test_unknown_columns_are_ignored(self):
        self.assert_matches({"deleted_column_999999999": text("notBlank")}, range(20))

    def test_legacy_and_mixed_filters(self):
        # Filter groups saved by the legacy UI
        self.assertEqual(sorted(self.group_ids({f"{self.pm_property_id}__icontains": "1"})), self.ids([1, *range(10, 20)]))
        self.assertEqual(sorted(self.group_ids({f"{self.gross_floor_area}__gt": "1015"})), self.ids(range(16, 20)))
        self.assertEqual(sorted(self.group_ids({"child__icontains": "child"})), self.ids(range(15, 20)))

        # and both formats
        mixed = {f"{self.pm_property_id}__icontains": "1", self.gross_floor_area: number("lessThan", 1012)}
        self.assertEqual(sorted(self.group_ids(mixed)), self.ids([1, 10, 11]))

    def test_legacy_related_filters(self):
        # As in the legacy inventory list, a property matches legacy filters on tax lot columns if one of its tax lots
        # matches them all (pm-0 and pm-1 share jt-1, pm-2 has jt-2a and jt-2b, and the others have none)
        def update_taxlot(jurisdiction_tax_lot_id, **fields):
            TaxLotState.objects.filter(organization=self.org, jurisdiction_tax_lot_id=jurisdiction_tax_lot_id).update(**fields)

        def assert_group_matches(query_dict, indexes):
            self.assertEqual(sorted(self.group_ids(query_dict)), self.ids(indexes))

        update_taxlot("jt-1", address_line_1="1 Main St", extra_data={"extra_eui": 5})
        update_taxlot("jt-2a", address_line_1="2 Main St", extra_data={"extra_eui": 50})
        update_taxlot("jt-2b", address_line_1=None)
        jtlid, address = self.jurisdiction_tax_lot_id, self.taxlot_address_line_1

        assert_group_matches({f"{jtlid}__icontains": "jt-2"}, [2])
        assert_group_matches({f"{self.pm_property_id}__icontains": "1", f"{address}__icontains": "main"}, [1])
        assert_group_matches({f"{jtlid}__exact": "jt-2a", f"{address}__icontains": "2 main"}, [2])
        assert_group_matches({f"{jtlid}__exact": "jt-2b", f"{address}__icontains": "main"}, [])
        assert_group_matches({f"{jtlid}__icontains": "jt,2b"}, [2])
        assert_group_matches({f"{jtlid}__icontains": "2a,2b"}, [])
        assert_group_matches({f"{jtlid}__ne": "jt-1"}, [2])

        # Blanks match properties without tax lots too, but the property's own blanks don't
        assert_group_matches({f"{address}__exact": ""}, [2, *range(3, 20)])
        assert_group_matches({f"{address}__ne": ""}, [0, 1, 2])
        assert_group_matches({f"{self.address_line_1}__exact": "", f"{jtlid}__icontains": "jt"}, [0, 2])

        # Tax lot extra data and derived columns, even named as the property's
        extra_eui = Column.objects.create(
            table_name="TaxLotState", column_name="extra_eui", organization=self.org, is_extra_data=True, data_type="number"
        )
        extra_eui = ColumnSerializer(extra_eui).data["name"]
        derived_column = DerivedColumn.objects.create(
            name="Lot EUI", expression="$a / 2", organization=self.org, inventory_type=DerivedColumn.TAXLOT_TYPE
        )
        update_taxlot("jt-2b", derived_data={derived_column.name: 7})
        assert_group_matches({f"{extra_eui}__lt": "10"}, [0, 1])
        assert_group_matches({f"{self.extra_eui}__icontains": "10", f"{extra_eui}__gt": "10"}, [2])
        assert_group_matches({f"{ColumnSerializer(derived_column.column).data['name']}__gt": "1"}, [2])

        # and with the grid's filters, whose conditions can each match a different tax lot
        assert_group_matches({f"{jtlid}__icontains": "jt", self.pm_property_id: text("contains", "1")}, [1])
        assert_group_matches({f"{jtlid}__exact": "jt-2b", address: text("contains", "main")}, [2])

    def test_labels(self):
        # 3 and 4 have both OR labels, but are returned once
        self.assertEqual(sorted(self.group_ids({}, or_labels=[self.label_a, self.label_b])), self.ids(range(8)))
        self.assertEqual(sorted(self.group_ids({}, and_labels=[self.label_a, self.label_b])), self.ids([3, 4]))
        self.assertEqual(sorted(self.group_ids({}, exclude_labels=[self.label_a])), self.ids(range(5, 20)))

        either = {self.pm_property_id: text("contains", "4")}
        self.assertEqual(sorted(self.group_ids(either, or_labels=[self.label_a, self.label_b])), self.ids([4]))

    def test_invalid_filters(self):
        pm_property_id = self.pm_property_id
        invalid_filters = [
            {pm_property_id: text("unknownType", "pm")},
            {pm_property_id: {"filterType": "text"}},
            {pm_property_id: {"filterType": "text", "operator": "XOR", "conditions": [text("equals", "pm-1")]}},
            # Values that aren't a number or a date, and comparisons text filters don't make
            {self.gross_floor_area: number("equals", "abc")},
            {self.year_ending: date_filter("equals", "not a date")},
            {pm_property_id: text("greaterThan", "pm")},
            # Malformed, e.g., in a filter group made with the API
            {pm_property_id: text(["equals"], "pm-1")},
            {pm_property_id: text("equals", {"value": "pm-1"})},
            {pm_property_id: {"filterType": ["text"], "type": "equals", "filter": "pm-1"}},
            {pm_property_id: {"filterType": "text", "operator": ["OR"], "conditions": [text("equals", "pm-1")]}},
            {pm_property_id: {"filterType": "text", "operator": "OR", "conditions": "pm-1"}},
            {pm_property_id: {"filterType": "text", "operator": "OR", "conditions": ["pm-1"]}},
            {"child": text(["contains"], "child")},
        ]
        for filters in invalid_filters:
            with self.subTest(filters=filters):
                with pytest.raises(FilterError):
                    self.group_ids(filters)
                self.assertEqual(self.post_grid_filters(filters).status_code, 400)

        with pytest.raises(FilterError):
            self.group_ids([pm_property_id])
        # Text filters on other columns compare their values as text
        self.assert_matches({self.gross_floor_area: text("equals", "abc")}, [])
        for filters in [[pm_property_id]]:
            self.assertEqual(self.post_grid_filters(filters).status_code, 400)

    def test_tax_lot_filter_groups(self):
        def group_ids(filters, views=None):
            return sorted(view.id for view in self.filter_group(filters, inventory_type=VIEW_LIST_TAXLOT).views(views))

        jt_2 = {self.jurisdiction_tax_lot_id: text("startsWith", "jt-2")}
        not_jt_2 = {self.jurisdiction_tax_lot_id: text("notContains", "jt-2")}
        blank = {self.jurisdiction_tax_lot_id: text("blank")}

        # Of all the organization's tax lots, by default
        self.assertEqual(group_ids(jt_2), sorted([self.taxlot_views["jt-2a"].id, self.taxlot_views["jt-2b"].id]))

        # or the properties of the matching tax lots, e.g., in a property report, but not those without tax lots
        views = PropertyView.objects.filter(property__organization=self.org, cycle=self.cycle)
        self.assertEqual(group_ids(jt_2, views), self.ids([2]))
        self.assertEqual(group_ids(not_jt_2, views), self.ids([0, 1]))
        self.assertEqual(group_ids(blank, views), [])

        # Legacy filters on property columns match tax lots with a property that matches them all
        self.assertEqual(group_ids({f"{self.pm_property_id}__exact": "pm-2"}), group_ids(jt_2))
        not_pm_2 = {f"{self.pm_property_id}__ne": "pm-2", f"{self.address_line_1}__ne": ""}  # pm-1
        self.assertEqual(group_ids(not_pm_2), [self.taxlot_views["jt-1"].id])
        # jt-1's pm-0 has a blank address, and its pm-1 isn't pm-0
        self.assertEqual(group_ids({f"{self.pm_property_id}__exact": "pm-0", f"{self.address_line_1}__ne": ""}), [])
        # pm-0's tax lot is pm-1's too
        self.assertEqual(group_ids({f"{self.gross_floor_area}__lt": "1001"}, views), self.ids([0, 1]))

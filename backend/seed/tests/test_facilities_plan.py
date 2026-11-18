"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author nicholas.long@nlr.gov
"""

import json
from contextlib import closing
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.lib.tkbl.tkbl import EISA432_CODES
from seed.models import Column, Cycle, FacilitiesPlan, FacilitiesPlanRun, PropertyView, Uniformat
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakeElementFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class BaseFacilitiesPlanTests(TestCase):
    def setUp(self):
        # login
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        self.user = User.objects.create_superuser(email="test_user@demo.com", **user_details)
        self.org, _, _ = create_organization(self.user)
        self.client.login(**user_details)

        # create FacilitiesPlan
        col_args = {"table_name": "PropertyState", "organization": self.org, "is_extra_data": True}
        self.electric_energy_usage_column = Column.objects.create(
            column_name="electric_energy_usage_column", data_type="number", **col_args
        )
        self.gas_energy_usage_column = Column.objects.create(column_name="gas_energy_usage_column", data_type="number", **col_args)
        self.steam_energy_usage_column = Column.objects.create(column_name="steam_energy_usage_column", data_type="number", **col_args)
        self.include_in_total_denominator_column = Column.objects.create(column_name="include_in_total_denominator_column", **col_args)
        self.require_in_plan_column = Column.objects.create(column_name="require_in_plan_column", **col_args)
        self.exclude_from_plan_column = Column.objects.create(column_name="exclude_from_plan_column", **col_args)
        self.facilities_plan = FacilitiesPlan.objects.create(
            organization=self.org,
            name="test",
            electric_energy_usage_column=self.electric_energy_usage_column,
            gas_energy_usage_column=self.gas_energy_usage_column,
            steam_energy_usage_column=self.steam_energy_usage_column,
            include_in_total_denominator_column=self.include_in_total_denominator_column,
            require_in_plan_column=self.require_in_plan_column,
            exclude_from_plan_column=self.exclude_from_plan_column,
            energy_running_sum_percentage=0.60,
        )


class FacilitiesPlanAPITests(BaseFacilitiesPlanTests):
    def setUp(self):
        super().setUp()

    def test_list(self):
        response = self.client.get(
            reverse("api:v3:facilities_plans-list") + "?organization_id=" + str(self.org.id), content_type="application/json"
        )

        self.assertDictEqual(
            response.json(),
            {
                "status": "success",
                "data": [
                    {
                        "id": self.facilities_plan.id,
                        "organization": self.org.id,
                        "name": "test",
                        "energy_running_sum_percentage": 0.6,
                        "compliance_cycle_year_column": None,
                        "include_in_total_denominator_column": self.include_in_total_denominator_column.id,
                        "exclude_from_plan_column": self.exclude_from_plan_column.id,
                        "require_in_plan_column": self.require_in_plan_column.id,
                        "electric_energy_usage_column": self.electric_energy_usage_column.id,
                        "gas_energy_usage_column": self.gas_energy_usage_column.id,
                        "steam_energy_usage_column": self.steam_energy_usage_column.id,
                    }
                ],
            },
        )

    def test_retrieve(self):
        response = self.client.get(
            reverse("api:v3:facilities_plans-detail", args=[self.facilities_plan.id]) + "?organization_id=" + str(self.org.id),
            content_type="application/json",
        )

        self.assertDictEqual(
            response.json(),
            {
                "status": "success",
                "data": {
                    "id": self.facilities_plan.id,
                    "organization": self.org.id,
                    "name": "test",
                    "energy_running_sum_percentage": 0.6,
                    "compliance_cycle_year_column": None,
                    "include_in_total_denominator_column": self.include_in_total_denominator_column.id,
                    "exclude_from_plan_column": self.exclude_from_plan_column.id,
                    "require_in_plan_column": self.require_in_plan_column.id,
                    "electric_energy_usage_column": self.electric_energy_usage_column.id,
                    "gas_energy_usage_column": self.gas_energy_usage_column.id,
                    "steam_energy_usage_column": self.steam_energy_usage_column.id,
                },
            },
        )

    def test_create_and_update_reject_another_organization(self):
        other_org, _, _ = create_organization(self.user, "other org")
        url = reverse("api:v3:facilities_plans-list") + "?organization_id=" + str(self.org.id)
        detail_url = reverse("api:v3:facilities_plans-detail", args=[self.facilities_plan.id]) + "?organization_id=" + str(self.org.id)

        # cannot create a plan in, or move a plan to, another organization than the requested one
        response = self.client.post(url, data=json.dumps({"name": "other", "organization": other_org.id}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        response = self.client.put(
            detail_url, data=json.dumps({"name": "test", "organization": other_org.id}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(FacilitiesPlan.objects.filter(organization=other_org).exists())

        # cannot reference another organization's columns
        other_column = Column.objects.filter(organization=other_org).first()
        response = self.client.post(
            url,
            data=json.dumps({"name": "other", "organization": self.org.id, "electric_energy_usage_column": other_column.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FacilitiesPlan.objects.filter(organization=self.org).count(), 1)

        # can create and update within the requested organization
        response = self.client.post(url, data=json.dumps({"name": "other", "organization": self.org.id}), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        response = self.client.put(
            detail_url, data=json.dumps({"name": "renamed", "organization": self.org.id}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FacilitiesPlan.objects.get(pk=self.facilities_plan.id).name, "renamed")


class FacilitiesPlanRunAPITests(BaseFacilitiesPlanTests):
    def setUp(self):
        super().setUp()

        # create facilities_plan_run
        self.cycle = Cycle.objects.first()
        self.ali = AccessLevelInstance.objects.first()
        self.facilities_plan_run = FacilitiesPlanRun.objects.create(
            facilities_plan=self.facilities_plan,
            cycle=self.cycle,
            ali=self.ali,
            name="Test Facilities Plan Run",
        )

        self.property_view_factory = FakePropertyViewFactory(organization=self.org, user=self.user)

    def test_export_preserves_property_and_component_values(self):
        Column.objects.filter(organization=self.org, column_name="address_line_1", table_name="PropertyState").update(
            display_name="Site Address"
        )
        property_ = self.property_view_factory.property_factory.get_property()
        state = self.property_view_factory.state_factory.get_property_state(
            address_line_1="001 Test Street",
            gross_floor_area=2500,
            extra_data={
                "electric_energy_usage_column": 10,
                "gas_energy_usage_column": 0,
                "steam_energy_usage_column": 0,
                "include_in_total_denominator_column": True,
            },
        )
        # Distinct IDs prevent coincidentally aligned sequences from masking a bad join.
        view = PropertyView.objects.create(id=property_.id + 1, property=property_, cycle=self.cycle, state=state)
        code = Uniformat.objects.filter(code__in=EISA432_CODES).first()
        assert code is not None
        FakeElementFactory(organization=self.org).get_element(
            property=view.property,
            code=code,
            remaining_service_life=5.5,
            replacement_cost=1000,
            extra_data={"Component_SubType": "Heat pump", "CAPACITY_COOLING": 0},
        )
        self.facilities_plan_run.run()

        response = self.client.post(
            f"{reverse('api:v3:facilities_plan_runs-export', args=[self.facilities_plan_run.id])}?organization_id={self.org.id}",
            content_type="application/json",
        )

        assert response.status_code == 200
        with closing(load_workbook(BytesIO(response.content))) as workbook:
            assert workbook.sheetnames == ["How To Guide", "1. Facilities Plan", "2. Prioritized Bldg Components", "3. ECM Data Dictionary"]
            for sheet_name in ["1. Facilities Plan", "2. Prioritized Bldg Components"]:
                sheet = workbook[sheet_name]
                headers = [cell.value for cell in sheet[1]]
                row = dict(zip(headers, next(sheet.iter_rows(min_row=2, max_row=2, values_only=True)), strict=True))
                assert row["Site Address"] == "001 Test Street"

                if sheet_name == "1. Facilities Plan":
                    assert row["electric_energy_usage_column"] == 10
                    assert row["include_in_total_denominator_column"] is True
                    assert row["Total Energy Usage"] == 10
                else:
                    assert row["Uniformat Category"] == code.code
                    assert row["RSL"] == 5.5
                    assert row["Replacement Cost"] == 1000
                    assert row["Component_SubType"] == "Heat pump"
                    assert row["Capacity_cooling"] == 0
                    assert row["Capacity_heating"] is None

    def test_list(self):
        # Action
        response = self.client.get(
            reverse("api:v3:facilities_plan_runs-list") + "?organization_id=" + str(self.org.id), content_type="application/json"
        )
        data = response.json()["data"][0]

        # Assertion
        self.assertEqual(data["id"], self.facilities_plan_run.id)
        self.assertEqual(data["facilities_plan"], self.facilities_plan.id)
        self.assertEqual(data["cycle"], self.cycle.id)
        self.assertEqual(data["ali"], self.ali.id)
        self.assertEqual(data["name"], "Test Facilities Plan Run")
        self.assertListEqual(
            list(data["columns"].keys()),
            [
                "include_in_total_denominator_column",
                "exclude_from_plan_column",
                "require_in_plan_column",
                "electric_energy_usage_column",
                "gas_energy_usage_column",
                "steam_energy_usage_column",
            ],
        )
        self.assertListEqual(data["display_columns"], [])
        self.assertEqual(data["property_display_field"]["column_name"], "address_line_1")
        self.assertEqual(data["run_at"], None)

    def test_retrieve(self):
        # Action
        response = self.client.get(
            reverse("api:v3:facilities_plan_runs-detail", args=[self.facilities_plan_run.id]) + "?organization_id=" + str(self.org.id),
            content_type="application/json",
        )
        data = response.json()["data"]

        # Assertion
        self.assertEqual(data["id"], self.facilities_plan_run.id)
        self.assertEqual(data["facilities_plan"], self.facilities_plan.id)
        self.assertEqual(data["cycle"], self.cycle.id)
        self.assertEqual(data["ali"], self.ali.id)
        self.assertEqual(data["name"], "Test Facilities Plan Run")
        self.assertListEqual(
            list(data["columns"].keys()),
            [
                "include_in_total_denominator_column",
                "exclude_from_plan_column",
                "require_in_plan_column",
                "electric_energy_usage_column",
                "gas_energy_usage_column",
                "steam_energy_usage_column",
            ],
        )
        self.assertListEqual(data["display_columns"], [])
        self.assertEqual(data["property_display_field"]["column_name"], "address_line_1")
        self.assertEqual(data["run_at"], None)

    def test_get_properties(self):
        # Setup
        PropertyView.objects.all().delete()
        for e in [10, 20, 30, 40]:
            self.property_view_factory.get_property_view(
                cycle=self.cycle,
                extra_data={
                    "electric_energy_usage_column": e,
                    "gas_energy_usage_column": 0,
                    "steam_energy_usage_column": 0,
                    "include_in_total_denominator_column": True,
                },
            )

        # Action
        response = self.client.get(
            reverse("api:v3:facilities_plan_runs-properties", args=[self.facilities_plan_run.id]) + "?organization_id=" + str(self.org.id),
            content_type="application/json",
        )
        properties = response.json()["properties"]

        # Assert
        self.assertEqual(len(properties), 4)

    def test_run(self):
        # Setup
        PropertyView.objects.all().delete()
        for e in [10, 20, 30, 40]:
            self.property_view_factory.get_property_view(
                cycle=self.cycle,
                extra_data={
                    "electric_energy_usage_column": e,
                    "gas_energy_usage_column": 0,
                    "steam_energy_usage_column": 0,
                    "include_in_total_denominator_column": True,
                },
            )
        self.assertEqual(len(self.facilities_plan_run.property_rankings.all()), 0)

        # Action
        response = self.client.post(
            reverse("api:v3:facilities_plan_runs-run", args=[self.facilities_plan_run.id]) + "?organization_id=" + str(self.org.id),
            content_type="application/json",
        )

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.facilities_plan_run.property_rankings.all()), 4)


class FacilitiesPlanRunTests(BaseFacilitiesPlanTests):
    def setUp(self):
        super().setUp()

        # create facilities_plan_run
        self.cycle = Cycle.objects.first()
        self.ali = AccessLevelInstance.objects.first()
        self.facilities_plan_run = FacilitiesPlanRun.objects.create(
            facilities_plan=self.facilities_plan,
            cycle=self.cycle,
            ali=self.ali,
            name="Test Facilities Plan Run",
        )

        self.property_view_factory = FakePropertyViewFactory(organization=self.org, user=self.user)

        self.maxDiff = None

    def test_run(self):
        # Setup
        PropertyView.objects.all().delete()
        properties = []
        for e in [10, 20, 30, 40]:
            properties.append(
                self.property_view_factory.get_property_view(
                    cycle=self.cycle,
                    extra_data={
                        "electric_energy_usage_column": e,
                        "gas_energy_usage_column": 0,
                        "steam_energy_usage_column": 0,
                        "include_in_total_denominator_column": True,
                    },
                )
            )

        # Action
        self.facilities_plan_run.run()

        # Assert
        self.assertListEqual(
            [
                {
                    "total_energy_usage": round(r.total_energy_usage, 2),
                    "percentage_of_total_energy_usage": round(r.percentage_of_total_energy_usage, 2),
                    "rank": round(r.rank, 2),
                    "running_percentage": round(r.running_percentage, 2),
                    "running_square_footage": round(r.running_square_footage, 2),
                }
                for r in self.facilities_plan_run.property_rankings.all()
            ],
            [
                {
                    "total_energy_usage": 40.0,
                    "percentage_of_total_energy_usage": 0.4,
                    "rank": 0,
                    "running_percentage": 0.4,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[3]])),
                },
                {
                    "total_energy_usage": 30.0,
                    "percentage_of_total_energy_usage": 0.3,
                    "rank": 1,
                    "running_percentage": 0.7,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[3], properties[2]])),
                },
                {
                    "total_energy_usage": 20.0,
                    "percentage_of_total_energy_usage": 0.2,
                    "rank": 2,
                    "running_percentage": 0.9,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[3], properties[2], properties[1]])),
                },
                {
                    "total_energy_usage": 10.0,
                    "percentage_of_total_energy_usage": 0.1,
                    "rank": 3,
                    "running_percentage": 1.0,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in properties)),
                },
            ],
        )

    def test_run_missing_columns(self):
        # Setup
        PropertyView.objects.all().delete()
        properties = []
        for e in [10, 20, 30, 40]:
            properties.append(
                self.property_view_factory.get_property_view(
                    cycle=self.cycle,
                    extra_data={
                        "electric_energy_usage_column": e,
                        "gas_energy_usage_column": None,
                        # "steam_energy_usage_column": 0,  # oh no! i'm missing
                        "include_in_total_denominator_column": True,
                    },
                )
            )

        # Action
        self.facilities_plan_run.run()

        # Assert
        self.assertListEqual(
            [
                {
                    "total_energy_usage": round(r.total_energy_usage, 2),
                    "percentage_of_total_energy_usage": round(r.percentage_of_total_energy_usage, 2),
                    "rank": round(r.rank, 2),
                    "running_percentage": round(r.running_percentage, 2),
                    "running_square_footage": round(r.running_square_footage, 2),
                }
                for r in self.facilities_plan_run.property_rankings.all()
            ],
            [
                {
                    "total_energy_usage": 40.0,
                    "percentage_of_total_energy_usage": 0.4,
                    "rank": 0,
                    "running_percentage": 0.4,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[3]])),
                },
                {
                    "total_energy_usage": 30.0,
                    "percentage_of_total_energy_usage": 0.3,
                    "rank": 1,
                    "running_percentage": 0.7,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[3], properties[2]])),
                },
                {
                    "total_energy_usage": 20.0,
                    "percentage_of_total_energy_usage": 0.2,
                    "rank": 2,
                    "running_percentage": 0.9,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[3], properties[2], properties[1]])),
                },
                {
                    "total_energy_usage": 10.0,
                    "percentage_of_total_energy_usage": 0.1,
                    "rank": 3,
                    "running_percentage": 1.0,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in properties)),
                },
            ],
        )

    def test_run_require_in_plan(self):
        # Setup
        PropertyView.objects.all().delete()
        properties = []
        for e in [10, 20, 30, 40]:
            properties.append(
                self.property_view_factory.get_property_view(
                    cycle=self.cycle,
                    extra_data={
                        "electric_energy_usage_column": e,
                        "gas_energy_usage_column": 0,
                        "steam_energy_usage_column": 0,
                        "include_in_total_denominator_column": True,
                    },
                )
            )

        # the first two properties must be included in the plan
        properties[0].state.extra_data["require_in_plan_column"] = True
        properties[0].state.save()
        properties[1].state.extra_data["require_in_plan_column"] = True
        properties[1].state.save()
        properties[2].state.extra_data["require_in_plan_column"] = False
        properties[2].state.save()

        # Action
        self.facilities_plan_run.run()

        # Assert
        self.assertListEqual(
            [
                {
                    "total_energy_usage": round(r.total_energy_usage, 2),
                    "percentage_of_total_energy_usage": round(r.percentage_of_total_energy_usage, 2),
                    "rank": round(r.rank, 2),
                    "running_percentage": round(r.running_percentage, 2),
                    "running_square_footage": round(r.running_square_footage, 2),
                }
                for r in self.facilities_plan_run.property_rankings.all()
            ],
            [
                {
                    "total_energy_usage": 20.0,
                    "percentage_of_total_energy_usage": 0.2,
                    "rank": 0,
                    "running_percentage": 0.2,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[1]])),
                },
                {
                    "total_energy_usage": 10.0,
                    "percentage_of_total_energy_usage": 0.1,
                    "rank": 1,
                    "running_percentage": 0.3,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[0], properties[1]])),
                },
                {
                    "total_energy_usage": 40.0,
                    "percentage_of_total_energy_usage": 0.4,
                    "rank": 2,
                    "running_percentage": 0.7,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[0], properties[1], properties[3]])),
                },
                {
                    "total_energy_usage": 30.0,
                    "percentage_of_total_energy_usage": 0.3,
                    "rank": 3,
                    "running_percentage": 1.0,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in properties)),
                },
            ],
        )

    def test_run_exclude_from_plan(self):
        # Setup
        PropertyView.objects.all().delete()
        properties = []
        for e in [10, 20, 30, 40]:
            properties.append(
                self.property_view_factory.get_property_view(
                    cycle=self.cycle,
                    extra_data={
                        "electric_energy_usage_column": e,
                        "gas_energy_usage_column": 0,
                        "steam_energy_usage_column": 0,
                        "include_in_total_denominator_column": True,
                    },
                )
            )

        # the first two properties must be included in the plan
        properties[2].state.extra_data["exclude_from_plan_column"] = True
        properties[2].state.save()
        properties[1].state.extra_data["exclude_from_plan_column"] = True
        properties[1].state.save()
        properties[0].state.extra_data["exclude_from_plan_column"] = False
        properties[0].state.save()

        # Action
        self.facilities_plan_run.run()

        # Assert
        self.assertListEqual(
            [
                {
                    "total_energy_usage": round(r.total_energy_usage, 2),
                    "percentage_of_total_energy_usage": round(r.percentage_of_total_energy_usage, 2),
                    "rank": round(r.rank, 2),
                    "running_percentage": round(r.running_percentage, 2),
                    "running_square_footage": round(r.running_square_footage, 2),
                }
                for r in self.facilities_plan_run.property_rankings.all()
            ],
            [
                {
                    "total_energy_usage": 40.0,
                    "percentage_of_total_energy_usage": 0.4,
                    "rank": 0,
                    "running_percentage": 0.4,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[3]])),
                },
                {
                    "total_energy_usage": 10.0,
                    "percentage_of_total_energy_usage": 0.1,
                    "rank": 1,
                    "running_percentage": 0.5,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[3], properties[0]])),
                },
                {
                    "total_energy_usage": 30.0,
                    "percentage_of_total_energy_usage": 0.3,
                    "rank": 2,
                    "running_percentage": 0.8,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[3], properties[0], properties[2]])),
                },
                {
                    "total_energy_usage": 20.0,
                    "percentage_of_total_energy_usage": 0.2,
                    "rank": 3,
                    "running_percentage": 1.0,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in properties)),
                },
            ],
        )

    def test_run_include_in_total_denominator_column(self):
        # Setup
        PropertyView.objects.all().delete()
        properties = []
        for e in [10, 20, 30, 40]:
            properties.append(
                self.property_view_factory.get_property_view(
                    cycle=self.cycle,
                    extra_data={
                        "electric_energy_usage_column": e,
                        "gas_energy_usage_column": 0,
                        "steam_energy_usage_column": 0,
                        "include_in_total_denominator_column": True,
                    },
                )
            )

        properties[3].state.extra_data["include_in_total_denominator_column"] = False
        properties[3].state.save()

        # Action
        self.facilities_plan_run.run()

        # Assert
        self.assertListEqual(
            [
                {
                    "total_energy_usage": round(r.total_energy_usage, 2),
                    "percentage_of_total_energy_usage": round(r.percentage_of_total_energy_usage, 2),
                    "rank": round(r.rank, 2),
                    "running_percentage": round(r.running_percentage, 2),
                    "running_square_footage": round(r.running_square_footage, 2),
                }
                for r in self.facilities_plan_run.property_rankings.all()
            ],
            [
                {
                    "total_energy_usage": 30.0,
                    "percentage_of_total_energy_usage": 0.5,
                    "rank": 0,
                    "running_percentage": 0.5,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[2]])),
                },
                {
                    "total_energy_usage": 20.0,
                    "percentage_of_total_energy_usage": 0.33,
                    "rank": 1,
                    "running_percentage": 0.83,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[2], properties[1]])),
                },
                {
                    "total_energy_usage": 10.0,
                    "percentage_of_total_energy_usage": 0.17,
                    "rank": 2,
                    "running_percentage": 1.0,
                    "running_square_footage": float(sum(p.state.gross_floor_area for p in [properties[2], properties[1], properties[0]])),
                },
            ],
        )


class FacilitiesPlanRunPermissionsTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.cycle = self.cycle_factory.get_cycle()
        self.facilities_plan = FacilitiesPlan.objects.create(organization=self.org, name="test")
        self.root_run = FacilitiesPlanRun.objects.create(
            facilities_plan=self.facilities_plan, cycle=self.cycle, ali=self.root_level_instance, name="root run"
        )

    def _payload(self, ali, **kwargs):
        return json.dumps(
            {"ali": ali.id, "facilities_plan": self.facilities_plan.id, "cycle": self.cycle.id, "display_columns": [], **kwargs}
        )

    def test_update_and_destroy_require_hierarchy_access(self):
        url = reverse("api:v3:facilities_plan_runs-detail", args=[self.root_run.id]) + "?organization_id=" + str(self.org.id)

        # child members cannot update or delete a run above their access level
        self.login_as_child_member()
        response = self.client.put(url, data=self._payload(self.child_level_instance, name="moved"), content_type="application/json")
        self.assertEqual(response.status_code, 404)
        response = self.client.delete(url, content_type="application/json")
        self.assertEqual(response.status_code, 404)
        self.root_run.refresh_from_db()
        self.assertEqual(self.root_run.name, "root run")
        self.assertEqual(self.root_run.ali, self.root_level_instance)

        # nor move their own run above their access level
        child_run = FacilitiesPlanRun.objects.create(facilities_plan=self.facilities_plan, cycle=self.cycle, ali=self.child_level_instance)
        child_url = reverse("api:v3:facilities_plan_runs-detail", args=[child_run.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.put(child_url, data=self._payload(self.root_level_instance), content_type="application/json")
        self.assertEqual(response.status_code, 404)
        child_run.refresh_from_db()
        self.assertEqual(child_run.ali, self.child_level_instance)

        # root members can
        self.login_as_root_member()
        response = self.client.put(url, data=self._payload(self.root_level_instance, name="renamed"), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.root_run.refresh_from_db()
        self.assertEqual(self.root_run.name, "renamed")
        response = self.client.delete(url, content_type="application/json")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(FacilitiesPlanRun.objects.filter(pk=self.root_run.id).exists())

    def test_create_and_update_reject_another_organizations_data(self):
        other_org, _, _ = create_organization(self.superuser, "other org")
        other_cycle = FakeCycleFactory(organization=other_org, user=self.superuser).get_cycle()
        other_plan = FacilitiesPlan.objects.create(organization=other_org, name="other")
        other_column = Column.objects.filter(organization=other_org).first()
        url = reverse("api:v3:facilities_plan_runs-list") + "?organization_id=" + str(self.org.id)
        detail_url = reverse("api:v3:facilities_plan_runs-detail", args=[self.root_run.id]) + "?organization_id=" + str(self.org.id)

        self.login_as_root_member()
        for payload in [
            self._payload(self.root_level_instance, cycle=other_cycle.id),
            self._payload(self.root_level_instance, facilities_plan=other_plan.id),
            self._payload(self.root_level_instance, display_columns=[other_column.id]),
        ]:
            response = self.client.post(url, data=payload, content_type="application/json")
            self.assertEqual(response.status_code, 400)
            response = self.client.put(detail_url, data=payload, content_type="application/json")
            self.assertEqual(response.status_code, 400)
        self.assertEqual(FacilitiesPlanRun.objects.count(), 1)
        self.root_run.refresh_from_db()
        self.assertEqual(self.root_run.cycle, self.cycle)
        self.assertEqual(self.root_run.facilities_plan, self.facilities_plan)

        # data from the requested organization is accepted
        response = self.client.post(url, data=self._payload(self.root_level_instance), content_type="application/json")
        self.assertEqual(response.status_code, 201)

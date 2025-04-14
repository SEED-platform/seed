"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author nicholas.long@nrel.gov
"""

from django.test import TestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import Column, Cycle, FacilitiesPlan, PropertyView
from seed.test_helpers.fake import (
    FakePropertyViewFactory,
)
from seed.utils.organizations import create_organization


class FacilitiesPlanTests(TestCase):
    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        self.user = User.objects.create_superuser(email="test_user@demo.com", **user_details)
        self.org, _, _ = create_organization(self.user)
        self.client.login(**user_details)

        self.cycle = Cycle.objects.first()
        self.ali = AccessLevelInstance.objects.first()

        col_args = {"table_name": "PropertyState", "organization": self.org, "is_extra_data": True}
        self.electric_energy_usage_column = Column.objects.create(
            column_name="electric_energy_usage_column", data_type="number", **col_args
        )
        self.gas_energy_usage_column = Column.objects.create(column_name="gas_energy_usage_column", data_type="number", **col_args)
        self.steam_energy_usage_column = Column.objects.create(column_name="steam_energy_usage_column", data_type="number", **col_args)
        self.include_in_total_denominator_column = Column.objects.create(column_name="include_in_total_denominator_column", **col_args)
        self.require_in_plan_column = Column.objects.create(column_name="require_in_plan_column", **col_args)
        self.facilities_plan = FacilitiesPlan.objects.create(
            organization=self.org,
            name="test",
            electric_energy_usage_column=self.electric_energy_usage_column,
            gas_energy_usage_column=self.gas_energy_usage_column,
            steam_energy_usage_column=self.steam_energy_usage_column,
            include_in_total_denominator_column=self.include_in_total_denominator_column,
            require_in_plan_column=self.require_in_plan_column,
            energy_running_sum_percentage=0.60,
        )
        self.property_view_factory = FakePropertyViewFactory(organization=self.org, user=self.user)

        self.maxDiff = None

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
                        "exclude_from_plan_column": None,
                        "require_in_plan_column": self.require_in_plan_column.id,
                        "gross_floor_area_column": None,
                        "building_category_column": None,
                        "electric_eui_column": None,
                        "gas_eui_column": None,
                        "steam_eui_column": None,
                        "total_eui_column": None,
                        "electric_energy_usage_column": self.electric_energy_usage_column.id,
                        "gas_energy_usage_column": self.gas_energy_usage_column.id,
                        "steam_energy_usage_column": self.steam_energy_usage_column.id,
                        "electric_data_source_column": None,
                        "gas_data_source_column": None,
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
                    "exclude_from_plan_column": None,
                    "require_in_plan_column": self.require_in_plan_column.id,
                    "gross_floor_area_column": None,
                    "building_category_column": None,
                    "electric_eui_column": None,
                    "gas_eui_column": None,
                    "steam_eui_column": None,
                    "total_eui_column": None,
                    "electric_energy_usage_column": self.electric_energy_usage_column.id,
                    "gas_energy_usage_column": self.gas_energy_usage_column.id,
                    "steam_energy_usage_column": self.steam_energy_usage_column.id,
                    "electric_data_source_column": None,
                    "gas_data_source_column": None,
                },
            },
        )

    def test_get_selected_properties(self):
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
        results = self.facilities_plan.get_selected_properties(self.ali, self.cycle)

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
                for r in results.property_rankings.all()
            ],
            [
                {
                    "total_energy_usage": 40.0,
                    "percentage_of_total_energy_usage": 0.4,
                    "rank": 0,
                    "running_percentage": 0.4,
                    "running_square_footage": 0.0,
                },
                {
                    "total_energy_usage": 30.0,
                    "percentage_of_total_energy_usage": 0.3,
                    "rank": 1,
                    "running_percentage": 0.7,
                    "running_square_footage": 0.0,
                },
                {
                    "total_energy_usage": 20.0,
                    "percentage_of_total_energy_usage": 0.2,
                    "rank": 2,
                    "running_percentage": 0.9,
                    "running_square_footage": 0.0,
                },
                {
                    "total_energy_usage": 10.0,
                    "percentage_of_total_energy_usage": 0.1,
                    "rank": 3,
                    "running_percentage": 1.0,
                    "running_square_footage": 0.0,
                },
            ],
        )

    def test_get_selected_properties_missing_columns(self):
        # Setup
        PropertyView.objects.all().delete()
        for e in [10, 20, 30, 40]:
            self.property_view_factory.get_property_view(
                cycle=self.cycle,
                extra_data={
                    "electric_energy_usage_column": e,
                    "gas_energy_usage_column": None,
                    # "steam_energy_usage_column": 0,  # oh no! i'm missing
                    "include_in_total_denominator_column": True,
                },
            )

        # Action
        results = self.facilities_plan.get_selected_properties(self.ali, self.cycle)

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
                for r in results.property_rankings.all()
            ],
            [
                {
                    "total_energy_usage": 40.0,
                    "percentage_of_total_energy_usage": 0.4,
                    "rank": 0,
                    "running_percentage": 0.4,
                    "running_square_footage": 0.0,
                },
                {
                    "total_energy_usage": 30.0,
                    "percentage_of_total_energy_usage": 0.3,
                    "rank": 1,
                    "running_percentage": 0.7,
                    "running_square_footage": 0.0,
                },
                {
                    "total_energy_usage": 20.0,
                    "percentage_of_total_energy_usage": 0.2,
                    "rank": 2,
                    "running_percentage": 0.9,
                    "running_square_footage": 0.0,
                },
                {
                    "total_energy_usage": 10.0,
                    "percentage_of_total_energy_usage": 0.1,
                    "rank": 3,
                    "running_percentage": 1.0,
                    "running_square_footage": 0.0,
                },
            ],
        )

    def test_get_selected_properties_require_in_plan(self):
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
        results = self.facilities_plan.get_selected_properties(self.ali, self.cycle)

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
                for r in results.property_rankings.all()
            ],
            [
                {
                    "total_energy_usage": 20.0,
                    "percentage_of_total_energy_usage": 0.2,
                    "rank": 0,
                    "running_percentage": 0.2,
                    "running_square_footage": 0.0,
                },
                {
                    "total_energy_usage": 10.0,
                    "percentage_of_total_energy_usage": 0.1,
                    "rank": 1,
                    "running_percentage": 0.3,
                    "running_square_footage": 0.0,
                },
                {
                    "total_energy_usage": 40.0,
                    "percentage_of_total_energy_usage": 0.4,
                    "rank": 2,
                    "running_percentage": 0.7,
                    "running_square_footage": 0.0,
                },
                {
                    "total_energy_usage": 30.0,
                    "percentage_of_total_energy_usage": 0.3,
                    "rank": 3,
                    "running_percentage": 1.0,
                    "running_square_footage": 0.0,
                },
            ],
        )

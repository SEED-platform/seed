"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from datetime import UTC, datetime

from django.urls import reverse

from seed.models import Column, CycleGoal, Goal
from seed.test_helpers.fake import FakeCycleFactory, FakePropertyFactory, FakePropertyViewFactory
from seed.tests.util import AccessLevelBaseTestCase


class GoalPropertyViewIdsTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.root_owner_user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.baseline_cycle = self.cycle_factory.get_cycle(start=datetime(2022, 1, 1, tzinfo=UTC))
        self.current_cycle = self.cycle_factory.get_cycle(start=datetime(2023, 1, 1, tzinfo=UTC))
        self.goal = Goal.objects.create(
            organization=self.org,
            access_level_instance=self.root_level_instance,
            baseline_cycle=self.baseline_cycle,
            eui_column1=Column.objects.get(organization=self.org, column_name="site_eui"),
            area_column=Column.objects.get(organization=self.org, column_name="gross_floor_area"),
            target_percentage=10,
            name="Selection Goal",
        )
        self.cycle_goal = CycleGoal.objects.create(goal=self.goal, current_cycle=self.current_cycle)

        root_property = self.property_factory.get_property(access_level_instance=self.root_level_instance)
        child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)
        self.root_baseline_view = self.property_view_factory.get_property_view(prprty=root_property, cycle=self.baseline_cycle)
        self.property_view_factory.get_property_view(prprty=root_property, cycle=self.current_cycle)
        self.child_baseline_view = self.property_view_factory.get_property_view(prprty=child_property, cycle=self.baseline_cycle)
        self.property_view_factory.get_property_view(prprty=child_property, cycle=self.current_cycle)

    def test_returns_only_baseline_view_ids_in_goal_scope(self):
        self.login_as_root_member()
        url = reverse(
            "api:v4:goals-property-view-ids",
            kwargs={"pk": self.goal.id, "cycle_goal_id": self.cycle_goal.id},
        )

        response = self.client.get(url, {"organization_id": self.org.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()["property_view_ids"]),
            {self.root_baseline_view.id, self.child_baseline_view.id},
        )

    def test_denies_goal_selection_outside_user_hierarchy(self):
        self.login_as_child_member()
        url = reverse(
            "api:v4:goals-property-view-ids",
            kwargs={"pk": self.goal.id, "cycle_goal_id": self.cycle_goal.id},
        )

        response = self.client.get(url, {"organization_id": self.org.id})

        self.assertEqual(response.status_code, 404)
"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime

from django.urls import reverse_lazy

from seed.models import Column, CycleGoal, PropertyViewLabel
from seed.models.data_quality import StatusLabel
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeCycleFactory,
    FakeGoalFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import AccessLevelBaseTestCase


class PropertyLabelViewTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.root_owner_user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.goal_factory = FakeGoalFactory(organization=self.org)

        # cycles
        self.cycle1 = self.cycle_factory.get_cycle(start=datetime(2001, 1, 1), end=datetime(2002, 1, 1))
        self.cycle2 = self.cycle_factory.get_cycle(start=datetime(2002, 1, 1), end=datetime(2003, 1, 1))
        self.root_ali = self.org.root

        self.property1 = self.property_factory.get_property(access_level_instance=self.root_ali)
        self.property2 = self.property_factory.get_property(access_level_instance=self.root_ali)
        self.property3 = self.property_factory.get_property(access_level_instance=self.root_ali)
        self.property4 = self.property_factory.get_property(access_level_instance=self.root_ali)
        self.property5 = self.property_factory.get_property(access_level_instance=self.root_ali)
        self.property6 = self.property_factory.get_property(access_level_instance=self.root_ali)

        state_details = self.property_state_factory.get_details()
        self.state1 = self.property_state_factory.get_property_state(**state_details)
        self.state2 = self.property_state_factory.get_property_state(**state_details)
        self.state3 = self.property_state_factory.get_property_state(**state_details)
        self.state4 = self.property_state_factory.get_property_state(**state_details)
        self.state5 = self.property_state_factory.get_property_state(**state_details)
        self.state6 = self.property_state_factory.get_property_state(**state_details)

        self.view1 = self.property_view_factory.get_property_view(prprty=self.property1, state=self.state1, cycle=self.cycle1)
        self.view2 = self.property_view_factory.get_property_view(prprty=self.property2, state=self.state2, cycle=self.cycle1)
        self.view3 = self.property_view_factory.get_property_view(prprty=self.property3, state=self.state3, cycle=self.cycle1)
        self.view4 = self.property_view_factory.get_property_view(prprty=self.property4, state=self.state4, cycle=self.cycle1)
        self.view5 = self.property_view_factory.get_property_view(prprty=self.property5, state=self.state5, cycle=self.cycle1)
        self.view6 = self.property_view_factory.get_property_view(prprty=self.property6, state=self.state6, cycle=self.cycle1)

        goal_details = {
            "baseline_cycle": self.cycle1,
            "access_level_instance": self.root_ali,
            "eui_column1": Column.objects.get(organization=self.org.id, column_name="source_eui"),
            "area_column": Column.objects.get(organization=self.org.id, column_name="gross_floor_area"),
            "target_percentage": 20,
            "name": "goal1",
        }
        self.goal1 = self.goal_factory.get_goal(**goal_details)
        self.cycle_goal = CycleGoal.objects.create(current_cycle=self.cycle2, goal=self.goal1, salesforce_annual_report_id="123")
        goal_details["name"] = "goal2"
        self.goal2 = self.goal_factory.get_goal(**goal_details)

        labels = StatusLabel.objects.all()
        self.pvl1 = PropertyViewLabel.objects.create(propertyview=self.view1, statuslabel=labels[0])
        self.pvl2 = PropertyViewLabel.objects.create(propertyview=self.view2, statuslabel=labels[1])
        self.pvl3 = PropertyViewLabel.objects.create(propertyview=self.view3, statuslabel=labels[2], goal=self.goal1)
        self.pvl4 = PropertyViewLabel.objects.create(propertyview=self.view4, statuslabel=labels[3], goal=self.goal1)
        self.pvl5 = PropertyViewLabel.objects.create(propertyview=self.view5, statuslabel=labels[2], goal=self.goal2)
        self.pvl6 = PropertyViewLabel.objects.create(propertyview=self.view6, statuslabel=labels[4], goal=self.goal2)

    def test_property_view_label_viewset(self):
        url = reverse_lazy("api:v3:property_view_labels-list-by-cycle-goal")
        params = {"organization_id": self.org.id, "goal_id": self.goal1.id, "cycle_id": self.cycle_goal.current_cycle.id}
        response = self.client.get(url, params, content_type="application/json")
        labels = response.json()
        assert len(labels) == 0

        params["cycle_id"] = self.goal1.baseline_cycle.id
        response = self.client.get(url, params, content_type="application/json")
        labels = response.json()
        assert len(labels) == 4
        assert labels[0]["goal"] is None
        assert labels[1]["goal"] is None
        assert labels[2]["goal"] == self.goal1.id
        assert labels[3]["goal"] == self.goal1.id

    def test_list_by_cycle_goal_returns_goal_and_unattached_labels(self):
        url = reverse_lazy("api:v3:property_view_labels-list-by-cycle-goal")
        params = {"organization_id": self.org.id, "goal_id": self.goal1.id, "cycle_id": self.goal1.baseline_cycle.id}

        response = self.client.get(url, params, content_type="application/json")
        assert response.status_code == 200

        labels = response.json()
        assert len(labels) == 4
        goals = [label["goal"] for label in labels]
        assert goals.count(None) == 2
        assert goals.count(self.goal1.id) == 2

    def _inventory_labels(self):
        url = reverse_lazy("api:v3:properties-labels")
        response = self.client.post(
            f"{url}?organization_id={self.org.id}&cycle_id={self.cycle1.id}",
            content_type="application/json",
        )
        assert response.status_code == 200
        return {label["id"]: label for label in response.json()}

    def test_inventory_labels_is_applied_includes_goal_applied_views(self):
        """Goal-applied labels must stay visible in the inventory list and detail pages."""
        labels = self._inventory_labels()

        manual_label = labels[self.pvl1.statuslabel_id]
        assert manual_label["is_applied"] == [self.view1.id]
        assert manual_label["is_applied_by_goal"] == []

        # statuslabel shared by goal1 (view3) and goal2 (view5)
        assert self.pvl3.statuslabel_id in labels, "goal-applied label missing from the payload"
        goal_label = labels[self.pvl3.statuslabel_id]
        assert sorted(goal_label["is_applied"]) == sorted([self.view3.id, self.view5.id])
        assert sorted(goal_label["is_applied_by_goal"]) == sorted([self.view3.id, self.view5.id])

    def test_inventory_labels_reports_unapplied_labels(self):
        """Labels with no applications at all must still be returned."""
        labels = self._inventory_labels()
        unapplied = StatusLabel.objects.exclude(
            id__in=[
                self.pvl1.statuslabel_id,
                self.pvl2.statuslabel_id,
                self.pvl3.statuslabel_id,
                self.pvl4.statuslabel_id,
                self.pvl6.statuslabel_id,
            ]
        ).first()

        assert unapplied.id in labels
        assert labels[unapplied.id]["is_applied"] == []
        assert labels[unapplied.id]["is_applied_by_goal"] == []

    def test_taxlot_labels_omit_is_applied_by_goal(self):
        url = reverse_lazy("api:v3:taxlots-labels")
        response = self.client.post(f"{url}?organization_id={self.org.id}", content_type="application/json")

        assert response.status_code == 200
        assert all("is_applied_by_goal" not in label for label in response.json())

    def test_goal_applied_label_can_be_removed_from_inventory(self):
        """Users may delete a cross-cycle label from the inventory; the UI warns them first."""
        response = self.client.put(
            f"/api/v3/labels_property/?organization_id={self.org.id}",
            data=json.dumps({"inventory_ids": [self.view3.id], "remove_label_ids": [self.pvl3.statuslabel_id]}),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert not PropertyViewLabel.objects.filter(id=self.pvl3.id).exists()
        # the other goal's use of the same label is untouched
        assert PropertyViewLabel.objects.filter(id=self.pvl5.id).exists()

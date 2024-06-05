"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime
from django.forms.models import model_to_dict
from django.test import TestCase
from quantityfield.units import ureg
from django.urls import reverse_lazy


from seed.models import Column, DerivedColumnParameter, Goal, PropertyView, PropertyViewLabel
from seed.models.data_quality import DataQualityCheck, DataQualityTypeCastError, Rule, StatusLabel, UnitMismatchError
from seed.models.derived_columns import DerivedColumn
from seed.models.models import ASSESSED_RAW
from seed.test_helpers.fake import (
    FakeDerivedColumnFactory,
    FakeGoalFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
    FakeColumnFactory,
    FakeCycleFactory,
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
            "current_cycle": self.cycle2, 
            "access_level_instance": self.root_ali,
            "eui_column1": Column.objects.get(organization=self.org.id, column_name="source_eui"),
            "area_column": Column.objects.get(organization=self.org.id, column_name="gross_floor_area"),
            "target_percentage": 20,
            "name": "goal1",
        }
        self.goal1 = self.goal_factory.get_goal(**goal_details)
        goal_details["name"] = "goal2"
        self.goal2 = self.goal_factory.get_goal(**goal_details)

        labels = StatusLabel.objects.all()
        self.pvl1 = PropertyViewLabel.objects.create(propertyview=self.view1, statuslabel=labels[0])
        self.pvl1 = PropertyViewLabel.objects.create(propertyview=self.view2, statuslabel=labels[1])
        self.pvl1 = PropertyViewLabel.objects.create(propertyview=self.view3, statuslabel=labels[2], goal=self.goal1)
        self.pvl1 = PropertyViewLabel.objects.create(propertyview=self.view4, statuslabel=labels[3], goal=self.goal1)
        self.pvl1 = PropertyViewLabel.objects.create(propertyview=self.view5, statuslabel=labels[2], goal=self.goal2)
        self.pvl1 = PropertyViewLabel.objects.create(propertyview=self.view6, statuslabel=labels[4], goal=self.goal2)

    def test_property_view_label_viewset(self):
        url = reverse_lazy("api:v3:property_view_labels-list-by-goal")
        response = self.client.get(url, {"organization_id": self.org.id, "goal_id": self.goal1.id}, content_type="application/json")
        response = json.loads(response.content)
        labels = response["message"]

        assert len(labels) == 4
        assert labels[0]["goal"] == None
        assert labels[1]["goal"] == None
        assert labels[2]["goal"] == self.goal1.id
        assert labels[3]["goal"] == self.goal1.id

        
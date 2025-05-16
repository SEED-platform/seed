"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import reverse_lazy

from seed.models import Column
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import AccessLevelBaseTestCase


class TestAnalysisViews(AccessLevelBaseTestCase):

    def setUp(self):
        super().setUp()
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org)
        self.cycle = self.cycle_factory.get_cycle()

        Column.objects.create( table_name="PropertyState", column_name="extra_field", organization=self.org, is_extra_data=True )

        for i in range(5):
            self.property_view_factory.get_property_view(cycle=self.cycle)
        for i in range(5):
            details = {"custom_id_1": i, "extra_data": {"extra_field": f"extra {i}"}}
            state = self.property_state_factory.get_property_state(**details)
            self.property_view_factory.get_property_view(cycle=self.cycle, state=state)

    def test_stats(self):
        url =  reverse_lazy("api:v4:analyses-stats") + f"?organization_id={self.org.id}&cycle_id={self.cycle.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["status"], "success")
        stats = response["stats"]

        address_line_1 = next(stat for stat in stats if stat["column_name"] == "address_line_1")
        address_line_2 = next(stat for stat in stats if stat["column_name"] == "address_line_2")
        custom_id_1 = next(stat for stat in stats if stat["column_name"] == "custom_id_1")
        extra_field = next(stat for stat in stats if stat["column_name"] == "extra_field")

        self.assertEqual(address_line_1["count"], 10)
        self.assertEqual(address_line_1["display_name"], "Address Line 1")
        self.assertEqual(address_line_1["is_extra_data"], False)
        self.assertEqual(address_line_2["count"], 0)
        self.assertEqual(custom_id_1["count"], 5)
        self.assertEqual(extra_field["count"], 5)
        self.assertEqual(extra_field["is_extra_data"], True)



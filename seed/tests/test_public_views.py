# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from datetime import datetime

from django.urls import reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.models import Column
from seed.test_helpers.fake import FakeCycleFactory, FakePropertyFactory, FakePropertyStateFactory, FakePropertyViewFactory
from seed.tests.util import DataMappingBaseTestCase
from seed.utils.organizations import create_organization


class TestPublicViews(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        user = User.objects.create_superuser(email="test_user@demo.com", **user_details)
        self.org, _, _ = create_organization(user)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)

        Column.objects.create(
            table_name="PropertyState",
            column_name="extra_col",
            organization=self.org,
            is_extra_data=True,
        )
        column_names = ["ubid", "property_name", "source_eui", "gross_floor_area", "energy_score", "extra_col"]
        for column_name in column_names:
            column = Column.objects.filter(column_name=column_name).first()
            column.shared_field_type = 1
            column.save()

        # create cycles
        self.cycle1 = self.cycle_factory.get_cycle(name="2010 Calendar Year", start=datetime(2010, 1, 1), end=datetime(2011, 1, 1))
        self.cycle2 = self.cycle_factory.get_cycle(name="2011 Calendar Year", start=datetime(2011, 1, 1), end=datetime(2012, 1, 1))
        self.cycle3 = self.cycle_factory.get_cycle(name="2012 Calendar Year", start=datetime(2012, 1, 1), end=datetime(2013, 1, 1))

        # create properties
        property1 = self.property_factory.get_property()
        property2 = self.property_factory.get_property()

        # create states{property#}{cycle#}
        state11 = self.property_state_factory.get_property_state(property_name="property 11", ubid="a+b+c-1")
        state12 = self.property_state_factory.get_property_state(property_name="property 12", ubid="a+b+c-1")
        state13 = self.property_state_factory.get_property_state(
            property_name="property 13", ubid="a+b+c-1", extra_data={"extra_col": "aaa"}
        )
        state21 = self.property_state_factory.get_property_state(
            property_name="property 21", ubid="a+b+c-2", extra_data={"extra_col": "bbb"}
        )
        state22 = self.property_state_factory.get_property_state(property_name="property 22", ubid="a+b+c-2")
        state23 = self.property_state_factory.get_property_state(property_name="property 23", ubid="a+b+c-2")

        # create views
        self.property_view_factory.get_property_view(prpty=property1, state=state11, cycle=self.cycle1)
        self.property_view_factory.get_property_view(prpty=property1, state=state12, cycle=self.cycle2)
        self.property_view_factory.get_property_view(prpty=property1, state=state13, cycle=self.cycle3)
        self.property_view_factory.get_property_view(prpty=property2, state=state21, cycle=self.cycle1)
        self.property_view_factory.get_property_view(prpty=property2, state=state22, cycle=self.cycle2)
        self.property_view_factory.get_property_view(prpty=property2, state=state23, cycle=self.cycle3)

    def test_public_feed(self):
        # a non logged in user should be able to access public endpoints, but not others
        url = reverse_lazy("api:v3:organizations-list")
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403
        assert response.json() == {"detail": "You do not have permission to perform this action."}

        # public feed is not yet enabled
        url = reverse_lazy("api:v3:public-organizations-feed-json", args=[self.org.id])
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert response.json() == {
            "detail": f"Public feed is not enabled for organization '{self.org.name}'. Public endpoints can be enabled in organization settings"
        }

        # enable public feed
        self.org.public_feed_enabled = True
        self.org.public_feed_labels = True
        self.org.save()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        res = response.json()
        assert sorted(res.keys()) == ["data", "organization", "pagination", "query_params"]
        assert sorted(res["pagination"].keys()) == ["page", "per_page", "property_count", "taxlot_count", "total_pages"]
        assert sorted(res["query_params"].keys()) == ["cycle_ids", "labels", "properties", "taxlots"]
        assert res["organization"]["id"] == self.org.id
        data = res["data"]
        assert len(data["properties"]) == 6
        assert len(data["taxlots"]) == 0

        url = reverse_lazy("api:v3:public-organizations-feed-html", args=[self.org.id])
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"

    def test_public_geojson(self):
        url = reverse_lazy("api:v3:public-organizations-cycles-geojson", args=[self.org.id, self.cycle2.id])
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert response.json() == {
            "detail": f"Public GeoJSON is not enabled for organization '{self.org.name}'. Public endpoints can be enabled in organization settings"
        }

        self.org.public_feed_enabled = True
        self.org.save()

        # incorrect args
        url = reverse_lazy("api:v3:public-organizations-cycles-geojson", args=[-1, self.cycle1.id])
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json() == {"erorr": "Organization does not exist"}
        url = reverse_lazy("api:v3:public-organizations-cycles-geojson", args=[self.org.id, -1])
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json() == {"erorr": "Cycle does not exist"}

        url = reverse_lazy("api:v3:public-organizations-cycles-geojson", args=[self.org.id, self.cycle2.id])
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        data = response.json()
        assert sorted(data.keys()) == ["features", "name", "type"]
        assert len(data["features"]) == 2
        assert data["features"][0]["properties"]["Property Name"] == "property 12"

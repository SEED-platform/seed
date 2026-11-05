"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.urls import reverse_lazy

from seed.models import PropertyView
from seed.test_helpers.fake import FakePropertyViewFactory
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class PropertyViewsTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.root_property = self.property_factory.get_property(access_level_instance=self.root_level_instance)
        self.root_view = self.property_view_factory.get_property_view(prprty=self.root_property)

        self.child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)
        self.child_view = self.property_view_factory.get_property_view(prprty=self.child_property)

        self.cycle = self.cycle_factory.get_cycle()

    def test_property_views_list(self):
        url = reverse_lazy("api:v3:property_views-list") + f"?organization_id={self.org.id}"

        self.login_as_child_member()
        resp = self.client.get(url, content_type="application/json")
        assert len(resp.json()["property_views"]) == 1

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/json")
        assert len(resp.json()["property_views"]) == 2

    def test_property_views_get(self):
        url = reverse_lazy("api:v3:property_views-detail", args=[self.root_view.pk]) + f"?organization_id={self.org.id}"

        self.login_as_child_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 200

    def test_property_views_delete(self):
        url = reverse_lazy("api:v3:property_views-detail", args=[self.root_view.pk]) + f"?organization_id={self.org.id}"

        self.login_as_child_member()
        resp = self.client.delete(url, content_type="application/json")
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.delete(url, content_type="application/json")
        assert resp.status_code == 204

    def test_property_views_put(self):
        url = reverse_lazy("api:v3:property_views-detail", args=[self.root_view.pk]) + f"?organization_id={self.org.id}"
        params = json.dumps({})

        self.login_as_child_member()
        resp = self.client.put(url, params, content_type="application/json")
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.put(url, params, content_type="application/json")
        assert resp.status_code == 200

    def test_property_views_patch(self):
        url = reverse_lazy("api:v3:property_views-detail", args=[self.root_view.pk]) + f"?organization_id={self.org.id}"
        params = json.dumps({})

        self.login_as_child_member()
        resp = self.client.patch(url, params, content_type="application/json")
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.patch(url, params, content_type="application/json")
        assert resp.status_code == 200

    def test_property_views_create(self):
        url = reverse_lazy("api:v3:property_views-list") + f"?organization_id={self.org.id}"
        params = json.dumps({"cycle_id": self.cycle.pk, "property_id": self.root_property.pk, "state_id": self.root_view.state.pk})

        self.login_as_child_member()
        resp = self.client.post(url, params, content_type="application/json")
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, params, content_type="application/json")
        assert resp.status_code == 201

    def test_property_views_list_excludes_other_organizations(self):
        # the other organization's access level tree overlaps this one's `lft`/`rgt` range
        other_org, _, _ = create_organization(self.superuser, "test-organization-b")
        FakePropertyViewFactory(organization=other_org).get_property_view()
        url = reverse_lazy("api:v3:property_views-list") + f"?organization_id={self.org.id}"

        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/json")
        assert {view["id"] for view in resp.json()["property_views"]} == {self.root_view.id, self.child_view.id}

    def test_property_views_create_rejects_inaccessible_cycle_and_state(self):
        url = reverse_lazy("api:v3:property_views-list") + f"?organization_id={self.org.id}"
        other_org, _, _ = create_organization(self.superuser, "test-organization-b")
        other_view = FakePropertyViewFactory(organization=other_org).get_property_view()
        cycle = self.cycle_factory.get_cycle(name="new cycle")

        self.login_as_root_member()
        # another organization's state or cycle cannot be linked to this organization's property
        for body in [
            {"cycle_id": cycle.pk, "property_id": self.root_property.pk, "state_id": other_view.state_id},
            {"cycle_id": other_view.cycle_id, "property_id": self.root_property.pk, "state_id": self.root_view.state_id},
        ]:
            resp = self.client.post(url, json.dumps(body), content_type="application/json")
            assert resp.status_code == 404
        assert not PropertyView.objects.filter(property=self.root_property, cycle__in=[cycle, other_view.cycle]).exists()

        # a child member cannot share the state of a property outside their access level
        self.login_as_child_member()
        params = {"cycle_id": cycle.pk, "property_id": self.child_property.pk}
        resp = self.client.post(url, json.dumps({**params, "state_id": self.root_view.state_id}), content_type="application/json")
        assert resp.status_code == 404
        resp = self.client.post(url, json.dumps({**params, "state_id": self.child_view.state_id}), content_type="application/json")
        assert resp.status_code == 201

    def test_property_views_create_with_organization_in_body(self):
        # the organization can be given in the body, and only the view's fields are used to create it
        url = reverse_lazy("api:v3:property_views-list")
        body = {
            "organization_id": self.org.id,
            "cycle_id": self.cycle.pk,
            "property_id": self.root_property.pk,
            "state_id": self.root_view.state_id,
        }

        self.login_as_root_member()
        resp = self.client.post(url, json.dumps(body), content_type="application/json")
        assert resp.status_code == 201
        new_view = PropertyView.objects.get(pk=resp.json()["property_view"]["id"])
        assert (new_view.property_id, new_view.cycle_id, new_view.state_id) == (
            self.root_property.pk,
            self.cycle.pk,
            self.root_view.state_id,
        )

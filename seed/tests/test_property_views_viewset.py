"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse_lazy

from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import ROLE_MEMBER
from seed.models import DATA_STATE_IMPORT, PropertyView, TaxLot, TaxLotProperty
from seed.test_helpers.fake import FakePropertyViewFactory
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.merge import merge_properties
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

    def test_property_views_create_rejects_states_without_views_for_non_root_users(self):
        url = reverse_lazy("api:v3:property_views-list") + f"?organization_id={self.org.id}"
        cycle = self.cycle_factory.get_cycle(name="new cycle")
        # a raw state of a root user's import, which has no view
        import_record = ImportRecord.objects.create(
            owner=self.root_owner_user, super_organization=self.org, access_level_instance=self.org.root
        )
        import_file = ImportFile.objects.create(import_record=import_record)
        import_state = self.property_state_factory.get_property_state(import_file=import_file, data_state=DATA_STATE_IMPORT)
        # the states of root properties merged away into a new state
        merged_views = [
            self.property_view_factory.get_property_view(
                prprty=self.property_factory.get_property(access_level_instance=self.root_level_instance), cycle=self.cycle
            )
            for _ in range(2)
        ]
        merged_away_state_ids = [view.state_id for view in merged_views]
        merge_properties(merged_away_state_ids, self.org.id, "Manual Match")
        # the state of a deleted root view
        deleted_view_state_id = self.root_view.state_id
        self.root_view.delete()
        detached_state_ids = [import_state.id, *merged_away_state_ids, deleted_view_state_id]
        assert not PropertyView.objects.filter(state_id__in=detached_state_ids).exists()

        # a child member cannot attach any of them to their property
        self.login_as_child_member()
        for state_id in detached_state_ids:
            body = {"cycle_id": cycle.pk, "property_id": self.child_property.pk, "state_id": state_id}
            resp = self.client.post(url, json.dumps(body), content_type="application/json")
            assert resp.status_code == 404
        assert not PropertyView.objects.filter(state_id__in=detached_state_ids).exists()

        # a root member, who can access the whole organization, can
        self.login_as_root_member()
        body = {"cycle_id": cycle.pk, "property_id": self.root_property.pk, "state_id": deleted_view_state_id}
        resp = self.client.post(url, json.dumps(body), content_type="application/json")
        assert resp.status_code == 201
        assert PropertyView.objects.filter(property=self.root_property, cycle=cycle, state_id=deleted_view_state_id).exists()

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

    def test_property_views_create_locks_the_state(self):
        # so that concurrent requests can't both find a state unused and attach it to different properties
        url = reverse_lazy("api:v3:property_views-list") + f"?organization_id={self.org.id}"
        body = {"cycle_id": self.cycle.pk, "property_id": self.root_property.pk, "state_id": self.root_view.state_id}

        self.login_as_root_member()
        with CaptureQueriesContext(connection) as queries:
            resp = self.client.post(url, json.dumps(body), content_type="application/json")
        assert resp.status_code == 201
        sql = [query["sql"] for query in queries.captured_queries]
        lock_index = next(i for i, q in enumerate(sql) if 'FROM "seed_propertystate"' in q and "FOR UPDATE" in q)
        insert_index = next(i for i, q in enumerate(sql) if q.startswith('INSERT INTO "seed_propertyview"'))
        # the state is locked before the views that use it are checked
        check_index = next(i for i, q in enumerate(sql) if 'FROM "seed_propertyview"' in q and '"state_id" =' in q)
        assert lock_index < check_index < insert_index

    def test_property_views_create_only_shares_states_within_a_property(self):
        url = reverse_lazy("api:v3:property_views-list") + f"?organization_id={self.org.id}"
        cycle = self.cycle_factory.get_cycle(name="new cycle")

        # a root member cannot share a child property's state with a root property, which child members could then
        # edit or delete through their own view
        self.login_as_root_member()
        body = {"cycle_id": cycle.pk, "property_id": self.root_property.pk, "state_id": self.child_view.state_id}
        resp = self.client.post(url, json.dumps(body), content_type="application/json")
        assert resp.status_code == 400
        assert resp.json()["message"] == "The state belongs to another property's view."
        assert not PropertyView.objects.filter(property=self.root_property, cycle=cycle).exists()

        # but can share it with the same property in another cycle
        resp = self.client.post(url, json.dumps({**body, "property_id": self.child_property.pk}), content_type="application/json")
        assert resp.status_code == 201

    def test_property_views_create_rejects_duplicate_property_and_cycle(self):
        url = reverse_lazy("api:v3:property_views-list") + f"?organization_id={self.org.id}"
        sibling_level_instance = self.org.add_new_access_level_instance(self.org.root.id, "sibling")
        sibling_member_user_details = {"username": "sibling_member@demo.com", "password": "test_pass"}
        self.org.add_member(User.objects.create_user(**sibling_member_user_details), sibling_level_instance.pk, ROLE_MEMBER)
        body = {"cycle_id": self.child_view.cycle_id, "property_id": self.child_property.pk, "state_id": self.child_view.state_id}
        count = PropertyView.objects.count()

        # a sibling member cannot learn whether the child property has a view in the cycle
        self.client.login(**sibling_member_user_details)
        resp = self.client.post(url, json.dumps(body), content_type="application/json")
        assert resp.status_code == 404

        self.login_as_child_member()
        resp = self.client.post(url, json.dumps(body), content_type="application/json")
        assert resp.status_code == 400
        assert resp.json()["message"] == "The property already has a view in this cycle."
        assert PropertyView.objects.count() == count

    def test_property_views_create_rejects_malformed_ids(self):
        url = reverse_lazy("api:v3:property_views-list") + f"?organization_id={self.org.id}"
        valid_body = {"cycle_id": self.cycle.pk, "property_id": self.child_property.pk, "state_id": self.child_view.state_id}
        count = PropertyView.objects.count()

        self.login_as_child_member()
        # a malformed property ID cannot identify a property, and the cycle and state IDs must be integers
        for key, value, status_code in [
            ("property_id", "abc", 404),
            ("property_id", "", 404),
            ("property_id", [self.child_property.pk], 404),
            ("property_id", None, 404),
            ("cycle_id", "abc", 400),
            ("cycle_id", None, 400),
            ("state_id", "abc", 400),
            ("state_id", None, 400),
            ("state_id", {"id": self.child_view.state_id}, 400),
            ("state_id", True, 400),
        ]:
            resp = self.client.post(url, json.dumps({**valid_body, key: value}), content_type="application/json")
            assert resp.status_code == status_code, (key, value)

        # a JSON number too large to be an integer
        raw_body = f'{{"cycle_id": {self.cycle.pk}, "property_id": 1e999, "state_id": {self.child_view.state_id}}}'
        resp = self.client.post(url, raw_body, content_type="application/json")
        assert resp.status_code == 404

        for key, status_code in [("property_id", 404), ("cycle_id", 400), ("state_id", 400)]:
            body = {k: v for k, v in valid_body.items() if k != key}
            resp = self.client.post(url, json.dumps(body), content_type="application/json")
            assert resp.status_code == status_code, key

        # without a property_id, has_hierarchy_access checks the query string's property view instead
        body = {k: v for k, v in valid_body.items() if k != "property_id"}
        resp = self.client.post(f"{url}&property_view_id={self.child_view.pk}", json.dumps(body), content_type="application/json")
        assert resp.status_code == 400
        resp = self.client.post(f"{url}&property_view_id=abc", json.dumps(body), content_type="application/json")
        assert resp.status_code == 404
        assert PropertyView.objects.count() == count

        # the same body with valid IDs is accepted
        resp = self.client.post(url, json.dumps(valid_body), content_type="application/json")
        assert resp.status_code == 201

    def test_property_views_detail_rejects_malformed_pk(self):
        url = reverse_lazy("api:v3:property_views-detail", args=["abc"]) + f"?organization_id={self.org.id}"
        count = PropertyView.objects.count()

        self.login_as_root_member()
        assert self.client.get(url, content_type="application/json").status_code == 404
        assert self.client.put(url, json.dumps({}), content_type="application/json").status_code == 404
        assert self.client.delete(url, content_type="application/json").status_code == 404
        assert PropertyView.objects.count() == count

    def test_property_views_create_rolls_back_when_the_property_cannot_be_saved(self):
        url = reverse_lazy("api:v3:property_views-list") + f"?organization_id={self.org.id}"
        # saving a property whose views are linked to tax lots in other access level instances fails validation, so
        # link the root view to a tax lot, then move the tax lot without validation
        taxlot = self.taxlot_factory.get_taxlot(access_level_instance=self.root_level_instance)
        taxlot_view = self.taxlot_view_factory.get_taxlot_view(taxlot=taxlot, cycle=self.root_view.cycle)
        TaxLotProperty.objects.create(property_view=self.root_view, taxlot_view=taxlot_view, cycle=self.root_view.cycle)
        TaxLot.objects.filter(pk=taxlot.pk).update(access_level_instance=self.child_level_instance)

        self.login_as_root_member()
        body = {"cycle_id": self.cycle.pk, "property_id": self.root_property.pk, "state_id": self.root_view.state_id}
        resp = self.client.post(url, json.dumps(body), content_type="application/json")
        assert resp.status_code == 400
        assert "related taxlots" in resp.json()["message"]
        assert not PropertyView.objects.filter(property=self.root_property, cycle=self.cycle).exists()

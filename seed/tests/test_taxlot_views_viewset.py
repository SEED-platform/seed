"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import reverse_lazy

from seed.test_helpers.fake import FakeTaxLotViewFactory
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class TaxlotViewsTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.root_taxlot = self.taxlot_factory.get_taxlot(access_level_instance=self.root_level_instance)
        self.root_view = self.taxlot_view_factory.get_taxlot_view(taxlot=self.root_taxlot)

        self.child_taxlot = self.taxlot_factory.get_taxlot(access_level_instance=self.child_level_instance)
        self.child_view = self.taxlot_view_factory.get_taxlot_view(taxlot=self.child_taxlot)

        self.cycle = self.cycle_factory.get_cycle()

    def test_taxlot_views_list(self):
        url = reverse_lazy("api:v3:taxlot_views-list") + f"?organization_id={self.org.id}"

        self.login_as_child_member()
        resp = self.client.get(url, content_type="application/json")
        assert len(resp.json()["taxlot_views"]) == 1

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/json")
        assert len(resp.json()["taxlot_views"]) == 2

    def test_taxlot_views_list_rejects_conflicting_organization_ids(self):
        other_org, _, _ = create_organization(self.superuser, "other-organization")
        FakeTaxLotViewFactory(organization=other_org).get_taxlot_view()

        # conflicting `organization` and `organization_id` params are rejected, since views may read either
        url = reverse_lazy("api:v3:taxlot_views-list") + f"?organization={self.org.id}&organization_id={other_org.id}"

        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.status_code == 403

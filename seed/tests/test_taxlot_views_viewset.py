from django.urls import reverse_lazy

from seed.tests.util import AccessLevelBaseTestCase


class TaxlotViewsTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.root_taxlot = self.taxlot_factory.get_taxlot(access_level_instance=self.root_level_instance)
        self.root_view = self.taxlot_view_factory.get_taxlot_view(taxlot=self.root_taxlot)

        self.child_taxlot = self.taxlot_factory.get_taxlot(access_level_instance=self.child_level_instance)
        self.child_view = self.taxlot_view_factory.get_taxlot_view(taxlot=self.child_taxlot)

        self.cycle = self.cycle_factory.get_cycle()

    def test_taxlot_views_list(self):
        url = reverse_lazy('api:v3:taxlot_views-list') + f'?organization_id={self.org.id}'

        self.login_as_child_member()
        resp = self.client.get(url, content_type='application/json')
        assert len(resp.json()['taxlot_views']) == 1

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type='application/json')
        assert len(resp.json()['taxlot_views']) == 2

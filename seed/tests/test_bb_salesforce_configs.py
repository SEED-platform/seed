"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import reverse_lazy

from seed.models import BBSalesforceConfig
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class BBSalesforceConfigViewSetTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

        self.salesforce_url = "http://test.com"
        self.bb_salesforce_config = BBSalesforceConfig.objects.create(
            organization=self.org,
            salesforce_url=self.salesforce_url,
            client_id="1",
            client_secret="1",
        )

    def test_list(self):
        # Action
        url = reverse_lazy("api:v3:bb_salesforce-configs-list") + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")

        # Assertion
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "status": "success",
                "bb_salesforce_configs": {
                    "organization": self.bb_salesforce_config.organization.id,
                    "salesforce_url": self.bb_salesforce_config.salesforce_url,
                    "client_id": self.bb_salesforce_config.client_id,
                    "client_secret": self.bb_salesforce_config.client_secret,
                },
            },
        )

    def test_update(self):
        # Action
        url = reverse_lazy("api:v3:bb_salesforce-configs-update-config") + "?organization_id=" + str(self.org.id)
        response = self.client.put(url, {"client_id": 2, "client_secret": 2}, content_type="application/json")

        # Assertion
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "status": "success",
                "bb_salesforce_configs": {
                    "organization": self.bb_salesforce_config.organization.id,
                    "salesforce_url": self.bb_salesforce_config.salesforce_url,
                    "client_id": "2",
                    "client_secret": "2",
                },
            },
        )
        updated_bb_config = BBSalesforceConfig.objects.get(id=self.bb_salesforce_config.id)
        assert updated_bb_config.client_id == "2"
        assert updated_bb_config.client_secret == "2"

    def test_delete(self):
        # Action
        url = (
            reverse_lazy("api:v3:bb_salesforce-configs-detail", args=[self.bb_salesforce_config.id])
            + "?organization_id="
            + str(self.org.id)
        )
        self.client.delete(url, content_type="application/json")

        # Assertion
        assert BBSalesforceConfig.objects.filter(id=self.bb_salesforce_config.id).first() is None

    def test_create(self):
        # Set up
        BBSalesforceConfig.objects.filter(organization_id=self.org.id).delete()
        assert BBSalesforceConfig.objects.filter(organization=self.org).first() is None

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-configs-update-config") + "?organization_id=" + str(self.org.id)
        data = {"salesforce_url": self.salesforce_url, "client_id": 2, "client_secret": 2}
        response = self.client.put(url, data, content_type="application/json")

        # Assertion
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "status": "success",
                "bb_salesforce_configs": {
                    "organization": self.bb_salesforce_config.organization.id,
                    "salesforce_url": self.bb_salesforce_config.salesforce_url,
                    "client_id": "2",
                    "client_secret": "2",
                },
            },
        )
        assert BBSalesforceConfig.objects.filter(organization=self.org).first() is not None

    def test_detail_endpoints_are_scoped_to_organization_owners(self):
        # Set Up - the root owner is not a member of the other organization
        other_org, _, _ = create_organization(self.superuser, "other-organization")
        other_config = BBSalesforceConfig.objects.create(organization=other_org, salesforce_url="http://other.com", client_id="3")
        own_url = reverse_lazy("api:v3:bb_salesforce-configs-detail", args=[self.bb_salesforce_config.id])
        other_url = reverse_lazy("api:v3:bb_salesforce-configs-detail", args=[other_config.id])
        own_org_params = f"?organization_id={self.org.id}"
        self.login_as_root_owner()

        # Action & Assertion - another organization's config cannot be read, changed, or deleted
        assert self.client.get(other_url + own_org_params).status_code == 404
        assert self.client.get(other_url + f"?organization_id={other_org.id}").status_code == 403
        response = self.client.put(other_url + own_org_params, {"client_id": "4"}, content_type="application/json")
        assert response.status_code == 404
        assert self.client.delete(other_url + own_org_params).status_code == 404
        other_config.refresh_from_db()
        assert other_config.client_id == "3"

        # Action & Assertion - members cannot read the config's secret
        self.login_as_root_member()
        assert self.client.get(own_url + own_org_params).status_code == 403

        # Action & Assertion - owners can
        self.login_as_root_owner()
        response = self.client.get(own_url + own_org_params)
        assert response.status_code == 200
        assert response.json()["client_secret"] == self.bb_salesforce_config.client_secret

    def test_create_uses_the_query_organization(self):
        # Set Up
        other_org, _, _ = create_organization(self.superuser, "other-organization")
        BBSalesforceConfig.objects.filter(organization=self.org).delete()
        self.login_as_root_owner()

        # Action - the body's organization is ignored
        url = reverse_lazy("api:v3:bb_salesforce-configs-list") + f"?organization_id={self.org.id}"
        data = {"organization": other_org.id, "salesforce_url": self.salesforce_url, "client_id": "2", "client_secret": "2"}
        response = self.client.post(url, data, content_type="application/json")

        # Assertion
        assert response.status_code == 201
        assert response.json()["organization"] == self.org.id
        assert BBSalesforceConfig.objects.filter(organization=self.org).exists()
        assert not BBSalesforceConfig.objects.filter(organization=other_org).exists()

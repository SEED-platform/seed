"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import reverse_lazy

from seed.models import BBSalesforceConfig
from seed.tests.util import AccessLevelBaseTestCase


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

"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from urllib.parse import quote_plus

import responses
from django.urls import reverse_lazy
from responses import matchers

from seed.models import BBSalesforceConfig, Goal
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.cache import get_cache_raw, set_cache_raw
from seed.views.v3.bb_salesforce import REDIRECT_URI


class BBSalesforceViewSetTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        self.salesforce_url = "http://test.com"
        self.bb_salesforce_config = BBSalesforceConfig.objects.create(
            organization=self.org,
            salesforce_url=self.salesforce_url,
            client_id=1,
            client_secret=1,
        )

        self.example_salesforce_goal_id = "example_salesforce_goal_id"
        self.goal = Goal.objects.create(
            salesforce_goal_id=self.example_salesforce_goal_id,
            target_percentage=30,
            access_level_instance_id=self.root_level_instance.id,
            area_column_id=self.column_factory.get_column("source_eui").id,  # does not matter
            baseline_cycle_id=self.cycle_factory.get_cycle(name="Cycle A").id,  # does not matter
            eui_column1_id=self.column_factory.get_column("source_eui").id,  # does not matter
            organization_id=self.org.id,  # does not matter
        )

    @responses.activate
    def test_login_url(self):
        # Set Up
        example_code_verifier = "example_code_verifier"
        example_code_challenge = "example_code_challenge"
        responses.add(
            responses.GET,
            f"{self.salesforce_url}/oauth2/pkce/generator",
            json={"code_verifier": example_code_verifier, "code_challenge": example_code_challenge},
            status=200,
        )

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-login-url") + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")

        #  Assertion
        assert response.status_code == 200
        assert (
            response.json()["url"] == f"{self.salesforce_url}/oauth2/authorize?"
            f"client_id={self.bb_salesforce_config.client_id}&"
            f"redirect_uri={quote_plus(REDIRECT_URI)}&"
            "response_type=code&"
            f"code_challenge={example_code_challenge}"
        )

        assert get_cache_raw(f"code_verifier_{self.org.id}") == example_code_verifier

    def test_login_url_no_connection(self):
        # Set Up
        BBSalesforceConfig.objects.filter(organization=self.org).delete()

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-login-url") + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")

        #  Assertion
        assert response.status_code == 200
        assert response.json()["response"] == "Org has no portfolio Salesforce connection."

    def test_login_url_invalid_url(self):
        # Set Up
        self.bb_salesforce_config.salesforce_url = "Im not a valid url"
        self.bb_salesforce_config.save()

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-login-url") + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")

        #  Assertion
        assert response.status_code == 400
        assert response.json()["message"] == "Invalid Salesforce URL"

    def test_logout(self):
        # Set Up
        set_cache_raw(f"access_token_{self.org.id}", "example access token")

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-logout") + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")

        #  Assertion
        assert response.status_code == 200
        assert get_cache_raw(f"access_token_{self.org.id}") is None

    @responses.activate
    def test_get_token(self):
        # Set Up
        example_code = "example code"
        example_code_verifier = "example code verifier"
        set_cache_raw(f"code_verifier_{self.org.id}", example_code_verifier)

        responses.add(
            responses.POST,
            f"{self.salesforce_url}/oauth2/token",
            json={"access_token": "example access token"},
            status=200,
            match=[
                matchers.query_param_matcher(
                    {
                        "grant_type": "authorization_code",
                        "code": example_code,
                        "client_id": self.org.bb_salesforce_config.client_id,
                        "client_secret": self.org.bb_salesforce_config.client_secret,
                        "redirect_uri": REDIRECT_URI,
                        "code_verifier": example_code_verifier,
                    }
                )
            ],
        )

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-get-token")
        response = self.client.get(
            url,
            {"organization_id": str(self.org.id), "code": example_code},
            content_type="application/json",
        )

        #  Assertion
        assert response.status_code == 200
        assert get_cache_raw(f"access_token_{self.org.id}") == "example access token"

    @responses.activate
    def test_get_token_salesforce_fails(self):
        # Set Up
        example_code = "example code"
        example_code_verifier = "example code verifier"
        set_cache_raw(f"code_verifier_{self.org.id}", example_code_verifier)

        responses.add(
            responses.POST,
            f"{self.salesforce_url}/oauth2/token",
            json={"failure": "bad bad bad"},
            status=400,
            match=[
                matchers.query_param_matcher(
                    {
                        "grant_type": "authorization_code",
                        "code": example_code,
                        "client_id": self.org.bb_salesforce_config.client_id,
                        "client_secret": self.org.bb_salesforce_config.client_secret,
                        "redirect_uri": REDIRECT_URI,
                        "code_verifier": example_code_verifier,
                    }
                )
            ],
        )

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-get-token")
        response = self.client.get(
            url,
            {"organization_id": str(self.org.id), "code": example_code},
            content_type="application/json",
        )

        #  Assertion
        assert response.status_code == 500
        assert response.json()["response"] == {"failure": "bad bad bad"}

    @responses.activate
    def test_verify_token(self):
        # Set Up
        example_access_token = "example access token"
        set_cache_raw(f"access_token_{self.org.id}", example_access_token)

        responses.add(
            responses.GET,
            f"{self.salesforce_url}/oauth2/userinfo",
            status=200,
            match=[matchers.query_param_matcher({"access_token": example_access_token, "format": "json"})],
        )

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-verify-token") + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")

        #  Assertion
        assert response.status_code == 200
        assert response.json()["valid"]

    def test_verify_token_no_token(self):
        # Set Up
        example_access_token = None
        set_cache_raw(f"access_token_{self.org.id}", example_access_token)

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-verify-token") + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")

        #  Assertion
        assert response.status_code == 200
        assert not response.json()["valid"]

    @responses.activate
    def test_verify_token_old_token(self):
        # Set Up
        example_access_token = "example access token"
        set_cache_raw(f"access_token_{self.org.id}", "example access token")

        responses.add(
            responses.GET,
            f"{self.salesforce_url}/oauth2/userinfo",
            status=400,
            match=[matchers.query_param_matcher({"access_token": example_access_token, "format": "json"})],
        )

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-verify-token") + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")

        #  Assertion
        assert response.status_code == 200
        assert not response.json()["valid"]

    @responses.activate
    def test_partners(self):
        # Set Up
        example_access_token = "example access token"
        set_cache_raw(f"access_token_{self.org.id}", "example access token")

        responses.add(
            responses.GET,
            f"{self.salesforce_url}/data/v64.0/query?",
            json={
                "records": [
                    {
                        "Id": "partner 1 id",
                        "Name": "partner 1 name",
                        "Goals__r": None,
                    },
                    {
                        "Id": "partner 2 id",
                        "Name": "partner 2 name",
                        "Goals__r": {
                            "records": [
                                {
                                    "Id": "goal 1 id",
                                    "Name": "goal 1 name",
                                },
                                {
                                    "Id": "goal 2 id",
                                    "Name": "goal 2 name",
                                },
                            ]
                        },
                    },
                ]
            },
            status=200,
            match=[
                matchers.query_param_matcher({"q": "SELECT Id,  Name, (SELECT Id, Name FROM Goals__r) FROM Account"}),
                matchers.header_matcher({"Authorization": f"Bearer {example_access_token}"}),
            ],
        )

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-partners") + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")

        #  Assertion
        assert response.status_code == 200
        assert response.json()["results"] == [
            {
                "id": "partner 1 id",
                "name": "partner 1 name",
                "goals": [],
            },
            {
                "id": "partner 2 id",
                "name": "partner 2 name",
                "goals": [
                    {
                        "id": "goal 1 id",
                        "name": "goal 1 name",
                    },
                    {
                        "id": "goal 2 id",
                        "name": "goal 2 name",
                    },
                ],
            },
        ]

    @responses.activate
    def test_annual_report(self):
        # Set Up
        example_access_token = "example access token"
        set_cache_raw(f"access_token_{self.org.id}", example_access_token)

        responses.add(
            responses.GET,
            f"{self.salesforce_url}/data/v64.0/query?",
            json={
                "records": [
                    {
                        "Id": "annual_report 1 id",
                        "Name": "annual_report 1 name",
                    },
                    {
                        "Id": "annual_report 2 id",
                        "Name": "annual_report 2 name",
                    },
                ]
            },
            status=200,
            match=[
                matchers.query_param_matcher(
                    {"q": f"SELECT Id,  Name FROM Annual_Report__c WHERE BB_Goal__c = '{self.example_salesforce_goal_id}'"}  # noqa: S608
                ),
                matchers.header_matcher({"Authorization": f"Bearer {example_access_token}"}),
            ],
        )

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-annual-report")
        response = self.client.get(url, {"organization_id": str(self.org.id), "goal_id": self.goal.id}, content_type="application/json")

        #  Assertion
        assert response.status_code == 200
        assert response.json()["results"] == [
            {
                "id": "annual_report 1 id",
                "name": "annual_report 1 name",
            },
            {
                "id": "annual_report 2 id",
                "name": "annual_report 2 name",
            },
        ]

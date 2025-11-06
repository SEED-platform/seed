"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from urllib.parse import quote_plus

import responses
from django.urls import reverse_lazy
from responses import matchers

from seed.models import BBSalesforceConfig
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.cache import get_cache_raw, set_cache_raw
from seed.views.v3.bb_salesforce import REDIRECT_URI


class BBSalesforceViewSetTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        self.bb_salesforce_config = BBSalesforceConfig.objects.create(
            organization=self.org,
            salesforce_url="http://test.com",
            client_id=1,
            client_secret=1,
        )

    @responses.activate
    def test_login_url(self):
        # Set Up
        example_code_verifier = "example_code_verifier"
        example_code_challenge = "example_code_challenge"
        responses.add(
            responses.GET,
            "http://test.com/oauth2/pkce/generator",
            json={"code_verifier": example_code_verifier, "code_challenge": example_code_challenge},
            status=200,
        )

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-login-url") + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")

        #  Assertion
        assert response.status_code == 200
        assert (
            response.json()["url"] == f"{self.bb_salesforce_config.salesforce_url}/oauth2/authorize?"
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
            "http://test.com/oauth2/token",
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
            "http://test.com/oauth2/token",
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
            "http://test.com/oauth2/userinfo",
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
            "http://test.com/oauth2/userinfo",
            status=400,
            match=[matchers.query_param_matcher({"access_token": example_access_token, "format": "json"})],
        )

        # Action
        url = reverse_lazy("api:v3:bb_salesforce-verify-token") + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")

        #  Assertion
        assert response.status_code == 200
        assert not response.json()["valid"]

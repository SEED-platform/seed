"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

import requests
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from requests.models import PreparedRequest
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request, get_bb_salesforce_config
from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import Goal
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema, swagger_auto_schema_org_query_param
from seed.utils.cache import get_cache_raw, set_cache_raw

logger = logging.getLogger(__name__)

REDIRECT_URI_ENDING = "/app/#/salesforce_login"


def _get_redirect_uri():
    """Get the redirect URI, falling back to localhost if no site is configured."""
    try:
        current_site = Site.objects.get_current()
        if current_site and current_site.domain:
            # Check if domain contains 'example.com' (misconfigured)
            if "example.com" in current_site.domain:
                return "https://127.0.0.1:8000"
            # check if raw AWS domain
            elif "us-east-1.elb.amazonaws.com" in current_site.domain:
                # TODO - TEMPORARY
                # will need to use ENV VAR to define the domain name b/c right now
                # it's coming in as the raw AWS domain
                # right now assume we are on dev1
                return "https://dev1.seed-platform.org"
            else:
                return f"https://{current_site.domain}"
        else:
            return "https://127.0.0.1:8000"
    except Exception:
        return "https://127.0.0.1:8000"


def _get_pkce(bb_salesforce_config):
    response = requests.get(f"{bb_salesforce_config.salesforce_url}/oauth2/pkce/generator", timeout=10)
    return response.json()["code_verifier"], response.json()["code_challenge"]


def is_valid_url(url):
    validator = URLValidator()
    try:
        validator(url)
        return True
    except ValidationError:
        return False


class BBSalesforceViewSet(viewsets.ViewSet, OrgMixin):
    @swagger_auto_schema_org_query_param
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
        ]
    )
    @get_bb_salesforce_config
    @action(detail=False, methods=["GET"])
    def login_url(self, request, bb_salesforce_config):
        # we are going to need the code_verifier when the user has logged in and wants a token

        org_id = request.query_params.get("organization_id")

        # validate URL
        if not is_valid_url(bb_salesforce_config.salesforce_url):
            return JsonResponse({"status": "error", "message": "Invalid Salesforce URL"}, status=status.HTTP_400_BAD_REQUEST)

        code_verifier, code_challenge = _get_pkce(bb_salesforce_config)
        set_cache_raw(f"code_verifier_{org_id}", code_verifier)

        redirect_uri = _get_redirect_uri()  # Get the redirect URI dynamically
        if "us-east-1.elb.amazonaws.com" in redirect_uri:
            # TODO: TEMPORARY
            # will need to use ENV VAR to define the domain name b/c right now
            # it's coming in as the raw AWS domain
            redirect_uri = "https://dev1.seed-platform.org"
        logger.warning(f"BB SALESFORCE REDIRECT URI: {redirect_uri + REDIRECT_URI_ENDING}")

        request = PreparedRequest()
        request.prepare_url(
            url=f"{bb_salesforce_config.salesforce_url}/oauth2/authorize",
            params={
                "client_id": bb_salesforce_config.client_id,
                "redirect_uri": redirect_uri + REDIRECT_URI_ENDING,
                "response_type": "code",
                "code_challenge": code_challenge,
            },
        )

        return JsonResponse({"status": "success", "url": request.url}, status=status.HTTP_200_OK)

    @swagger_auto_schema_org_query_param
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
        ]
    )
    @get_bb_salesforce_config
    @action(detail=False, methods=["GET"])
    def logout(self, request, bb_salesforce_config):
        org_id = request.query_params.get("organization_id")
        # delete access_token
        set_cache_raw(f"access_token_{org_id}", None)

        return JsonResponse({"status": "success", "response": "access token deleted"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_string_field("org_id", required=True, description="org_id"),
            AutoSchemaHelper.query_string_field("code", required=True, description="code received from calling url given by /login_url"),
        ],
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
        ]
    )
    @get_bb_salesforce_config
    @action(detail=False, methods=["GET"])
    def get_token(self, request, bb_salesforce_config):
        org_id = request.query_params.get("organization_id")
        # get the cached code validator
        code = request.query_params.get("code")
        code_verifier = get_cache_raw(f"code_verifier_{org_id}")

        redirect_uri = _get_redirect_uri()  # Get the redirect URI dynamically

        # request a token
        response = requests.post(
            f"{bb_salesforce_config.salesforce_url}/oauth2/token",
            params={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": bb_salesforce_config.client_id,
                "client_secret": bb_salesforce_config.client_secret,
                "redirect_uri": redirect_uri + REDIRECT_URI_ENDING,
                "code_verifier": code_verifier,
            },
            headers={"accept": "application/json"},
            timeout=300,
        )

        if response.status_code != 200:
            return JsonResponse({"status": "error", "response": response.json()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # save access_token
        access_token = response.json()["access_token"]
        set_cache_raw(f"access_token_{org_id}", access_token, 60 * 60 * 24)

        return JsonResponse({"status": "success", "response": "access token created"}, status=status.HTTP_200_OK)

    @swagger_auto_schema_org_query_param
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
        ]
    )
    @action(detail=False, methods=["GET"])
    @get_bb_salesforce_config
    def verify_token(self, request, bb_salesforce_config):
        org_id = request.query_params.get("organization_id")
        access_token = get_cache_raw(f"access_token_{org_id}")

        # check if you ever had a token
        if access_token is None:
            return JsonResponse({"status": "success", "valid": False, "message": "No existing token"}, status=status.HTTP_200_OK)

        # validate URL
        if not is_valid_url(bb_salesforce_config.salesforce_url):
            return JsonResponse({"status": "success", "valid": False, "message": "Invalid Salesforce URL"}, status=status.HTTP_200_OK)

        # check the token is still valid
        response = requests.get(
            f"{bb_salesforce_config.salesforce_url}/oauth2/userinfo",
            params={
                "access_token": access_token,
                "format": "json",
            },
            headers={"accept": "application/json"},
            timeout=300,
        )

        if response.status_code == 200:
            return JsonResponse({"status": "success", "valid": True, "message": "Token is Valid"}, status=status.HTTP_200_OK)

        return JsonResponse({"status": "success", "valid": False, "message": "access token is not valid"}, status=status.HTTP_200_OK)

    @swagger_auto_schema_org_query_param
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
        ]
    )
    @get_bb_salesforce_config
    @action(detail=False, methods=["GET"])
    def partners(self, request, bb_salesforce_config):
        org_id = request.query_params.get("organization_id")
        access_token = get_cache_raw(f"access_token_{org_id}")

        # check the token is still valid
        response = requests.get(
            f"{bb_salesforce_config.salesforce_url}/data/v64.0/query?",
            params={
                "q": "SELECT Id,  Name, (SELECT Id, Name FROM Goals__r) FROM Account",
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=300,
        )

        return JsonResponse(
            {
                "status": "success",
                "results": [
                    {
                        "id": partner["Id"],
                        "name": partner["Name"],
                        "goals": []
                        if partner["Goals__r"] is None
                        else [
                            {
                                "id": goal["Id"],
                                "name": goal["Name"],
                            }
                            for goal in partner["Goals__r"]["records"]
                        ],
                    }
                    for partner in response.json()["records"]
                ],
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(True),
            AutoSchemaHelper.query_integer_field("goal_id", False, "Property ID"),
        ]
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
        ]
    )
    @get_bb_salesforce_config
    @action(detail=False, methods=["GET"])
    def annual_report(self, request, bb_salesforce_config):
        # get goal
        try:
            goal = Goal.objects.get(pk=request.query_params.get("goal_id"))
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."})

        # ensure salesforce goal is attached
        salesforce_goal_id = goal.salesforce_goal_id
        if salesforce_goal_id is None:
            return JsonResponse({"status": "error", "message": "No attached salesforce goal."})

        # get annual reports
        org_id = request.query_params.get("organization_id")
        access_token = get_cache_raw(f"access_token_{org_id}")
        response = requests.get(
            f"{bb_salesforce_config.salesforce_url}/data/v64.0/query?",
            params={
                "q": f"SELECT Id,  Name FROM Annual_Report__c WHERE BB_Goal__c = '{salesforce_goal_id}'",  # noqa: S608 no fear of sql injection as the id comes from the db, and must be an int
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=300,
        )

        return JsonResponse(
            {
                "status": "success",
                "results": [{"id": annual_report["Id"], "name": annual_report["Name"]} for annual_report in response.json()["records"]],
            },
            status=status.HTTP_200_OK,
        )

"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

import requests
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from requests.models import PreparedRequest
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class, get_bb_salesforce_config
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import Goal
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema, swagger_auto_schema_org_query_param
from seed.utils.cache import get_cache_raw, set_cache_raw

logger = logging.getLogger(__name__)
REDIRECT_URI = "https://127.0.0.1:8000"


def _get_pkce(bb_salesforce_config):
    logger.error("+++++++")
    logger.error(f"{bb_salesforce_config.salesforce_url}/oauth2/pkce/generator")
    logger.error("+++++++")
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
    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=["GET"])
    @has_perm_class("requires_member")
    @get_bb_salesforce_config
    def login_url(self, request, bb_salesforce_config):
        # we are going to need the code_verifier when the user has logged in and wants a token

        org_id = request.query_params.get('organization_id')

        # validate URL
        if not is_valid_url(bb_salesforce_config.salesforce_url):
            return JsonResponse({"status": "error", "message": "Invalid Salesforce URL"}, status=status.HTTP_400_BAD_REQUEST)

        code_verifier, code_challenge = _get_pkce(bb_salesforce_config)
        set_cache_raw(f"code_verifier_{org_id}", code_verifier)

        request = PreparedRequest()
        request.prepare_url(
            url=f"{bb_salesforce_config.salesforce_url}/oauth2/authorize",
            params={
                "client_id": bb_salesforce_config.client_id,
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "code_challenge": code_challenge,
            },
        )

        return JsonResponse({"status": "success", "url": request.url}, status=status.HTTP_200_OK)

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=["GET"])
    @has_perm_class("requires_member")
    @get_bb_salesforce_config
    def logout(self, request, bb_salesforce_config):
        org_id = request.query_params.get('organization_id')
        # delete access_token
        set_cache_raw(f"access_token_{org_id}", None)

        return JsonResponse({"status": "success", "response": "access token deleted"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_string_field("org_id", required=True, description="org_id"),
            AutoSchemaHelper.query_string_field("code", required=True, description="code received from calling url given by /login_url"),
        ],
    )
    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=["GET"])
    @has_perm_class("requires_member")
    @get_bb_salesforce_config
    def get_token(self, request, bb_salesforce_config):
        org_id = request.query_params.get('organization_id')
        # get the cached code validator
        code = request.query_params.get("code")
        code_verifier = get_cache_raw(f"code_verifier_{org_id}")
        # request a token
        response = requests.post(
            f"{bb_salesforce_config.salesforce_url}/oauth2/token",
            params={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": bb_salesforce_config.client_id,
                "client_secret": bb_salesforce_config.client_secret,
                "redirect_uri": REDIRECT_URI,
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
    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=["GET"])
    @has_perm_class("requires_member")
    @get_bb_salesforce_config
    def verify_token(self, request, bb_salesforce_config):

        org_id = request.query_params.get('organization_id')
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
    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=["GET"])
    @has_perm_class("requires_member")
    @get_bb_salesforce_config
    def partners(self, request, bb_salesforce_config):
        org_id = request.query_params.get('organization_id')
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

    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=["GET"])
    @has_perm_class("requires_member")
    @get_bb_salesforce_config
    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(True),
            AutoSchemaHelper.query_integer_field("goal_id", False, "Property ID"),
        ]
    )
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
        org_id = request.query_params.get('organization_id')
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

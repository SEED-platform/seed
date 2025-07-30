"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

import requests
from django.http import JsonResponse
from requests.models import PreparedRequest
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema, swagger_auto_schema_org_query_param
from seed.utils.cache import get_cache_raw, set_cache_raw

logger = logging.getLogger(__name__)

BASE_URL =
CLIENT_ID =
CLIENT_SECRET =
REDIRECT_URI =


def _get_pkce():
    response = requests.get(f"{BASE_URL}/oauth2/pkce/generator")

    return response.json()["code_verifier"], response.json()["code_challenge"]


class SalesforceViewSet(viewsets.ViewSet, OrgMixin):
    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=["GET"])
    @has_perm_class("requires_member")
    def login_url(self, request):
        # we are going to need the code_verifier when the user has logged in and wants a token
        code_verifier, code_challenge = _get_pkce()
        set_cache_raw("code_verifier", code_verifier)

        request = PreparedRequest()
        request.prepare_url(
            url=f"{BASE_URL}/oauth2/authorize",
            params={
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "code_challenge": code_challenge,
            },
        )

        return JsonResponse({"status": "success", "url": request.url}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_string_field("org_id", required=True, description="org_id"),
            AutoSchemaHelper.query_string_field("code", required=True, description="code recieved from calling url given by /login_url"),
        ],
    )
    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=["GET"])
    @has_perm_class("requires_member")
    def get_token(self, request):
        # get the cached code validator
        code = request.query_params.get("code")
        code_verifier = get_cache_raw("code_verifier")

        # request a token
        response = requests.post(
            f"{BASE_URL}/oauth2/token",
            params={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": code_verifier,
            },
            headers={"accept": "application/json"},
        )

        if response.status_code != 200:
            return JsonResponse({"status": "error", "response": response.json()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # save access_token
        access_token = response.json()["access_token"]
        logger.error("+++++")
        logger.error(access_token)
        logger.error("+++++")
        set_cache_raw("access_token", access_token, 60 * 60 * 24)

        return JsonResponse({"status": "success", "response": "access token created"}, status=status.HTTP_200_OK)

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=["GET"])
    @has_perm_class("requires_member")
    def verify_token(self, request):
        access_token = get_cache_raw("access_token")

        # check if you ever had a token
        if access_token is None:
            return JsonResponse({"status": "success", "valid": False, "message": "No existing token"}, status=status.HTTP_200_OK)

        # check the token is still valid
        response = requests.get(
            f"{BASE_URL}/oauth2/userinfo",
            params={
                "access_token": access_token,
                "format": "json",
            },
            headers={"accept": "application/json"},
        )

        logger.error("+++++++")
        logger.error(response.status_code)
        logger.error("+++++++")

        if response.status_code == 200:
            return JsonResponse({"status": "success", "valid": True, "message": "Token is Valid"}, status=status.HTTP_200_OK)

        return JsonResponse({"status": "success", "valid": False, "message": "access token is not valid"}, status=status.HTTP_200_OK)

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=["GET"])
    @has_perm_class("requires_member")
    def partners(self, request):
        access_token = get_cache_raw("access_token")

        # check the token is still valid
        response = requests.get(
            f"{BASE_URL}/data/v64.0/query?",
            params={
                "q": "SELECT Id,  Name, (SELECT Id, Name FROM Goals__r) FROM Account",
            },
            headers={"Authorization": f"Bearer {access_token}"},
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

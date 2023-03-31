# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import logging

import requests
from django.conf import settings

from seed.building_sync import validation_client
from seed.lib.superperms.orgs.models import Organization

_log = logging.getLogger(__name__)


class AuditTemplate(object):

    HOST = settings.AUDIT_TEMPLATE_HOST
    API_URL = f'{HOST}/api/v2'

    def __init__(self, org_id):
        self.org_id = org_id

    def get_building(self, audit_template_building_id):
        token, message = self.get_api_token()
        if not token:
            return None, message
        url = f'{self.API_URL}/building_sync/download/rp/buildings/{audit_template_building_id}.xml?token={token}'
        headers = {'accept': 'application/xml'}

        try:
            response = requests.request("GET", url, headers=headers)
            if response.status_code != 200:
                return None, f'Expected 200 response from Audit Template but got {response.status_code}: {response.content}'
        except Exception as e:
            return None, f'Unexpected error from Audit Template: {e}'

        return response, ""

    def get_api_token(self):
        org = Organization.objects.get(pk=self.org_id)
        if not org.at_organization_token or not org.audit_template_user or not org.audit_template_password:
            return None, 'An Audit Template organization token, user email and password are required!'
        url = f'{self.API_URL}/users/authenticate'
        json = {
            'organization_token': org.at_organization_token,
            'email': org.audit_template_user,
            'password': org.audit_template_password
        }
        headers = {"Content-Type": "application/json; charset=utf-8", 'accept': 'application/xml'}

        try:
            response = requests.request("POST", url, headers=headers, json=json)
            if response.status_code != 200:
                return None, f'Expected 200 response from Audit Template but got {response.status_code}: {response.content}'
        except Exception as e:
            return None, f'Unexpected error from Audit Template: {e}'

        try:
            response_body = response.json()
        except ValueError:
            raise validation_client.ValidationClientException(f"Expected JSON response from Audit Template: {response.text}")

        return response_body['token'], ""

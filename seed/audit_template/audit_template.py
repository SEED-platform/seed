# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import logging
import json


import requests
from django.conf import settings
from celery import shared_task

from seed.building_sync import validation_client
from seed.lib.superperms.orgs.models import Organization
from seed.models import PropertyView

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
        return self.get_building_xml(audit_template_building_id, token)
    
    def get_building_xml(self, audit_template_building_id, token):
        url = f'{self.API_URL}/building_sync/download/rp/buildings/{audit_template_building_id}.xml?token={token}'
        headers = {'accept': 'application/xml'}

        try:
            response = requests.request("GET", url, headers=headers)
            if response.status_code != 200:
                return None, f'Expected 200 response from Audit Template but got {response.status_code}: {response.content}'
        except Exception as e:
            return None, f'Unexpected error from Audit Template: {e}'

        return response, ""
        
    def get_buildings(self, cycle_id):
        token, message = self.get_api_token()
        if not token:
            return None, message
        url = f'{self.API_URL}/rp/buildings?token={token}'
        headers = {'accept': 'application/xml'}

        return _get_buildings.delay(cycle_id, url, headers)
    
    def batch_get_building_xml(self, properties):
        token, message = self.get_api_token()
        if not token:
            return None, message
        url = f'{self.API_URL}/rp/buildings?token={token}'
        headers = {'accept': 'application/xml'}

        return _batch_get_building_xml.delay(self.org_id, token, properties)


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

@shared_task
def _get_buildings(cycle_id, url, headers):
    logging.error(">>> _GET_BUILDINGS CELERY")
    try:
        response = requests.request("GET", url, headers=headers)
        if response.status_code !=200:
            return None, f'Exected 200 response from Audit Template but got {response.status_code}: {response.content}'
    except Exception as e:
        return None, f'Unexpected error from Audit Template: {e}'
    logging.error('>>> GOT RESPONSE')
    at_buildings = response.json()
    result = []

    for b in at_buildings:
        view = PropertyView.objects.filter(cycle=cycle_id, state__audit_template_building_id=b['id']).first()
        if view:
            # xml, _ = AuditTemplate(org_id).get_building_xml(b['id'], token)
            result.append({'property_view': view.id, 'audit_template_building_id': b['id'] })
            # result.append({'property_view': view.id, 'audit_template_building_id': b['id'], 'xml': xml.text })

    return json.dumps(result), ""

@shared_task
def _batch_get_building_xml(org_id, token, properties):
    logging.error('>>> _batch_get_building_xml')
    result = []
    for property in properties:
        audit_template_building_id = property["audit_template_building_id"]
        # view = PropertyView.objects.filter(cycle=cycle_id, state__audit_template_building_id=property['id']).first()
        xml, _ = AuditTemplate(org_id).get_building_xml(property['audit_template_building_id'], token)
        result.append({'property_view': property['property_view'], 'audit_template_building_id': audit_template_building_id, 'xml': xml.text })

    return json.dumps(result), ""
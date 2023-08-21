# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
import logging

from django.db.models import Q
import requests
from celery import shared_task
from django.conf import settings
from datetime import datetime

from seed.building_sync import validation_client
from seed.lib.progress_data.progress_data import ProgressData
from seed.lib.superperms.orgs.models import Organization
from seed.models import PropertyView
from seed.views.v3.properties import PropertyViewSet

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
                return None, f'Expected 200 response from Audit Template get_building_xml but got {response.status_code}: {response.content}'
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

    def batch_get_building_xml(self, cycle_id, properties):
        token, message = self.get_api_token()
        if not token:
            return None, message
        progress_data = ProgressData(func_name='batch_get_building_xml', unique_id=self.org_id)
        progress_data.total = len(properties) * 2
        progress_data.save()

        _batch_get_building_xml.delay(self.org_id, cycle_id, token, properties, progress_data.key)

        return progress_data.result()

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
                return None, f'Expected 200 response from Audit Template get_api_token but got {response.status_code}: {response.content}'
        except Exception as e:
            return None, f'Unexpected error from Audit Template: {e}'

        try:
            response_body = response.json()
        except ValueError:
            raise validation_client.ValidationClientException(f"Expected JSON response from Audit Template: {response.text}")

        return response_body['token'], ""


@shared_task
def _get_buildings(cycle_id, url, headers):
    try:
        response = requests.request("GET", url, headers=headers)
        if response.status_code != 200:
            return None, f'Expected 200 response from Audit Template get_buildings but got {response.status_code}: {response.content}'
    except Exception as e:
        return None, f'Unexpected error from Audit Template: {e}'
    at_buildings = response.json()
    result = []
    for b in at_buildings:
        # Only update properties that have been recently updated on Audit Template
        at_updated = datetime.fromisoformat(b['updated_at']).strftime("%Y-%m-%d %I:%M %p")
        at_updated_condition = ~Q(state__extra_data__at_updated_at=at_updated) | Q(state__extra_data__at_updated_at__isnull=True)
        at_building_id_condition = Q(state__audit_template_building_id=b['id'])
        cycle_condition = Q(cycle=cycle_id)
        query = at_updated_condition & at_building_id_condition & cycle_condition

        view = PropertyView.objects.filter(query).first()
        if view:
            email = b['owner'].get('email') if b.get('owner') else 'n/a'
            result.append({
                'audit_template_building_id': b['id'],
                'email': email,
                'name': b['name'],
                'property_view': view.id,
                'updated_at': at_updated,
            })

    return json.dumps(result), ""


@shared_task
def _batch_get_building_xml(org_id, cycle_id, token, properties, progress_key):
    progress_data = ProgressData.from_key(progress_key)
    result = []

    for property in properties:
        audit_template_building_id = property["audit_template_building_id"]
        xml, _ = AuditTemplate(org_id).get_building_xml(property['audit_template_building_id'], token)
        result.append({
            'property_view': property['property_view'],
            'audit_template_building_id': audit_template_building_id,
            'xml': xml.text,
            'updated_at': property['updated_at']
        })
        progress_data.step('Getting XML for buildings...')

    # Call the PropertyViewSet to update the property view with xml data
    property_view_set = PropertyViewSet()
    property_view_set.batch_update_with_building_sync(result, org_id, cycle_id, progress_data.key)

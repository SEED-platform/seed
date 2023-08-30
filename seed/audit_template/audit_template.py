# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
import logging
from datetime import datetime

import requests
from celery import shared_task
from django.conf import settings
from django.db.models import Q
from lxml import etree
from lxml.builder import ElementMaker
from quantityfield.units import ureg

from seed.building_sync import validation_client
from seed.lib.progress_data.progress_data import ProgressData
from seed.lib.superperms.orgs.models import Organization
from seed.models import PropertyView
from seed.views.v3.properties import PropertyViewSet
from seed.building_sync.mappings import BUILDINGSYNC_URI, NAMESPACES

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
    
    def batch_export_to_audit_template(self, states):
        results = {'success': [], 'failure': []}
        for state in states:
            response, message = self.export_to_audit_template(state)
            if response:
                results['success'].append({state.id: response}) 
            else:
                results['failure'].append({state.id: message})
        
        return results

    def export_to_audit_template(self, state):
        org = Organization.objects.get(pk=self.org_id)
        url = f'{self.API_URL}/building_sync/upload'
        token, message = self.get_api_token()
        if not token:
            return None, message
        
        try:
            xml_string, _ = self.build_xml(state, org.audit_template_report_type)
            if not xml_string:
                return None, 'Unable to create xml from property state'
        except Exception as e:
            return None, f'Unexpected error creating building xml {e}'

        try:    
            files = {'audit_file': ('at_export.xml', xml_string)}
            body = {'token': token}
            response = requests.post(url, data=body, files=files)
            if response.status_code != 200:
                return None, f'Expected 200 response from Audit Template upload but got {response.status_code}: {response.content}'
        except Exception as e:
            return None, f'Unexpected error from Audit Template: {e}'
        
        return response, ''
    
    def build_xml(self, state, report_type):
        view = state.propertyview_set.first()

        gfa = state.gross_floor_area
        if type(gfa) == int:
            gross_floor_area = str(gfa)
        elif gfa.units != ureg.feet**2:
            gross_floor_area = str(gfa.to(ureg.feet ** 2).magnitude)
        else:
            gross_floor_area = str(gfa.magnitude)

        XSI_URI = 'http://www.w3.org/2001/XMLSchema-instance'
        nsmap = {
            'xsi': XSI_URI,
        }
        nsmap.update(NAMESPACES)
        E = ElementMaker(
            namespace=BUILDINGSYNC_URI,
            nsmap=nsmap
        )
        doc = (
            E.BuildingSync(
                {
                    etree.QName(XSI_URI,
                                'schemaLocation'): 'http://buildingsync.net/schemas/bedes-auc/2019 https://raw.github.com/BuildingSync/schema/v2.3.0/BuildingSync.xsd',
                    'version': '2.3.0'
                },
                E.Facilities(
                    E.Facility(
                        {'ID': 'Facility-69909846999990'},
                        E.Sites(
                            E.Site(
                                {'ID': 'SiteType-69909846999991'},
                                E.Buildings(
                                    E.Building(
                                        {'ID': 'BuildingType-69909846999992'},
                                        E.PremisesName(state.property_name),
                                        E.PremisesNotes('Note-1'),
                                        E.PremisesIdentifiers(
                                            E.PremisesIdentifier(
                                                E.IdentifierLabel('Custom'),
                                                E.IdentifierCustomName('SEED Property View ID'),
                                                E.IdentifierValue(str(view.id))
                                            )
                                        ),
                                        E.Address(
                                            E.StreetAddressDetail(
                                                E.Simplified(
                                                    E.StreetAddress(state.address_line_1)
                                                ),
                                            ),
                                            E.City(state.city),
                                            E.State(state.state),
                                            E.PostalCode(str(state.postal_code)),
                                        ),
                                        E.FloorAreas(
                                            E.FloorArea(
                                                E.FloorAreaType('Gross'),
                                                E.FloorAreaValue(gross_floor_area),
                                            ),
                                        ),
                                        E.YearOfConstruction(str(state.year_built)),
                                    )
                                )
                            )
                        ),
                        E.Reports(
                            E.Report(
                                {'ID': "ReportType-69909846999993"},
                                E.LinkedPremisesOrSystem(
                                    E.Building(
                                        E.LinkedBuildingID ({'IDref': "BuildingType-69909846999992"})
                                    ),
                                ),
                                E.UserDefinedFields(
                                    E.UserDefinedField(
                                        E.FieldName('Audit Template Report Type'),
                                        E.FieldValue(report_type),
                                    ),
                                )
                            )
                        )
                    )
                )
            )
        )

        return etree.tostring(doc, pretty_print=True).decode('utf-8'), []


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
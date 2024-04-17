# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
import logging
from datetime import datetime
from typing import Any, Tuple

import requests
from celery import shared_task
from django.conf import settings
from django.db.models import Q
from lxml import etree
from lxml.builder import ElementMaker
from quantityfield.units import ureg

from seed.building_sync import validation_client
from seed.building_sync.mappings import BUILDINGSYNC_URI, NAMESPACES
from seed.lib.progress_data.progress_data import ProgressData
from seed.lib.superperms.orgs.models import Organization
from seed.models import PropertyView
from seed.utils.encrypt import decrypt
from seed.views.v3.properties import PropertyViewSet

_log = logging.getLogger(__name__)


class AuditTemplate:
    HOST = settings.AUDIT_TEMPLATE_HOST
    API_URL = f"{HOST}/api/v2"

    def __init__(self, org_id):
        self.org_id = org_id

    def get_building(self, audit_template_building_id):
        token, message = self.get_api_token()
        if not token:
            return None, message
        return self.get_building_xml(audit_template_building_id, token)

    def get_building_xml(self, audit_template_building_id, token):
        url = f"{self.API_URL}/building_sync/download/rp/buildings/{audit_template_building_id}.xml?token={token}"
        headers = {"accept": "application/xml"}

        try:
            response = requests.request("GET", url, headers=headers)
            if response.status_code != 200:
                return (
                    None,
                    f"Expected 200 response from Audit Template get_building_xml but got {response.status_code}: {response.content}",
                )
        except Exception as e:
            return None, f"Unexpected error from Audit Template: {e}"

        return response, ""

    def get_submission(self, audit_template_submission_id: int, report_format: str = "pdf") -> Tuple[Any, str]:
        """Download an Audit Template submission report.

        Args:
            audit_template_submission_id (int): value of the "Submission ID" as seen on Audit Template
            report_format (str, optional): Report format, either `json`, `xml`, or `pdf`. Defaults to 'pdf'.

        Returns:
            requests.response: Result from Audit Template website
        """
        # supporting 'JSON', PDF', and 'XML' formats only for now
        token, message = self.get_api_token()
        if not token:
            return None, message

        # validate format
        if report_format.lower() not in {"json", "xml", "pdf"}:
            report_format = "pdf"

        # set headers
        accept_type = "application/" + report_format.lower()
        headers = {"accept": accept_type}

        url = f"{self.API_URL}/rp/submissions/{audit_template_submission_id}.{report_format}?token={token}"
        try:
            response = requests.request("GET", url, headers=headers)

            if response.status_code != 200:
                return (
                    None,
                    f"Expected 200 response from Audit Template get_submission but got {response.status_code!r}: {response.content!r}",
                )
        except Exception as e:
            return None, f"Unexpected error from Audit Template: {e}"

        return response, ""

    def get_buildings(self, cycle_id):
        token, message = self.get_api_token()
        if not token:
            return None, message
        url = f"{self.API_URL}/rp/buildings?token={token}"
        headers = {"accept": "application/xml"}

        return _get_buildings.delay(cycle_id, url, headers)

    def batch_get_building_xml(self, cycle_id, properties):
        token, message = self.get_api_token()
        if not token:
            return None, message
        progress_data = ProgressData(func_name="batch_get_building_xml", unique_id=self.org_id)
        progress_data.total = len(properties) * 2
        progress_data.save()

        _batch_get_building_xml.delay(self.org_id, cycle_id, token, properties, progress_data.key)

        return progress_data.result()

    def get_api_token(self):
        org = Organization.objects.get(pk=self.org_id)
        if not org.at_organization_token or not org.audit_template_user or not org.audit_template_password:
            return None, "An Audit Template organization token, user email and password are required!"
        url = f"{self.API_URL}/users/authenticate"
        # Send data as form-data to handle special characters like '%'
        form_data = {
            "organization_token": (None, org.at_organization_token),
            "email": (None, org.audit_template_user),
            "password": (None, decrypt(org.audit_template_password)[0]),
        }
        headers = {"Accept": "application/xml"}

        try:
            response = requests.request("POST", url, headers=headers, files=form_data)
            if response.status_code != 200:
                return None, f"Expected 200 response from Audit Template get_api_token but got {response.status_code}: {response.content}"
        except Exception as e:
            return None, f"Unexpected error from Audit Template: {e}"

        try:
            response_body = response.json()
        except ValueError:
            raise validation_client.ValidationClientError(f"Expected JSON response from Audit Template: {response.text}")

        return response_body["token"], ""

    def batch_export_to_audit_template(self, view_ids):
        token, message = self.get_api_token()
        if not token:
            return None, message
        progress_data = ProgressData(func_name="batch_export_to_audit_template", unique_id=view_ids[0])
        progress_data.total = len(view_ids)
        progress_data.save()

        _batch_export_to_audit_template.delay(self.org_id, view_ids, token, progress_data.key)

        return progress_data.result(), []

    def export_to_audit_template(self, state, token):
        org = Organization.objects.get(pk=self.org_id)
        url = f"{self.API_URL}/building_sync/upload"
        display_field = getattr(state, org.property_display_field)

        if state.audit_template_building_id:
            return None, ["info", f"{display_field}: Existing Audit Template Property"]

        try:
            xml_string, messages = self.build_xml(state, org.audit_template_report_type, display_field)
            if not xml_string:
                return None, messages
        except Exception as e:
            return None, ["error", f"{display_field}: Unexpected error creating building xml {e}"]

        try:
            files = {"audit_file": ("at_export.xml", xml_string)}
            body = {"token": token}
            response = requests.request("POST", url, data=body, files=files)
            if response.status_code != 200:
                return None, [
                    "error",
                    f"{display_field}: Expected 200 response from Audit Template upload but got {response.status_code}: {response.content}",
                ]
        except Exception as e:
            return None, ["error", f"{display_field}: Unexpected error from Audit Template: {e}"]

        return response, []

    def validate_state_for_xml(self, state, display_field):
        missing_fields = []
        expected_fields = ["address_line_1", "city", "gross_floor_area", "postal_code", "property_name", "state", "year_built"]
        for field in expected_fields:
            if getattr(state, field) is None:
                missing_fields.append(field)

        if len(missing_fields):
            missing_fields = ", ".join(missing_fields)
            messages = ["error", f"Validation Error. {display_field} must have {missing_fields}"]
            return False, messages

        return True, []

    def build_xml(self, state, report_type, display_field):
        valid, messages = self.validate_state_for_xml(state, display_field)
        if not valid:
            return None, messages

        view = state.propertyview_set.first()

        gfa = state.gross_floor_area
        if isinstance(gfa, int):
            gross_floor_area = str(gfa)
        elif gfa.units != ureg.feet**2:
            gross_floor_area = str(gfa.to(ureg.feet**2).magnitude)
        else:
            gross_floor_area = str(gfa.magnitude)

        XSI_URI = "http://www.w3.org/2001/XMLSchema-instance"
        nsmap = {
            "xsi": XSI_URI,
        }
        nsmap.update(NAMESPACES)
        E = ElementMaker(namespace=BUILDINGSYNC_URI, nsmap=nsmap)
        doc = E.BuildingSync(
            {
                etree.QName(
                    XSI_URI, "schemaLocation"
                ): "http://buildingsync.net/schemas/bedes-auc/2019 https://raw.github.com/BuildingSync/schema/v2.3.0/BuildingSync.xsd",
                "version": "2.3.0",
            },
            E.Facilities(
                E.Facility(
                    {"ID": "Facility-69909846999990"},
                    E.Sites(
                        E.Site(
                            {"ID": "SiteType-69909846999991"},
                            E.Buildings(
                                E.Building(
                                    {"ID": "BuildingType-69909846999992"},
                                    E.PremisesName(state.property_name),
                                    E.PremisesNotes("Note-1"),
                                    E.PremisesIdentifiers(
                                        E.PremisesIdentifier(
                                            E.IdentifierLabel("Custom"),
                                            E.IdentifierCustomName("SEED Property View ID"),
                                            E.IdentifierValue(str(view.id)),
                                        )
                                    ),
                                    E.Address(
                                        E.StreetAddressDetail(
                                            E.Simplified(E.StreetAddress(state.address_line_1)),
                                        ),
                                        E.City(state.city),
                                        E.State(state.state),
                                        E.PostalCode(str(state.postal_code)),
                                    ),
                                    E.FloorAreas(
                                        E.FloorArea(
                                            E.FloorAreaType("Gross"),
                                            E.FloorAreaValue(gross_floor_area),
                                        ),
                                    ),
                                    E.YearOfConstruction(str(state.year_built)),
                                )
                            ),
                        )
                    ),
                    E.Reports(
                        E.Report(
                            {"ID": "ReportType-69909846999993"},
                            E.LinkedPremisesOrSystem(
                                E.Building(E.LinkedBuildingID({"IDref": "BuildingType-69909846999992"})),
                            ),
                            E.UserDefinedFields(
                                E.UserDefinedField(
                                    E.FieldName("Audit Template Report Type"),
                                    E.FieldValue(report_type),
                                ),
                            ),
                        )
                    ),
                )
            ),
        )

        return etree.tostring(doc, pretty_print=True).decode("utf-8"), []

    def update_export_results(self, view_id, results, status, **extra_fields):
        results.setdefault(status, {"count": 0, "details": []})
        results[status]["count"] += 1
        results[status]["details"].append({"view_id": view_id, **extra_fields})


@shared_task
def _get_buildings(cycle_id, url, headers):
    try:
        response = requests.request("GET", url, headers=headers)
        if response.status_code != 200:
            return None, f"Expected 200 response from Audit Template get_buildings but got {response.status_code}: {response.content}"
    except Exception as e:
        return None, f"Unexpected error from Audit Template: {e}"
    at_buildings = response.json()
    result = []
    for b in at_buildings:
        # Only update properties that have been recently updated on Audit Template
        at_updated = datetime.fromisoformat(b["updated_at"]).strftime("%Y-%m-%d %I:%M %p")
        at_updated_condition = ~Q(state__extra_data__at_updated_at=at_updated) | Q(state__extra_data__at_updated_at__isnull=True)
        at_building_id_condition = Q(state__audit_template_building_id=b["id"])
        cycle_condition = Q(cycle=cycle_id)
        query = at_updated_condition & at_building_id_condition & cycle_condition

        view = PropertyView.objects.filter(query).first()
        if view:
            email = b["owner"].get("email") if b.get("owner") else "n/a"
            result.append(
                {
                    "audit_template_building_id": b["id"],
                    "email": email,
                    "name": b["name"],
                    "property_view": view.id,
                    "updated_at": at_updated,
                }
            )

    return json.dumps(result), ""


@shared_task
def _batch_get_building_xml(org_id, cycle_id, token, properties, progress_key):
    progress_data = ProgressData.from_key(progress_key)
    result = []

    for property in properties:
        audit_template_building_id = property["audit_template_building_id"]
        xml, _ = AuditTemplate(org_id).get_building_xml(property["audit_template_building_id"], token)
        result.append(
            {
                "property_view": property["property_view"],
                "audit_template_building_id": audit_template_building_id,
                "xml": xml.text,
                "updated_at": property["updated_at"],
            }
        )
        progress_data.step("Getting XML for buildings...")

    # Call the PropertyViewSet to update the property view with xml data
    property_view_set = PropertyViewSet()
    property_view_set.batch_update_with_building_sync(result, org_id, cycle_id, progress_data.key)


@shared_task
def _batch_export_to_audit_template(org_id, view_ids, token, progress_key):
    audit_template = AuditTemplate(org_id)
    progress_data = ProgressData.from_key(progress_key)
    views = PropertyView.objects.filter(id__in=view_ids, state__organization_id=org_id).select_related("state")
    results = {}

    for view in views:
        state = view.state
        response, messages = audit_template.export_to_audit_template(state, token)

        if not response:
            audit_template.update_export_results(view.id, results, messages[0], message=messages[1])
            progress_data.step("Exporting properties to Audit Template...")

            continue

        at_building_id = None
        for k, v in response.json()["rp_buildings"].items():
            if "BuildingType-" in k:
                at_building_id = v.split("/")[-1]
                break

        if at_building_id:
            state.audit_template_building_id = at_building_id
            state.save()
            audit_template.update_export_results(view.id, results, "success", at_building_id=at_building_id)
        else:
            audit_template.update_export_results(view.id, results, "error", message="Unexpected Response from Audit Template")

        progress_data.update_summary(results)
        progress_data.step("Exporting properties to Audit Template...")

    progress_data.finish_with_success(results)

"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
import logging
import re
from functools import wraps

import requests
from celery import shared_task
from dateutil import parser
from django.conf import settings
from django.utils.timezone import get_current_timezone
from django_celery_beat.models import CrontabSchedule, PeriodicTask
from lxml import etree
from lxml.builder import ElementMaker
from quantityfield.units import ureg
from tkbl import bsync_by_uniformat_code

from seed.analysis_pipelines.better.buildingsync import SEED_TO_BSYNC_RESOURCE_TYPE
from seed.building_sync import validation_client
from seed.building_sync.mappings import BUILDINGSYNC_URI, NAMESPACES
from seed.data_importer.utils import kbtu_thermal_conversion_factors
from seed.lib.progress_data.progress_data import ProgressData
from seed.lib.superperms.orgs.models import Organization
from seed.lib.tkbl.tkbl import EISA432_CODES
from seed.models import Element, Measure, Meter, MeterReading, PropertyView
from seed.utils.encrypt import decrypt

_log = logging.getLogger(__name__)

AUTO_SYNC_NAME = "audit_template_sync_org-"

# Currently default version is the latest version.
# Need to keep this version in sync with Audit Template
AT_BUILDINGSYNC_VERSION = settings.BUILDINGSYNC_VERSION


def require_token(fn):
    """Decorator to get an AT api token"""

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        if not self.token:
            token, message = self.get_api_token()
            if not token:
                return None, message
        return fn(self, *args, **kwargs)

    return wrapper


def schedule_sync(data, org_id):
    timezone = data.get("timezone", get_current_timezone())

    if "update_at_hour" in data and "update_at_minute" in data:
        # create crontab schedule
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=data["update_at_minute"],
            hour=data["update_at_hour"],
            day_of_week=data["update_at_day"],
            day_of_month="*",
            month_of_year="*",
            timezone=timezone,
        )

        # then schedule task (create/update with new crontab)
        tasks = PeriodicTask.objects.filter(name=AUTO_SYNC_NAME + str(org_id))
        if not tasks:
            PeriodicTask.objects.create(
                crontab=schedule, name=AUTO_SYNC_NAME + str(org_id), task="seed.tasks.sync_audit_template", args=json.dumps([org_id])
            )
        else:
            task = tasks.first()
            # update crontab (if changed)
            task.crontab = schedule
            task.save()

            # Cleanup orphaned/unused crontab schedules
            CrontabSchedule.objects.exclude(id__in=PeriodicTask.objects.values_list("crontab_id", flat=True)).delete()


def toggle_audit_template_sync(audit_template_sync_enabled, org_id):
    """when audit_template_sync_enabled value is toggled, also toggle the auto sync
    task status if it exists
    """
    tasks = PeriodicTask.objects.filter(name=AUTO_SYNC_NAME + str(org_id))
    if tasks:
        task = tasks.first()
        task.enabled = bool(audit_template_sync_enabled)
        task.save()


class AuditTemplate:
    HOST = settings.AUDIT_TEMPLATE_HOST
    API_URL = f"{HOST}/api/v2"
    token = None

    def __init__(self, org_id):
        self.org_id = org_id
        self.org = Organization.objects.get(id=self.org_id)

    def batch_get_city_submission_xml(self, view_ids):
        """
        1. get city_cubmissions
        2. find views using xml fields custom_id_1 and updated for cycle start/end bounds
        3. get xmls corresponding to submissions matching a view
        4. group data by cycles
        5. update cycle grouped views in cycle batches

        if param view_ids is empty [], all SEED properties will be used to determine the correct PropertyView
        """
        progress_data = ProgressData(func_name="batch_get_city_submission_xml", unique_id=self.org_id)

        _batch_get_city_submission_xml.delay(self.org_id, self.org.audit_template_city_id, view_ids, progress_data.key)

        return progress_data.result(), ""

    def get_city_submission_xml(self, custom_id_1):
        progress_data = ProgressData(func_name="get_city_submission_xml", unique_id=self.org_id)

        _get_city_submission_xml.delay(self.org_id, self.org.audit_template_city_id, custom_id_1, progress_data.key)

        return progress_data.result(), ""

    @require_token
    def get_submission(self, audit_template_submission_id: int, report_format: str = "pdf"):
        """Download an Audit Template submission report.

        Args:
            audit_template_submission_id (int): value of the "Submission ID" as seen on Audit Template
            report_format (str, optional): Report format, either `json`, `xml`, or `pdf`. Defaults to 'pdf'.

        Returns:
            requests.response: Result from Audit Template website
        """
        # supporting 'JSON', PDF', and 'XML' formats only for now
        # validate format
        if report_format.lower() not in {"json", "xml", "pdf"}:
            report_format = "pdf"

        # set headers
        accept_type = "application/" + report_format.lower()
        headers = {"accept": accept_type}

        url = f"{self.API_URL}/rp/submissions/{audit_template_submission_id}.{report_format}?token={self.token}"
        try:
            response = requests.request("GET", url, headers=headers, timeout=60)

            if response.status_code != 200:
                return (
                    None,
                    f"Expected 200 response from Audit Template get_submission but got {response.status_code!r}: {response.content!r}",
                )
        except Exception as e:
            return None, f"Unexpected error from Audit Template: {e}"

        return response, ""

    @require_token
    def get_city_submissions(self, city_id, status_types):
        """Return all submissions for a city"""

        headers = {"accept": "application/xml"}
        url = f"{self.API_URL}/rp/cities/{city_id}?token={self.token}"
        per_page = 100
        idx = 1
        submissions = []
        params = {"per_page": per_page}
        valid_statuses = ["Complies", "Pending", "Received", "Rejected"]
        # return all submissions for all selected status types
        for status_type in status_types.split(","):
            if status_type not in valid_statuses:
                continue

            params["status"] = status_type
            try:
                # AT submissions are paginated (max per_page = 100). Loop through all pages to return all submissions
                while True:
                    params["page"] = idx
                    response = requests.request("GET", url, headers=headers, params=params, timeout=60)
                    # Raise an exception for non 2XX responses
                    response.raise_for_status()

                    data = response.json()
                    submissions.extend(data)
                    if len(data) < per_page:
                        break
                    idx += 1

            except Exception as e:
                return None, f"Unexpected error from Audit Template: {e}"

        return submissions, ""

    def get_api_token(self):
        if not self.org.at_organization_token or not self.org.audit_template_user or not self.org.audit_template_password:
            return None, "An Audit Template organization token, user email and password are required!"

        url = f"{self.API_URL}/users/authenticate"
        # Send data as form-data to handle special characters like '%'
        form_data = {
            "organization_token": (None, self.org.at_organization_token),
            "email": (None, self.org.audit_template_user),
            "password": (None, decrypt(self.org.audit_template_password)[0]),
        }
        headers = {"Accept": "application/xml"}

        try:
            response = requests.request("POST", url, headers=headers, files=form_data, timeout=60)
            if response.status_code != 200:
                return None, f"Expected 200 response from Audit Template get_api_token but got {response.status_code}: {response.content}"
        except Exception as e:
            return None, f"Unexpected error from Audit Template: {e}"

        try:
            response_body = response.json()
        except ValueError:
            raise validation_client.ValidationClientError(f"Expected JSON response from Audit Template: {response.text}")

        # instead of pinging AT for tokens every time, use existing token.
        self.token = response_body.get("token")
        return self.token, ""

    @require_token
    def batch_export_to_audit_template(self, view_ids):
        progress_data = ProgressData(func_name="batch_export_to_audit_template", unique_id=self.org_id)
        progress_data.total = len(view_ids)
        progress_data.save()

        _batch_export_to_audit_template.delay(self.org_id, view_ids, self.token, progress_data.key)

        return progress_data.result(), []

    def export_to_audit_template(self, state, token, file_only=False):
        url = f"{self.API_URL}/building_sync/upload"
        display_field = getattr(state, self.org.property_display_field)

        if state.audit_template_building_id:
            return None, ["info", f"{display_field}: Existing Audit Template Property"]

        try:
            xml_string, messages = self.build_xml(state, self.org.audit_template_report_type, display_field)

            if not xml_string:
                return None, messages
            if file_only:
                return xml_string, messages
        except Exception as e:
            return None, ["error", f"{display_field}: Unexpected error creating building xml {e}"]

        try:
            files = {"audit_file": ("at_export.xml", xml_string)}
            body = {"token": token}
            response = requests.request("POST", url, data=body, files=files, timeout=60)
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
        expected_fields = ["gross_floor_area", "postal_code", "property_name", "year_built"]
        for field in expected_fields:
            if getattr(state, field) is None:
                missing_fields.append(field)

        if missing_fields:
            missing_fields = ", ".join(missing_fields)
            messages = ["error", f"Validation Error. {display_field} must have {missing_fields}"]
            return False, messages

        return True, []

    def build_xml(self, state, report_type, display_field):
        valid, messages = self.validate_state_for_xml(state, display_field)
        if not valid:
            return None, messages

        view = state.propertyview_set.first()
        org = view.property.organization

        # Retrieve unique tax Identifier to use. Default is custom_ID_1.
        tracking_id = state.custom_id_1
        if org.audit_template_tracking_id_field:
            if org.audit_template_tracking_id_field in state._meta.fields:
                tracking_id = getattr(state, org.audit_template_tracking_id_field)
            elif org.audit_template_tracking_id_field in state.extra_data:
                tracking_id = state.extra_data[org.audit_template_tracking_id_field]

        gfa = state.gross_floor_area
        if isinstance(gfa, int):
            gross_floor_area = str(gfa)
        elif gfa.units != ureg.feet**2:
            gross_floor_area = str(gfa.to(ureg.feet**2).magnitude)
        else:
            gross_floor_area = str(gfa.magnitude)

        # set up some IDs for XML
        facility_id = "Facility-1"
        site_id = "Site-1"
        building_id = "Building-1"
        report_id = "Report-1"

        # TODO: BuildingSync version is very hardcoded here...use env var

        XSI_URI = "http://www.w3.org/2001/XMLSchema-instance"
        nsmap = {
            "xsi": XSI_URI,
        }
        nsmap.update(NAMESPACES)
        em = ElementMaker(namespace=BUILDINGSYNC_URI, nsmap=nsmap)

        doc = em.BuildingSync(
            {
                etree.QName(
                    XSI_URI, "schemaLocation"
                ): f"http://buildingsync.net/schemas/bedes-auc/2019 https://raw.github.com/BuildingSync/schema/v{AT_BUILDINGSYNC_VERSION}/BuildingSync.xsd",
                "version": AT_BUILDINGSYNC_VERSION,
            },
            em.Facilities(
                em.Facility(
                    {"ID": facility_id},
                    em.Sites(
                        em.Site(
                            {"ID": site_id},
                            em.Buildings(
                                em.Building(
                                    {"ID": building_id},
                                    em.PremisesName(state.property_name),
                                    em.PremisesIdentifiers(
                                        em.PremisesIdentifier(
                                            em.IdentifierLabel("Custom"),
                                            em.IdentifierCustomName(org.audit_template_tracking_id_name),
                                            em.IdentifierValue(str(tracking_id)),
                                        )
                                    ),
                                    _build_address(em, state),
                                    em.FloorAreas(
                                        em.FloorArea(
                                            em.FloorAreaType("Gross"),
                                            em.FloorAreaValue(gross_floor_area),
                                        ),
                                    ),
                                    em.YearOfConstruction(str(state.year_built)),
                                )
                            ),
                        )
                    ),
                    *([] if not org.audit_template_export_measures else _build_measures_element(em, view.property.id, building_id)),
                    em.Reports(
                        em.Report(
                            {"ID": report_id},
                            em.Scenarios(
                                *(
                                    []
                                    if not org.audit_template_export_meters
                                    else _build_metering_scenarios(em, view.property.id, building_id)
                                ),
                            ),
                            em.LinkedPremisesOrSystem(
                                em.Building(em.LinkedBuildingID({"IDref": building_id})),
                            ),
                            em.UserDefinedFields(
                                em.UserDefinedField(
                                    em.FieldName("Audit Template Report Type"),
                                    em.FieldValue(report_type),
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


def _build_address(em, state):
    address_elements = []
    if state.address_line_1:
        address_elements.append(
            em.StreetAddressDetail(
                em.Simplified(em.StreetAddress(state.address_line_1)),
            )
        )
    if state.city:
        address_elements.append(em.City(state.city))

    if state.state:
        address_elements.append(em.State(state.state))

    if state.postal_code:
        # add postal code truncated to 5 first digits
        address_elements.append(em.PostalCode(str(state.postal_code[:5])))

    return em.Address(*address_elements)


def _build_metering_scenarios(em, property_id, building_id):
    scenario_base = "Scenario-"
    scenario_counter = 0

    # grab Electricity_GRID meter. if it doesn't exist, then ELECTRICITY meter (AT wants this in kWh)
    meters_elec = Meter.objects.filter(property_id=property_id, type__in=[Meter.ELECTRICITY_GRID, Meter.ELECTRICITY])
    if len(meters_elec) > 1:
        # get ELECTRICITY_GRID
        meters_elec = Meter.objects.filter(property_id=property_id, type=Meter.ELECTRICITY_GRID)

    # make sure there are meterreadings. Right now we are retrieving all readings for this meter
    # TODO: should we be looking at dates here? (get meter data that matches the current cycle?)
    if len(meters_elec) == 0 or meters_elec.first().meter_readings.count() == 0:
        meters_elec = []

    # then grab NATURAL_GAS (AT wants this in therms)
    meters_ng = Meter.objects.filter(property_id=property_id, type__in=[Meter.NATURAL_GAS])
    if len(meters_ng) == 0 or meters_ng.first().meter_readings.count() == 0:
        meters_ng

    # concatenate the meters_elec and meters results
    meters = list(meters_elec) + list(meters_ng)

    # make sure there's at least 1 meter, if not return empty list
    if len(meters) == 0:
        return []

    # create root element
    root = em.RootElement()

    # now make the available energy meter
    scenario_counter += 1
    scenario = em.Scenario(
        {"ID": f"{scenario_base}{scenario_counter}"},
        em.ScenarioName("Audit Template Available Energy"),
        em.TemporalStatus("Current"),
        em.ScenarioType(em.Other()),
        _build_resource_uses(em, property_id, meters, "available", use_meter_ids=False),
        em.LinkedPremises(
            em.Building(em.LinkedBuildingID({"IDref": building_id})),
        ),
        em.UserDefinedFields(
            em.UserDefinedField(
                em.FieldName("Other Scenario Type"),
                em.FieldValue("Audit Template Available Energy"),
            ),
        ),
    )
    root.append(scenario)

    # now make the scenarios with meter data in them (1 per meter)
    for meter in meters:
        scenario_counter += 1
        scenario = em.Scenario(
            {"ID": scenario_base + str(scenario_counter)},
            em.ScenarioName(f"Audit Template Energy Meter Readings - {SEED_TO_BSYNC_RESOURCE_TYPE.get(meter.type, 'Other')}"),
            em.TemporalStatus("Current"),
            em.ScenarioType(em.Other()),
            _build_resource_uses(em, property_id, [meter], "meters", True),
            _build_time_series_data(em, property_id, meter),
            _build_all_resource_totals(em, meter),
            em.LinkedPremises(
                em.Building(em.LinkedBuildingID({"IDref": building_id})),
            ),
            em.UserDefinedFields(
                em.UserDefinedField(
                    em.FieldName("Other Scenario Type"),
                    em.FieldValue("Audit Template Energy Meter Readings"),
                ),
            ),
        )
        root.append(scenario)
    return root


def _build_all_resource_totals(em, meter):
    resource_total_base = "AllResourceTotal-"
    timeseries_id_base = "TimeSeries-"

    # all meter readings are stored in kBtu. Need to be converted to send over to AT
    factors = kbtu_thermal_conversion_factors("US")
    kBtu_to_kWh = factors["Electric"]["kWh (thousand Watt-hours)"]
    kBtu_to_therms = factors["Natural Gas"]["therms"]

    meter_readings = MeterReading.objects.filter(meter_id=meter.id)
    if len(meter_readings) == 0:
        return []

    return em.AllResourceTotals(
        {},
        *[
            em.AllResourceTotal(
                {"ID": f"{resource_total_base}{meter.id}-{i + 1}"},
                em.EndUse("All end uses"),
                em.ResourceBoundary("Site"),
                em.SiteEnergyUse(
                    str(meter_reading.reading / kBtu_to_kWh)
                    if SEED_TO_BSYNC_RESOURCE_TYPE.get(meter.type, "Other")
                    else str(meter_reading.reading / kBtu_to_therms)
                ),
                em.UserDefinedFields(
                    em.UserDefinedField(em.FieldName("Linked Time Series ID"), em.FieldValue(f"{timeseries_id_base}{meter.id}-{i + 1}"))
                ),
            )
            for i, meter_reading in enumerate(meter_readings)
        ],
    )


def _build_time_series_data(em, property_id, meter):
    timeseries_id_base = "TimeSeries-"
    resource_use_base = "ResourceUse-"
    meter_readings = MeterReading.objects.filter(meter_id=meter.id)

    if len(meter_readings) == 0:
        return []

    return em.TimeSeriesData(
        {},
        *[
            em.TimeSeries(
                {"ID": f"{timeseries_id_base}{meter.id}-{i + 1}"},
                em.ReadingType("Peak"),
                em.TimeSeriesReadingQuantity("Voltage"),
                em.StartTimestamp(meter_reading.start_time.isoformat()),
                em.EndTimestamp(meter_reading.end_time.isoformat()),
                # em.IntervalReading(str(meter_reading.reading)),
                em.IntervalFrequency("Other"),
                em.ResourceUseID(
                    {"IDref": f"{resource_use_base}{meter.id}"},
                ),
            )
            for i, meter_reading in enumerate(meter_readings)
        ],
    )


def _build_resource_uses(em, property_id, meters, scenario_type, use_meter_ids=True):
    resource_use_base = "ResourceUse-"
    # for now just pass in electricity and natural gas meters
    # the ResourceUse element in the "Audit Template Available Energy" scenario is slightly
    # different than the one in the "Audit Template Energy Meter Readings" scenario
    # TODO: there could be additional meter types we want to send over to AT in the future
    return em.ResourceUses(
        {},
        *[
            em.ResourceUse(
                {"ID": f"{resource_use_base}{meter.id}" if use_meter_ids else f"{resource_use_base}{i + 1}"},
                em.EnergyResource(SEED_TO_BSYNC_RESOURCE_TYPE.get(meter.type, "Other")),
                em.ResourceBoundary("Site"),
                em.ResourceUnits("kWh" if SEED_TO_BSYNC_RESOURCE_TYPE.get(meter.type, "Other") == "Electricity" else "therms"),
                em.EndUse("All end uses") if scenario_type == "available" else em.SharedResourceSystem("Not shared"),
            )
            for i, meter in enumerate(meters)
        ],
    )


def _build_measures_element(em, property_id, building_id):
    measure_base = "Measure-"
    measure_tuples = _get_measures(property_id)
    if len(measure_tuples) == 0:
        return []

    return [
        em.Measures(
            {},
            *[
                em.Measure(
                    {"ID": f"{measure_base}{i}"},
                    em.LinkedPremises(
                        em.Building(em.LinkedBuildingID({"IDref": building_id})),
                    ),
                    em.TechnologyCategories(
                        {},
                        em.TechnologyCategory(
                            getattr(em, tc)(
                                {},
                                em.MeasureName(mn),
                            )
                        ),
                    ),
                    em.CustomMeasureName(mn),
                    em.LongDescription(mn),
                )
                for i, (tc, mn) in enumerate(_get_measures(property_id))
            ],
        )
    ]


def _get_measures(property_id):
    """Elements/TKBL implementation specific"""
    # TODO: revise this code to be able to export Recommended measures that were added to SEED via Audit Template import?
    tkbl_elements = Element.objects.filter(property_id=property_id, code__code__in=EISA432_CODES).order_by("remaining_service_life")[:3]
    bsync_measure_dicts = [x for e in tkbl_elements for x in bsync_by_uniformat_code(e.code.code)]

    bsync_measure_tuples = set()
    for bsync_measure_dict in bsync_measure_dicts:
        category = Measure.objects.filter(category_display_name=bsync_measure_dict["cat_lev1"]).order_by("-schema_version").first().category
        category = "".join(word.capitalize() for word in category.split("_"))
        # SPECIAL case: HVAC
        category = re.sub(r"Hvac", lambda x: x.group().upper(), category)

        bsync_measure_tuples.add((category, bsync_measure_dict["eem_name"]))

    return bsync_measure_tuples


@shared_task
def _batch_get_city_submission_xml(org_id, city_id, view_ids, progress_key):
    """
    1. get city_cubmissions
    2. find views using xml fields custom_id_1 and updated for cycle start/end bounds
    3. get xmls corresponding to submissions matching a view
    4. group data by cycles
    5. update cycle grouped views in cycle batches
    """
    org = Organization.objects.get(pk=org_id)
    status_types = org.audit_template_status_types
    audit_template = AuditTemplate(org_id)
    progress_data = ProgressData.from_key(progress_key)

    submissions, messages = audit_template.get_city_submissions(city_id, status_types)
    if not submissions:
        progress_data.finish_with_error(messages)
        return None, messages
    # Progress data is difficult to calculate as not all submissions will need an xml
    # Each xml has 2 steps (get and update)
    progress_data.total = len(submissions) * 2
    progress_data.save()

    # Need to specify Cycle. Current implementation uses xml field 'updated_at'
    # ideally use 'audit_date' but 'audit_date' is not a field in the returned AT xml.

    # filering for cycles that contain 'updated_at' makes the query more difficult
    # without placing dates it could be a simple view.filter(state__custom_id_1__in=custom_ids)
    # however that could return multiple views across many cycles
    # filtering by custom_id and 'updated_at' will require looping through results to query views

    property_views = PropertyView.objects.filter(state__organization_id=org_id)
    if view_ids:
        property_views = property_views.filter(id__in=view_ids)

    xml_data_by_cycle = {}
    # TODO: fix this to programmatically determine what tax_id maps to from the audit template org settings
    # TODO: Default is custom_id_1
    for sub in submissions:
        custom_id_1 = sub["tax_id"]
        created_at = parser.parse(sub["created_at"])

        filter_criteria = {
            "property__organization": org_id,
            "state__custom_id_1": custom_id_1,
            "cycle__start__lte": created_at,
            "cycle__end__gte": created_at,
        }

        if org.audit_template_conditional_import:
            updated_at = parser.parse(sub["updated_at"])
            filter_criteria["state__updated__lte"] = updated_at

        view = property_views.filter(**filter_criteria).first()

        progress_data.step("Getting XML for submissions...")
        if view:
            xml, _ = audit_template.get_submission(sub["id"], "xml")

            if hasattr(xml, "text"):
                if not xml_data_by_cycle.get(view.cycle.id):
                    xml_data_by_cycle[view.cycle.id] = []

                xml_data_by_cycle[view.cycle.id].append(
                    {"property_view": view.id, "matching_field": custom_id_1, "xml": xml.text, "updated_at": sub["updated_at"]}
                )

    from seed.views.v3.properties import PropertyViewSet

    property_view_set = PropertyViewSet()
    # Update is cycle based, going to have update in cycle specific batches
    combined_results = {"success": 0, "failure": 0, "data": []}
    try:
        for cycle, xmls in xml_data_by_cycle.items():
            # does progress_data need to be recursively passed?
            results = property_view_set.batch_update_with_building_sync(xmls, org_id, cycle, progress_data.key, finish=False)
            combined_results["success"] += results["success"]
            combined_results["failure"] += results["failure"]
            combined_results["data"].extend(results["data"])
    except Exception:
        progress_data.finish_with_error("Unexepected Error")

    progress_data.finish_with_success(combined_results)


@shared_task
def _get_city_submission_xml(org_id, city_id, custom_id_1, progress_key):
    """
    1. get city_cubmissions
    2. find view using xml fields custom_id_1 and updated for cycle start/end bounds
    3. get xml corresponding to submission matching a view
    4. update view
    """
    org = Organization.objects.get(pk=org_id)
    status_types = org.audit_template_status_types
    audit_template = AuditTemplate(org_id)
    progress_data = ProgressData.from_key(progress_key)

    submissions, messages = audit_template.get_city_submissions(city_id, status_types)
    if not submissions:
        progress_data.finish_with_error(messages)
        return None, messages
    # Progress data is difficult to calculate as not all submissions will need an xml
    # Each xml has 2 steps (get and update)
    progress_data.total = len(submissions) * 2
    progress_data.save()

    submissions = [sub for sub in submissions if sub["tax_id"] == custom_id_1]
    if not len(submissions):
        return progress_data.finish_with_error(f"No matching submissions for custom id: {custom_id_1}")
    sub = submissions[0]
    created_at = parser.parse(sub["created_at"])

    view = PropertyView.objects.filter(
        property__organization=org_id,
        state__custom_id_1=custom_id_1,
        cycle__start__lte=created_at,
        cycle__end__gte=created_at,
    ).first()

    if not view:
        progress_data.finish_with_error("No such resource.")

    progress_data.step("Getting XML for submissions...")
    if view:
        xml, _ = audit_template.get_submission(sub["id"], "xml")
        if hasattr(xml, "text"):
            xmls = [{"property_view": view.id, "matching_field": custom_id_1, "xml": xml.text, "updated_at": sub["updated_at"]}]

    from seed.views.v3.properties import PropertyViewSet

    property_view_set = PropertyViewSet()
    # Update is cycle based, going to have update in cycle specific batches

    try:
        results = property_view_set.batch_update_with_building_sync(xmls, org_id, view.cycle.id, progress_data.key, finish=False)
        if results.get("success"):
            message = {"message": "Successfully updated property"}
        else:
            message = {"message": "Failed to update property"}
    except Exception:
        return progress_data.finish_with_error("Unexepected Error")

    progress_data.finish_with_success(message)


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
            if "Building-" in k:
                at_building_id = v.split("/")[-1]
                break

        if at_building_id:
            state.audit_template_building_id = at_building_id
            state.save()
            audit_template.update_export_results(view.id, results, "success", at_building_id=at_building_id)
        else:
            audit_template.update_export_results(
                view.id, results, "error", message="Unexpected Response from Audit Template. Could not find AT Building ID in response."
            )

        progress_data.update_summary(results)
        progress_data.step("Exporting properties to Audit Template...")

    progress_data.finish_with_success(results)

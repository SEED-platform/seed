"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import contextlib
import functools
import json
import locale
import logging
import operator
from io import BytesIO
from numbers import Number
from pathlib import Path

import numpy as np
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import F, Value
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from xlsxwriter import Workbook

from seed import tasks
from seed.audit_template.audit_template import toggle_audit_template_sync
from seed.data_importer.models import ImportFile, ImportRecord
from seed.data_importer.tasks import save_raw_data
from seed.decorators import ajax_request_class
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.lib.superperms.orgs.models import ROLE_MEMBER, ROLE_OWNER, ROLE_VIEWER, AccessLevelInstance, Organization, OrganizationUser
from seed.models import (
    AUDIT_IMPORT,
    GREEN_BUTTON,
    PORTFOLIO_METER_USAGE,
    SEED_DATA_SOURCES,
    Column,
    Cycle,
    FilterGroup,
    Property,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    ReportConfiguration,
    TaxLot,
    TaxLotAuditLog,
    TaxLotState,
    TaxLotView,
)
from seed.models import StatusLabel as Label
from seed.serializers.column_mappings import SaveColumnMappingsRequestPayloadSerializer
from seed.serializers.columns import ColumnSerializer
from seed.serializers.organizations import SaveSettingsSerializer, SharedFieldsReturnSerializer
from seed.serializers.pint import add_pint_unit_suffix, apply_display_unit_preferences
from seed.serializers.report_configurations import ReportConfigurationSerializer
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.encrypt import decrypt, encrypt
from seed.utils.geocode import geocode_buildings
from seed.utils.match import match_merge_link
from seed.utils.merge import merge_properties
from seed.utils.organizations import create_organization, create_suborganization, set_default_2fa_method
from seed.utils.properties import pair_unpair_property_taxlot
from seed.utils.public import public_feed
from seed.utils.salesforce import toggle_salesforce_sync
from seed.utils.users import get_js_role

_log = logging.getLogger(__name__)


def _dict_org(request, organizations):
    """returns a dictionary of an organization's data."""

    orgs = []
    for o in organizations:
        org_cycles = Cycle.objects.filter(organization=o).only("id", "name").order_by("name")
        cycles = []
        for c in org_cycles:
            cycles.append(
                {
                    "name": c.name,
                    "cycle_id": c.pk,
                    "num_properties": PropertyView.objects.filter(cycle=c).count(),
                    "num_taxlots": TaxLotView.objects.filter(cycle=c).count(),
                }
            )

        # We don't wish to double count sub organization memberships.
        org_users = (
            OrganizationUser.objects.select_related("user")
            .only("role_level", "user__first_name", "user__last_name", "user__email", "user__id")
            .filter(organization=o)
        )

        owners = []
        role_level = None
        user_is_owner = False
        for ou in org_users:
            if ou.role_level == ROLE_OWNER:
                owners.append({"first_name": ou.user.first_name, "last_name": ou.user.last_name, "email": ou.user.email, "id": ou.user.id})

                if ou.user == request.user:
                    user_is_owner = True

            if ou.user == request.user:
                role_level = get_js_role(ou.role_level)

        org = {
            "name": o.name,
            "org_id": o.id,
            "id": o.id,
            "number_of_users": len(org_users),
            "user_is_owner": user_is_owner,
            "user_role": role_level,
            "owners": owners,
            "sub_orgs": _dict_org(request, o.child_orgs.all()),
            "is_parent": o.is_parent,
            "parent_id": o.parent_id,
            "display_units_eui": o.display_units_eui,
            "display_units_ghg": o.display_units_ghg,
            "display_units_ghg_intensity": o.display_units_ghg_intensity,
            "display_units_water_use": o.display_units_water_use,
            "display_units_wui": o.display_units_wui,
            "display_units_area": o.display_units_area,
            "display_decimal_places": o.display_decimal_places,
            "cycles": cycles,
            "created": o.created.strftime("%Y-%m-%d") if o.created else "",
            "mapquest_api_key": o.mapquest_api_key or "",
            "geocoding_enabled": o.geocoding_enabled,
            "better_analysis_api_key": o.better_analysis_api_key or "",
            "better_host_url": settings.BETTER_HOST,
            "property_display_field": o.property_display_field,
            "taxlot_display_field": o.taxlot_display_field,
            "display_meter_units": dict(sorted(o.display_meter_units.items(), key=lambda item: (item[0], item[1]))),
            "display_meter_water_units": dict(sorted(o.display_meter_water_units.items(), key=lambda item: (item[0], item[1]))),
            "thermal_conversion_assumption": o.thermal_conversion_assumption,
            "comstock_enabled": o.comstock_enabled,
            "new_user_email_from": o.new_user_email_from,
            "new_user_email_subject": o.new_user_email_subject,
            "new_user_email_content": o.new_user_email_content,
            "new_user_email_signature": o.new_user_email_signature,
            "at_organization_token": o.at_organization_token,
            "at_host_url": settings.AUDIT_TEMPLATE_HOST,
            "audit_template_user": o.audit_template_user,
            "audit_template_password": decrypt(o.audit_template_password)[0] if o.audit_template_password else "",
            "audit_template_city_id": o.audit_template_city_id,
            "audit_template_export_meters": o.audit_template_export_meters,
            "audit_template_export_measures": o.audit_template_export_measures,
            "audit_template_conditional_import": o.audit_template_conditional_import,
            "audit_template_report_type": o.audit_template_report_type,
            "audit_template_status_types": o.audit_template_status_types,
            "audit_template_sync_enabled": o.audit_template_sync_enabled,
            "audit_template_tracking_id_name": o.audit_template_tracking_id_name,
            "audit_template_tracking_id_field": o.audit_template_tracking_id_field,
            "salesforce_enabled": o.salesforce_enabled,
            "ubid_threshold": o.ubid_threshold,
            "inventory_count": o.property_set.count() + o.taxlot_set.count(),
            "access_level_names": o.access_level_names,
            "public_feed_enabled": o.public_feed_enabled,
            "public_feed_labels": o.public_feed_labels,
            "public_geojson_enabled": o.public_geojson_enabled,
            "default_reports_x_axis_options": ColumnSerializer(
                Column.objects.filter(organization=o, table_name="PropertyState", is_option_for_reports_x_axis=True), many=True
            ).data,
            "default_reports_y_axis_options": ColumnSerializer(
                Column.objects.filter(organization=o, table_name="PropertyState", is_option_for_reports_y_axis=True), many=True
            ).data,
            "require_2fa": o.require_2fa,
        }
        orgs.append(org)

    return orgs


def _dict_org_brief(request, organizations):
    """returns a brief dictionary of an organization's data."""

    organization_roles = list(OrganizationUser.objects.filter(user=request.user).values("organization_id", "role_level"))

    role_levels = {}
    for r in organization_roles:
        role_levels[r["organization_id"]] = get_js_role(r["role_level"])

    orgs = []
    for o in organizations:
        user_role = None
        with contextlib.suppress(KeyError):
            user_role = role_levels[o.id]

        org = {
            "name": o.name,
            "org_id": o.id,
            "parent_id": o.parent_org_id,
            "is_parent": o.is_parent,
            "id": o.id,
            "user_role": user_role,
            "display_decimal_places": o.display_decimal_places,
            "salesforce_enabled": o.salesforce_enabled,
            "access_level_names": o.access_level_names,
            "audit_template_conditional_import": o.audit_template_conditional_import,
            "property_display_field": o.property_display_field,
            "taxlot_display_field": o.taxlot_display_field,
        }
        orgs.append(org)

    return orgs


class OrganizationViewSet(viewsets.ViewSet):
    # allow using `pk` in url path for authorization (i.e., for has_perm_class)
    authz_org_id_kwarg = "pk"

    @ajax_request_class
    @has_perm_class("requires_owner")
    @action(detail=True, methods=["DELETE"])
    def columns(self, request, pk=None):
        """
        Delete all columns for an organization. This method is typically not recommended if there
        are data in the inventory as it will invalidate all extra_data fields. This also removes
        all the column mappings that existed.

        ---
        parameters:
            - name: pk
              description: The organization_id
              required: true
              paramType: path
        type:
            status:
                description: success or error
                type: string
                required: true
            column_mappings_deleted_count:
                description: Number of column_mappings that were deleted
                type: integer
                required: true
            columns_deleted_count:
                description: Number of columns that were deleted
                type: integer
                required: true
        """
        try:
            org = Organization.objects.get(pk=pk)
            c_count, cm_count = Column.delete_all(org)
            return JsonResponse(
                {
                    "status": "success",
                    "column_mappings_deleted_count": cm_count,
                    "columns_deleted_count": c_count,
                }
            )
        except Organization.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"organization with with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_integer_field("import_file_id", required=True, description="Import file id"),
            openapi.Parameter("id", openapi.IN_PATH, type=openapi.TYPE_INTEGER, description="Organization id"),
        ],
        request_body=SaveColumnMappingsRequestPayloadSerializer,
        responses={200: "success response"},
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_member")
    @has_hierarchy_access(param_import_file_id="import_file_id")
    @action(detail=True, methods=["POST"])
    def column_mappings(self, request, pk=None):
        """
        Saves the mappings between the raw headers of an ImportFile and the
        destination fields in the `to_table_name` model which should be either
        PropertyState or TaxLotState

        Valid source_type values are found in ``seed.models.SEED_DATA_SOURCES``
        """
        import_file_id = request.query_params.get("import_file_id")
        if import_file_id is None:
            return JsonResponse(
                {"status": "error", "message": "Query param `import_file_id` is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            ImportFile.objects.get(pk=import_file_id)
            organization = Organization.objects.get(pk=pk)
        except ImportFile.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No import file found"}, status=status.HTTP_404_NOT_FOUND)
        except Organization.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No organization found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            Column.create_mappings(request.data.get("mappings", []), organization, request.user, import_file_id)
        except PermissionError as e:
            return JsonResponse({"status": "error", "message": str(e)})

        else:
            return JsonResponse({"status": "success"})

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_boolean_field(
                "brief", required=False, description="If true, only return high-level organization details"
            )
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    def list(self, request):
        """
        Retrieves all orgs the user has access to.
        """

        # if brief==true only return high-level organization details
        brief = json.loads(request.query_params.get("brief", "false"))

        if brief:
            if request.user.is_superuser:
                qs = Organization.objects.only(
                    "id", "name", "parent_org_id", "display_decimal_places", "salesforce_enabled", "access_level_names"
                )
            else:
                qs = request.user.orgs.only(
                    "id", "name", "parent_org_id", "display_decimal_places", "salesforce_enabled", "access_level_names"
                )

            orgs = _dict_org_brief(request, qs)
            if len(orgs) == 0:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Your SEED account is not associated with any organizations. Please contact a SEED administrator.",
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            else:
                return JsonResponse({"organizations": orgs})
        else:
            if request.user.is_superuser:
                qs = Organization.objects.all()
            else:
                qs = request.user.orgs.all()

            orgs = _dict_org(request, qs)
            if len(orgs) == 0:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Your SEED account is not associated with any organizations. Please contact a SEED administrator.",
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            else:
                return JsonResponse({"organizations": orgs})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    def destroy(self, request, pk=None):
        """
        Starts a background task to delete an organization and all related data.
        """

        return JsonResponse(tasks.delete_organization_and_inventory(pk))

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    def retrieve(self, request, pk=None):
        """
        Retrieves a single organization by id.
        """
        org_id = pk
        brief = json.loads(request.query_params.get("brief", "false"))

        if org_id is None:
            return JsonResponse({"status": "error", "message": "no organization_id sent"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({"status": "error", "message": "organization does not exist"}, status=status.HTTP_404_NOT_FOUND)
        if (
            not request.user.is_superuser
            and not OrganizationUser.objects.filter(
                user=request.user, organization=org, role_level__in=[ROLE_OWNER, ROLE_MEMBER, ROLE_VIEWER]
            ).exists()
        ):
            # TODO: better permission and return 401 or 403
            return JsonResponse({"status": "error", "message": "user is not the owner of the org"}, status=status.HTTP_403_FORBIDDEN)

        if brief:
            org = _dict_org_brief(request, [org])[0]
        else:
            org = _dict_org(request, [org])[0]

        return JsonResponse(
            {
                "status": "success",
                "organization": org,
            }
        )

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory(
            {
                "organization_name": "string",
                "user_id": "integer",
            },
            required=["organization_name", "user_id"],
            description="Properties:\n"
            "- organization_name: The new organization name\n"
            "- user_id: The user ID (primary key) to be used as the owner of the new organization",
        )
    )
    @api_endpoint_class
    @ajax_request_class
    def create(self, request):
        """
        Creates a new organization.
        """
        body = request.data
        user = User.objects.get(pk=body["user_id"])
        org_name = body["organization_name"]

        if not request.user.is_superuser and request.user.id != user.id:
            return JsonResponse({"status": "error", "message": "not authorized"}, status=status.HTTP_403_FORBIDDEN)

        if Organization.objects.filter(name=org_name).exists():
            return JsonResponse({"status": "error", "message": "Organization name already exists"}, status=status.HTTP_409_CONFLICT)

        org, _, _ = create_organization(user, org_name, org_name)
        return JsonResponse({"status": "success", "message": "Organization created", "organization": _dict_org(request, [org])[0]})

    @api_endpoint_class
    @ajax_request_class
    @method_decorator(permission_required("seed.can_access_admin"))
    @action(detail=True, methods=["DELETE"])
    def inventory(self, request, pk=None):
        """
        Starts a background task to delete all properties & taxlots
        in an org.
        """
        return JsonResponse(tasks.delete_organization_inventory(pk))

    @swagger_auto_schema(
        request_body=SaveSettingsSerializer,
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    @action(detail=True, methods=["PUT"])
    def save_settings(self, request, pk=None):
        """
        Saves an organization's settings: name, query threshold, shared fields, etc
        """
        body = request.data
        org = Organization.objects.get(pk=pk)
        posted_org = body.get("organization", None)
        if posted_org is None:
            return JsonResponse({"status": "error", "message": "malformed request"}, status=status.HTTP_400_BAD_REQUEST)

        desired_threshold = posted_org.get("query_threshold", None)
        if desired_threshold is not None:
            org.query_threshold = desired_threshold

        desired_name = posted_org.get("name", None)
        if desired_name is not None:
            org.name = desired_name

        def is_valid_choice(choice_tuples, s):
            """choice_tuples is std model ((value, label), ...)"""
            return (s is not None) and (s in [choice[0] for choice in choice_tuples])

        def warn_bad_pint_spec(kind, unit_string):
            if unit_string is not None:
                _log.warn(f"got bad {kind} unit string {unit_string} for org {org.name}")

        def warn_bad_units(kind, unit_string):
            _log.warn(f"got bad {kind} unit string {unit_string} for org {org.name}")

        desired_display_units_eui = posted_org.get("display_units_eui")
        if is_valid_choice(Organization.MEASUREMENT_CHOICES_EUI, desired_display_units_eui):
            org.display_units_eui = desired_display_units_eui
        else:
            warn_bad_pint_spec("eui", desired_display_units_eui)

        desired_display_units_ghg = posted_org.get("display_units_ghg")
        if is_valid_choice(Organization.MEASUREMENT_CHOICES_GHG, desired_display_units_ghg):
            org.display_units_ghg = desired_display_units_ghg
        else:
            warn_bad_pint_spec("ghg", desired_display_units_ghg)

        desired_display_units_ghg_intensity = posted_org.get("display_units_ghg_intensity")
        if is_valid_choice(Organization.MEASUREMENT_CHOICES_GHG_INTENSITY, desired_display_units_ghg_intensity):
            org.display_units_ghg_intensity = desired_display_units_ghg_intensity
        else:
            warn_bad_pint_spec("ghg_intensity", desired_display_units_ghg_intensity)

        desired_display_units_water_use = posted_org.get("display_units_water_use")
        if is_valid_choice(Organization.MEASUREMENT_CHOICES_WATER_USE, desired_display_units_water_use):
            org.display_units_water_use = desired_display_units_water_use
        else:
            warn_bad_pint_spec("water_use", desired_display_units_water_use)

        desired_display_units_wui = posted_org.get("display_units_wui")
        if is_valid_choice(Organization.MEASUREMENT_CHOICES_WUI, desired_display_units_wui):
            org.display_units_wui = desired_display_units_wui
        else:
            warn_bad_pint_spec("wui", desired_display_units_wui)

        desired_display_units_area = posted_org.get("display_units_area")
        if is_valid_choice(Organization.MEASUREMENT_CHOICES_AREA, desired_display_units_area):
            org.display_units_area = desired_display_units_area
        else:
            warn_bad_pint_spec("area", desired_display_units_area)

        desired_display_decimal_places = posted_org.get("display_decimal_places")
        if isinstance(desired_display_decimal_places, int) and desired_display_decimal_places >= 0:
            org.display_decimal_places = desired_display_decimal_places
        elif desired_display_decimal_places is not None:
            _log.warn(f"got bad sig figs {desired_display_decimal_places} for org {org.name}")

        desired_display_meter_units = posted_org.get("display_meter_units")
        if desired_display_meter_units:
            org.display_meter_units = desired_display_meter_units

        desired_display_meter_water_units = posted_org.get("display_meter_water_units")
        if desired_display_meter_water_units:
            org.display_meter_water_units = desired_display_meter_water_units

        desired_thermal_conversion_assumption = posted_org.get("thermal_conversion_assumption")
        if is_valid_choice(Organization.THERMAL_CONVERSION_ASSUMPTION_CHOICES, desired_thermal_conversion_assumption):
            org.thermal_conversion_assumption = desired_thermal_conversion_assumption

        # Update MapQuest API Key if it's been changed
        mapquest_api_key = posted_org.get("mapquest_api_key", "")
        if mapquest_api_key != org.mapquest_api_key:
            org.mapquest_api_key = mapquest_api_key

        # Update geocoding_enabled option
        geocoding_enabled = posted_org.get("geocoding_enabled", True)
        if geocoding_enabled != org.geocoding_enabled:
            org.geocoding_enabled = geocoding_enabled

        # Update public_feed_enabled option
        public_feed_enabled = posted_org.get("public_feed_enabled")
        if public_feed_enabled:
            org.public_feed_enabled = True
        elif org.public_feed_enabled:
            org.public_feed_enabled = False
            org.public_feed_labels = False
            org.public_geojson_enabled = False

        # Update public_feed_labels option
        public_feed_labels = posted_org.get("public_feed_labels", False)
        if public_feed_enabled and public_feed_labels != org.public_feed_labels:
            org.public_feed_labels = public_feed_labels

        # Update public_geojson_enabled option
        public_geojson_enabled = posted_org.get("public_geojson_enabled", False)
        if public_feed_enabled and public_geojson_enabled != org.public_geojson_enabled:
            org.public_geojson_enabled = public_geojson_enabled

        # Update BETTER Analysis API Key if it's been changed
        better_analysis_api_key = posted_org.get("better_analysis_api_key", "").strip()
        if better_analysis_api_key != org.better_analysis_api_key:
            org.better_analysis_api_key = better_analysis_api_key

        # Update property_display_field option
        property_display_field = posted_org.get("property_display_field", "address_line_1")
        if property_display_field != org.property_display_field:
            org.property_display_field = property_display_field

        # Update taxlot_display_field option
        taxlot_display_field = posted_org.get("taxlot_display_field", "address_line_1")
        if taxlot_display_field != org.taxlot_display_field:
            org.taxlot_display_field = taxlot_display_field

        # update new user email from option
        new_user_email_from = posted_org.get("new_user_email_from")
        if new_user_email_from != org.new_user_email_from:
            org.new_user_email_from = new_user_email_from
        if not org.new_user_email_from:
            org.new_user_email_from = Organization._meta.get_field("new_user_email_from").get_default()

        # update new user email subject option
        new_user_email_subject = posted_org.get("new_user_email_subject")
        if new_user_email_subject != org.new_user_email_subject:
            org.new_user_email_subject = new_user_email_subject
        if not org.new_user_email_subject:
            org.new_user_email_subject = Organization._meta.get_field("new_user_email_subject").get_default()

        # update new user email content option
        new_user_email_content = posted_org.get("new_user_email_content")
        if new_user_email_content != org.new_user_email_content:
            org.new_user_email_content = new_user_email_content
        if not org.new_user_email_content:
            org.new_user_email_content = Organization._meta.get_field("new_user_email_content").get_default()
        if "{{sign_up_link}}" not in org.new_user_email_content:
            org.new_user_email_content += "\n\nSign up here: {{sign_up_link}}"

        # update new user email signature option
        new_user_email_signature = posted_org.get("new_user_email_signature")
        if new_user_email_signature != org.new_user_email_signature:
            org.new_user_email_signature = new_user_email_signature
        if not org.new_user_email_signature:
            org.new_user_email_signature = Organization._meta.get_field("new_user_email_signature").get_default()

        # update default_reports_x_axis_options
        default_reports_x_axis_options = sorted(posted_org.get("default_reports_x_axis_options", []))
        current_default_reports_x_axis_options = Column.objects.filter(organization=org, is_option_for_reports_x_axis=True).order_by("id")
        if default_reports_x_axis_options != list(current_default_reports_x_axis_options.values_list("id", flat=True)):
            current_default_reports_x_axis_options.update(is_option_for_reports_x_axis=False)
            Column.objects.filter(organization=org, table_name="PropertyState", id__in=default_reports_x_axis_options).update(
                is_option_for_reports_x_axis=True
            )

        # update default_reports_y_axis_options
        default_reports_y_axis_options = sorted(posted_org.get("default_reports_y_axis_options", []))
        current_default_reports_y_axis_options = Column.objects.filter(organization=org, is_option_for_reports_y_axis=True).order_by("id")
        if default_reports_y_axis_options != list(current_default_reports_y_axis_options.values_list("id", flat=True)):
            current_default_reports_y_axis_options.update(is_option_for_reports_y_axis=False)
            Column.objects.filter(organization=org, table_name="PropertyState", id__in=default_reports_y_axis_options).update(
                is_option_for_reports_y_axis=True
            )

        comstock_enabled = posted_org.get("comstock_enabled", False)
        if comstock_enabled != org.comstock_enabled:
            org.comstock_enabled = comstock_enabled

        at_organization_token = posted_org.get("at_organization_token", False)
        if at_organization_token != org.at_organization_token:
            org.at_organization_token = at_organization_token

        audit_template_user = posted_org.get("audit_template_user", False)
        if audit_template_user != org.audit_template_user:
            org.audit_template_user = audit_template_user

        audit_template_tracking_id_name = posted_org.get("audit_template_tracking_id_name", False)
        if audit_template_tracking_id_name != org.audit_template_tracking_id_name:
            org.audit_template_tracking_id_name = audit_template_tracking_id_name

        audit_template_tracking_id_field = posted_org.get("audit_template_tracking_id_field", False)
        if audit_template_tracking_id_field != org.audit_template_tracking_id_field:
            org.audit_template_tracking_id_field = audit_template_tracking_id_field

        audit_template_password = posted_org.get("audit_template_password", False)
        if audit_template_password != org.audit_template_password:
            org.audit_template_password = encrypt(audit_template_password)

        audit_template_report_type = posted_org.get("audit_template_report_type", False)
        if audit_template_report_type != org.audit_template_report_type:
            org.audit_template_report_type = audit_template_report_type

        audit_template_status_types = posted_org.get("audit_template_status_types", False)
        if audit_template_status_types != org.audit_template_status_types:
            org.audit_template_status_types = audit_template_status_types

        audit_template_city_id = posted_org.get("audit_template_city_id", False)
        if audit_template_city_id != org.audit_template_city_id:
            org.audit_template_city_id = audit_template_city_id

        audit_template_export_meters = posted_org.get("audit_template_export_meters", False)
        if audit_template_export_meters != org.audit_template_export_meters:
            org.audit_template_export_meters = audit_template_export_meters

        audit_template_export_measures = posted_org.get("audit_template_export_measures", False)
        if audit_template_export_measures != org.audit_template_export_measures:
            org.audit_template_export_measures = audit_template_export_measures

        audit_template_conditional_import = posted_org.get("audit_template_conditional_import", False)
        if audit_template_conditional_import != org.audit_template_conditional_import:
            org.audit_template_conditional_import = audit_template_conditional_import

        audit_template_sync_enabled = posted_org.get("audit_template_sync_enabled", False)
        if audit_template_sync_enabled != org.audit_template_sync_enabled:
            org.audit_template_sync_enabled = audit_template_sync_enabled
            # if audit_template_sync_enabled was toggled, must start/stop auto sync functionality
            toggle_audit_template_sync(audit_template_sync_enabled, org.id)

        salesforce_enabled = posted_org.get("salesforce_enabled", False)
        if salesforce_enabled != org.salesforce_enabled:
            org.salesforce_enabled = salesforce_enabled
            # if salesforce_enabled was toggled, must start/stop auto sync functionality
            toggle_salesforce_sync(salesforce_enabled, org.id)

        require_2fa = posted_org.get("require_2fa", False)
        if require_2fa != org.require_2fa:
            org.require_2fa = require_2fa
            if require_2fa:
                set_default_2fa_method(org)

        # update the ubid threshold option
        ubid_threshold = posted_org.get("ubid_threshold")
        if ubid_threshold is not None and ubid_threshold != org.ubid_threshold:
            if type(ubid_threshold) not in {float, int} or ubid_threshold < 0 or ubid_threshold > 1:
                return JsonResponse(
                    {"status": "error", "message": "ubid_threshold must be a float between 0 and 1"}, status=status.HTTP_400_BAD_REQUEST
                )

            org.ubid_threshold = ubid_threshold

        org.save()

        # Update the selected exportable fields.
        new_public_column_names = posted_org.get("public_fields", None)
        if new_public_column_names is not None:
            old_public_columns = Column.objects.filter(organization=org, shared_field_type=Column.SHARED_PUBLIC)
            # turn off sharing in the old_pub_fields
            for col in old_public_columns:
                col.shared_field_type = Column.SHARED_NONE
                col.save()

            # for now just iterate over this to grab the new columns.
            for col in new_public_column_names:
                new_col = Column.objects.filter(organization=org, id=col["id"])
                if len(new_col) == 1:
                    new_col = new_col.first()
                    new_col.shared_field_type = Column.SHARED_PUBLIC
                    new_col.save()

        return JsonResponse({"status": "success"})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_member")
    @action(detail=True, methods=["GET"])
    def query_threshold(self, request, pk=None):
        """
        Returns the "query_threshold" for an org.  Searches from
        members of sibling orgs must return at least this many buildings
        from orgs they do not belong to, or else buildings from orgs they
        don't belong to will be removed from the results.
        """
        org = Organization.objects.get(pk=pk)
        return JsonResponse({"status": "success", "query_threshold": org.query_threshold})

    @swagger_auto_schema(responses={200: SharedFieldsReturnSerializer})
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_member")
    @action(detail=True, methods=["GET"])
    def shared_fields(self, request, pk=None):
        """
        Retrieves all fields marked as shared for the organization. Will only return used fields.
        """
        result = {"status": "success", "public_fields": []}

        columns = Column.retrieve_all(pk, "property", True)
        for c in columns:
            if c["sharedFieldType"] == "Public":
                new_column = {
                    "table_name": c["table_name"],
                    "name": c["name"],
                    "column_name": c["column_name"],
                    # this is the field name in the db. The other name can have tax_
                    "display_name": c["display_name"],
                }
                result["public_fields"].append(new_column)

        return JsonResponse(result)

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory(
            {
                "sub_org_name": "string",
                "sub_org_owner_email": "string",
            },
            required=["sub_org_name", "sub_org_owner_email"],
            description="Properties:\n"
            "- sub_org_name: Name of the new sub organization\n"
            "- sub_org_owner_email: Email of the owner of the sub organization, which must already exist",
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_member")
    @action(detail=True, methods=["POST"])
    def sub_org(self, request, pk=None):
        """
        Creates a child org of a parent org.
        """
        body = request.data
        org = Organization.objects.get(pk=pk)
        email = body["sub_org_owner_email"].lower()
        try:
            user = User.objects.get(username=email)
        except User.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"User with email address ({email}) does not exist"}, status=status.HTTP_400_BAD_REQUEST
            )

        created, mess_or_org, _ = create_suborganization(user, org, body["sub_org_name"], ROLE_OWNER)
        if created:
            return JsonResponse({"status": "success", "organization_id": mess_or_org.pk})
        else:
            return JsonResponse({"status": "error", "message": mess_or_org}, status=status.HTTP_409_CONFLICT)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    @action(detail=True, methods=["GET"])
    def matching_criteria_columns(self, request, pk=None):
        """
        Retrieve all matching criteria columns for an org.
        """
        try:
            org = Organization.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve organization at pk = " + str(pk)}, status=status.HTTP_404_NOT_FOUND
            )

        matching_criteria_column_names = dict(
            org.column_set.filter(is_matching_criteria=True)
            .values("table_name")
            .annotate(column_names=ArrayAgg("column_name"))
            .values_list("table_name", "column_names")
        )

        return JsonResponse(matching_criteria_column_names)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_member")
    @action(detail=True, methods=["GET"])
    def geocoding_columns(self, request, pk=None):
        """
        Retrieve all geocoding columns for an org.
        """
        try:
            org = Organization.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve organization at pk = " + str(pk)}, status=status.HTTP_404_NOT_FOUND
            )

        geocoding_columns_qs = org.column_set.filter(geocoding_order__gt=0).order_by("geocoding_order").values("table_name", "column_name")

        geocoding_columns = {
            "PropertyState": [],
            "TaxLotState": [],
        }

        for col in geocoding_columns_qs:
            geocoding_columns[col["table_name"]].append(col["column_name"])

        return JsonResponse(geocoding_columns)

    def _format_property_display_field(self, view, org):
        try:
            return getattr(view.state, org.property_display_field)
        except AttributeError:
            return None

    def setup_report_data(self, organization_id, access_level_instance, cycles, x_var, y_var, filter_group_id=None, additional_columns=[]):
        all_property_views = (
            PropertyView.objects.select_related("property", "state")
            .filter(
                property__organization_id=organization_id,
                property__access_level_instance__lft__gte=access_level_instance.lft,
                property__access_level_instance__rgt__lte=access_level_instance.rgt,
                cycle_id__in=cycles,
            )
            .order_by("id")
        )

        if filter_group_id:
            filter_group = FilterGroup.objects.get(pk=filter_group_id)
            all_property_views = filter_group.views(all_property_views)

        # annotate properties with fields
        def get_column_model_field(column):
            if column in Organization.objects.get(pk=organization_id).access_level_names:
                return F("property__access_level_instance__path__" + column)
            elif column == "Count":
                return Value(1)
            elif column.is_extra_data:
                return F("state__extra_data__" + column.column_name)
            elif column.derived_column:
                return F("state__derived_data__" + column.column_name)
            else:
                return F("state__" + column.column_name)

        fields = {
            **{column.column_name: get_column_model_field(column) for column in additional_columns},
            "x": get_column_model_field(x_var),
            "y": get_column_model_field(y_var),
        }
        for k, v in fields.items():
            all_property_views = all_property_views.annotate(**{k: v})

        return {"all_property_views": all_property_views, "field_data": fields}

    def get_raw_report_data(self, organization_id, cycles, all_property_views, fields):
        organization = Organization.objects.get(pk=organization_id)
        # get data for each cycle
        results = []
        for cycle in cycles:
            property_views = all_property_views.annotate(yr_e=Value(str(cycle.end.year))).filter(cycle_id=cycle)
            data = [apply_display_unit_preferences(organization, d) for d in property_views.values("id", *fields.keys(), "yr_e")]

            # count before and after we prune the empty ones
            # watch out not to prune boolean fields
            count_total = len(data)
            data = [d for d in data if (d["x"] or d["x"] is False or d["x"] is True) and (d["y"] or d["y"] is False or d["y"] is True)]
            count_with_data = len(data)
            result = {
                "cycle_id": cycle.pk,
                "chart_data": data,
                "property_counts": {
                    "yr_e": cycle.end.strftime("%Y"),
                    "num_properties": count_total,
                    "num_properties_w-data": count_with_data,
                },
            }
            results.append(result)
        return results

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_string_field("x_var", required=True, description="Raw column name for x axis"),
            AutoSchemaHelper.query_string_field("y_var", required=True, description="Raw column name for y axis"),
            AutoSchemaHelper.query_string_field(
                "start", required=True, description='Start time, in the format "2018-12-31T23:53:00-08:00"'
            ),
            AutoSchemaHelper.query_string_field("end", required=True, description='End time, in the format "2018-12-31T23:53:00-08:00"'),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    @action(detail=True, methods=["GET"])
    def report(self, request, pk=None):
        """Retrieve a summary report for charting x vs y"""
        params = {
            "x_var": request.query_params.get("x_var", None),
            "y_var": request.query_params.get("y_var", None),
            "access_level_instance_id": request.query_params.get("access_level_instance_id", None),
            "cycle_ids": request.query_params.getlist("cycle_ids", None),
        }

        user_ali = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        filter_group_id = request.query_params.get("filter_group_id", None)
        if params["access_level_instance_id"] is None:
            ali = user_ali
        else:
            try:
                selected_ali = AccessLevelInstance.objects.get(pk=params["access_level_instance_id"])
                if not (selected_ali == user_ali or selected_ali.is_descendant_of(user_ali)):
                    raise AccessLevelInstance.DoesNotExist
            except (AccessLevelInstance.DoesNotExist, AssertionError):
                return Response({"status": "error", "message": "No such ali"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                ali = selected_ali

        excepted_params = ["x_var", "y_var", "cycle_ids"]
        missing_params = [p for p in excepted_params if p not in params]
        if missing_params:
            return Response(
                {"status": "error", "message": f"Missing params: {', '.join(missing_params)}"}, status=status.HTTP_400_BAD_REQUEST
            )

        # x could be an access level, else its a column
        access_level_names = Organization.objects.get(pk=pk).access_level_names
        if params["x_var"] not in access_level_names:
            x_var = Column.objects.get(column_name=params["x_var"], organization=pk, table_name="PropertyState")
        else:
            x_var = params["x_var"]

        # y could be count, else its a column
        if params["y_var"] != "Count":
            y_var = Column.objects.get(column_name=params["y_var"], organization=pk, table_name="PropertyState")
        else:
            y_var = params["y_var"]

        cycles = Cycle.objects.filter(id__in=params["cycle_ids"])
        report_data = self.setup_report_data(pk, ali, cycles, x_var, y_var, filter_group_id)
        data = self.get_raw_report_data(pk, cycles, report_data["all_property_views"], report_data["field_data"])
        axis_data = self.get_axis_data(
            pk, ali, cycles, params["x_var"], params["y_var"], report_data["all_property_views"], report_data["field_data"]
        )

        data = {
            "chart_data": functools.reduce(operator.iadd, [d["chart_data"] for d in data], []),
            "property_counts": [d["property_counts"] for d in data],
            "axis_data": axis_data,
        }

        return Response({"status": "success", "data": data}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_string_field("x_var", required=True, description="Raw column name for x axis"),
            AutoSchemaHelper.query_string_field(
                "y_var",
                required=True,
                description='Raw column name for y axis, must be one of: "gross_floor_area", "property_type", "year_built"',
            ),
            AutoSchemaHelper.query_string_field(
                "start", required=True, description='Start time, in the format "2018-12-31T23:53:00-08:00"'
            ),
            AutoSchemaHelper.query_string_field("end", required=True, description='End time, in the format "2018-12-31T23:53:00-08:00"'),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    @action(detail=True, methods=["GET"])
    def report_aggregated(self, request, pk=None):
        """Retrieve a summary report for charting x vs y aggregated by y_var"""
        # get params
        params = {
            "x_var": request.query_params.get("x_var", None),
            "y_var": request.query_params.get("y_var", None),
            "cycle_ids": request.query_params.getlist("cycle_ids", None),
            "access_level_instance_id": request.query_params.get("access_level_instance_id", None),
        }
        filter_group_id = request.query_params.get("filter_group_id", None)
        user_ali = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        if params["access_level_instance_id"] is None:
            ali = user_ali
        else:
            try:
                selected_ali = AccessLevelInstance.objects.get(pk=params["access_level_instance_id"])
                if not (selected_ali == user_ali or selected_ali.is_descendant_of(user_ali)):
                    raise AccessLevelInstance.DoesNotExist
            except (AccessLevelInstance.DoesNotExist, AssertionError):
                return Response({"status": "error", "message": "No such ali"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                ali = selected_ali

        # error if missing
        missing_params = [p for (p, v) in params.items() if v is None]
        if missing_params:
            return Response(
                {"status": "error", "message": f"Missing params: {', '.join(missing_params)}"}, status=status.HTTP_400_BAD_REQUEST
            )

        # X could be count, else its a column
        if params["x_var"] != "Count":
            x_var = Column.objects.get(column_name=params["x_var"], organization=pk, table_name="PropertyState")
        else:
            x_var = params["x_var"]

        # y could be an access level, else its a column
        access_level_names = Organization.objects.get(pk=pk).access_level_names
        if params["y_var"] not in access_level_names:
            y_var = Column.objects.get(column_name=params["y_var"], organization=pk, table_name="PropertyState")
        else:
            y_var = params["y_var"]

        cycles = Cycle.objects.filter(id__in=params["cycle_ids"])
        report_data = self.setup_report_data(pk, ali, cycles, x_var, y_var, filter_group_id)
        data = self.get_raw_report_data(pk, cycles, report_data["all_property_views"], report_data["field_data"])
        chart_data = []
        property_counts = []

        # set bins and choose agg type. treat booleans as discrete
        ys = [building["y"] for datum in data for building in datum["chart_data"] if building["y"] is not None]
        if ys and isinstance(ys[0], Number) and ys[0] is not True and ys[0] is not False:
            bins = np.histogram_bin_edges(ys, bins=5)

            # special case for year built: make bins integers
            # year built is in x axis, but it shows up in y_var variable
            if params["y_var"] == "year_built":
                bins = bins.astype(int)

            aggregate_data = self.continuous_aggregate_data
        else:
            bins = list(set(ys))
            aggregate_data = self.discrete_aggregate_data

        for datum in data:
            buildings = datum["chart_data"]
            yr_e = datum["property_counts"]["yr_e"]
            chart_data.extend(aggregate_data(yr_e, buildings, bins, count=params["x_var"] == "Count"))
            property_counts.append(datum["property_counts"])

        # Send back to client
        result = {
            "status": "success",
            "aggregated_data": {"chart_data": chart_data, "property_counts": property_counts},
        }

        return Response(result, status=status.HTTP_200_OK)

    def continuous_aggregate_data(self, yr_e, buildings, bins, count=False):
        buildings = [b for b in buildings if b["x"] is not None and b["y"] is not None]
        binplace = np.digitize([b["y"] for b in buildings], bins)
        xs = [b["x"] for b in buildings]

        results = []
        for i in range(len(bins) - 1):
            bin = f"{round(bins[i], 2)} - {round(bins[i + 1], 2)}"
            values = np.array(xs)[np.where(binplace == i + 1)]
            x = sum(values) if count else np.average(values).item()
            results.append({"y": bin, "x": None if np.isnan(x) else x, "yr_e": yr_e})

        return results

    def discrete_aggregate_data(self, yr_e, buildings, bins, count=False):
        xs_by_bin = {bin: [] for bin in bins}

        for building in buildings:
            xs_by_bin[building["y"]].append(building["x"])

        results = []
        for bin, xs in xs_by_bin.items():
            if count:
                x = sum(xs)
            elif len(xs) == 0:
                x = None
            else:
                x = sum(xs) / len(xs)

            results.append({"y": bin, "x": x, "yr_e": yr_e})

        return sorted(results, key=lambda d: d["x"] if d["x"] is not None else -np.inf, reverse=True)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_string_field("x_var", required=True, description="Raw column name for x axis"),
            AutoSchemaHelper.query_string_field("x_label", required=True, description="Label for x axis"),
            AutoSchemaHelper.query_string_field("y_var", required=True, description="Raw column name for y axis"),
            AutoSchemaHelper.query_string_field("y_label", required=True, description="Label for y axis"),
            AutoSchemaHelper.query_string_field(
                "start", required=True, description='Start time, in the format "2018-12-31T23:53:00-08:00"'
            ),
            AutoSchemaHelper.query_string_field("end", required=True, description='End time, in the format "2018-12-31T23:53:00-08:00"'),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    @action(detail=True, methods=["GET"])
    def report_export(self, request, pk=None):
        """
        Export a report as a spreadsheet
        """
        access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)

        # get params
        params = {
            "x_var": request.query_params.get("x_var", None),
            "x_label": request.query_params.get("x_label", None),
            "y_var": request.query_params.get("y_var", None),
            "y_label": request.query_params.get("y_label", None),
            "cycle_ids": request.query_params.getlist("cycle_ids", None),
        }
        filter_group_id = request.query_params.get("filter_group_id", None)

        # error if missing
        excepted_params = ["x_var", "x_label", "y_var", "y_label", "cycle_ids"]
        missing_params = [p for p in excepted_params if p not in params]
        if missing_params:
            return Response(
                {"status": "error", "message": f"Missing params: {', '.join(missing_params)}"}, status=status.HTTP_400_BAD_REQUEST
            )

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="report-data"'

        # Create WB
        output = BytesIO()
        wb = Workbook(output, {"remove_timezone": True})

        # Create sheets
        count_sheet = wb.add_worksheet("Counts")
        base_sheet = wb.add_worksheet("Raw")
        agg_sheet = wb.add_worksheet("Agg")

        # Enable bold format and establish starting cells
        bold = wb.add_format({"bold": True})
        data_row_start = 0
        data_col_start = 0

        # Write all headers across all sheets
        count_sheet.write(data_row_start, data_col_start, "Year Ending", bold)
        count_sheet.write(data_row_start, data_col_start + 1, "Properties with Data", bold)
        count_sheet.write(data_row_start, data_col_start + 2, "Total Properties", bold)

        agg_sheet.write(data_row_start, data_col_start, request.query_params.get("x_label"), bold)
        agg_sheet.write(data_row_start, data_col_start + 1, request.query_params.get("y_label"), bold)
        agg_sheet.write(data_row_start, data_col_start + 2, "Year Ending", bold)

        # Gather base data
        cycles = Cycle.objects.filter(id__in=params["cycle_ids"])
        matching_columns = Column.objects.filter(organization_id=pk, is_matching_criteria=True, table_name="PropertyState")
        x_var = Column.objects.get(column_name=params["x_var"], organization=pk, table_name="PropertyState")
        y_var = Column.objects.get(column_name=params["y_var"], organization=pk, table_name="PropertyState")
        report_data = self.setup_report_data(
            pk, access_level_instance, cycles, x_var, y_var, filter_group_id, additional_columns=matching_columns
        )
        data = self.get_raw_report_data(pk, cycles, report_data["all_property_views"], report_data["field_data"])

        base_sheet.write(data_row_start, data_col_start, "ID", bold)

        for i, matching_column in enumerate(matching_columns):
            base_sheet.write(data_row_start, data_col_start + i, matching_column.display_name, bold)
        base_sheet.write(data_row_start, data_col_start + len(matching_columns) + 0, params["x_label"], bold)
        base_sheet.write(data_row_start, data_col_start + len(matching_columns) + 1, params["y_label"], bold)
        base_sheet.write(data_row_start, data_col_start + len(matching_columns) + 2, "Year Ending", bold)

        base_row = data_row_start + 1
        agg_row = data_row_start + 1
        count_row = data_row_start + 1

        for cycle_results in data:
            total_count = cycle_results["property_counts"]["num_properties"]
            with_data_count = cycle_results["property_counts"]["num_properties_w-data"]
            yr_e = cycle_results["property_counts"]["yr_e"]

            # Write Counts
            count_sheet.write(count_row, data_col_start, yr_e)
            count_sheet.write(count_row, data_col_start + 1, with_data_count)
            count_sheet.write(count_row, data_col_start + 2, total_count)

            count_row += 1

            # Write Base/Raw Data
            data_rows = cycle_results["chart_data"]
            for datum in data_rows:
                del datum["id"]
                for i, k in enumerate(datum.keys()):
                    base_sheet.write(base_row, data_col_start + i, datum.get(k))

                base_row += 1

            # set bins and choose agg type
            ys = [building["y"] for datum in data for building in datum["chart_data"]]
            if ys and isinstance(ys[0], Number):
                bins = np.histogram_bin_edges(ys, bins=5)
                aggregate_data = self.continuous_aggregate_data
            else:
                bins = list(set(ys))
                aggregate_data = self.discrete_aggregate_data

            # Gather and write Agg data
            for agg_datum in aggregate_data(yr_e, data_rows, bins, count=params["x_var"] == "Count"):
                agg_sheet.write(agg_row, data_col_start, agg_datum.get("x"))
                agg_sheet.write(agg_row, data_col_start + 1, agg_datum.get("y"))
                agg_sheet.write(agg_row, data_col_start + 2, agg_datum.get("yr_e"))

                agg_row += 1

        wb.close()

        xlsx_data = output.getvalue()

        response.write(xlsx_data)

        return response

    def get_axis_stats(self, organization, cycle, axis, axis_var, views, ali):
        """returns axis_name, access_level_instance name, sum, mean, min, max, 5%, 25%, 50%, 75%, 99%
        exclude categorical and boolean from stats
        """

        filtered_properties = views.filter(
            property__access_level_instance__lft__gte=ali.lft, property__access_level_instance__rgt__lte=ali.rgt, cycle_id=cycle.id
        )

        data = [
            d[axis]
            for d in [apply_display_unit_preferences(organization, d) for d in filtered_properties.values(axis)]
            if axis in d and d[axis] is not None and d[axis] is not True and d[axis] is not False and isinstance(d[axis], (int, float))
        ]

        if len(data) > 0:
            percentiles = np.percentile(data, [5, 25, 50, 75, 95])
            # order the cols: sum, min, 5%, 25%, mean, median (50%), 75, 95, max
            return [
                axis_var,
                ali.name,
                sum(data),
                np.amin(data),
                percentiles[0],
                percentiles[1],
                np.mean(data),
                percentiles[2],
                percentiles[3],
                percentiles[4],
                np.amax(data),
            ]
        else:
            return [axis_var, ali.name, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    def get_axis_data(self, organization_id, access_level_instance, cycles, x_var, y_var, all_property_views, fields):
        axis_data = {}
        axes = {"x": x_var, "y": y_var}
        organization = Organization.objects.get(pk=organization_id)

        # initialize
        for cycle in cycles:
            axis_data[cycle.name] = {}

        for axis, axis_var in axes.items():
            if axis_var != "Count":
                columns = Column.objects.filter(organization_id=organization_id, column_name=axis_var, table_name="PropertyState")
                if not columns:
                    return {}

                column = columns[0]
                if not column.data_type or column.data_type == "None":
                    data_type = "float"
                else:
                    data_type = Column.DB_TYPES[column.data_type]

                # Get column label
                serialized_column = ColumnSerializer(column).data
                add_pint_unit_suffix(organization, serialized_column)
                for cycle in cycles:
                    name_to_display = (
                        serialized_column["display_name"] if serialized_column["display_name"] != "" else serialized_column["column_name"]
                    )
                    axis_data[cycle.name][name_to_display] = {}
                    stats = self.get_axis_stats(organization, cycle, axis, axis_var, all_property_views, access_level_instance)
                    axis_data[cycle.name][name_to_display]["values"] = self.clean_axis_data(data_type, stats)

                    children = access_level_instance.get_children()
                    if len(children):
                        axis_data[cycle.name][name_to_display]["children"] = {}
                        for child_ali in children:
                            stats = self.get_axis_stats(organization, cycle, axis, axis_var, all_property_views, child_ali)
                            axis_data[cycle.name][name_to_display]["children"][child_ali.name] = self.clean_axis_data(data_type, stats)

        return axis_data

    def clean_axis_data(self, data_type, data):
        if data_type == "float":
            return data[1:3] + np.round(data[3:], decimals=2).tolist()
        elif data_type == "integer":
            return data[1:3] + np.round(data[3:]).tolist()

    @has_perm_class("requires_member")
    @ajax_request_class
    @action(detail=True, methods=["GET"])
    def geocode_api_key_exists(self, request, pk=None):
        """
        Returns true if the organization has a mapquest api key
        """
        org = Organization.objects.get(id=pk)

        return bool(org.mapquest_api_key)

    @has_perm_class("requires_member")
    @ajax_request_class
    @action(detail=True, methods=["GET"])
    def geocoding_enabled(self, request, pk=None):
        """
        Returns the organization's geocoding_enabled setting
        """
        org = Organization.objects.get(id=pk)

        return org.geocoding_enabled

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    @action(detail=True, methods=["POST"])
    def reset_all_passwords(self, request, pk=None):
        """
        Resets all user passwords in organization
        """
        org_users = OrganizationUser.objects.filter(organization=pk).select_related("user")
        for org_user in org_users:
            form = PasswordResetForm({"email": org_user.user.email})
            if form.is_valid():
                org_user.user.password = ""
                org_user.user.save()
                form.save(
                    from_email=settings.PASSWORD_RESET_EMAIL,
                    subject_template_name="landing/password_reset_subject.txt",
                    email_template_name="landing/password_reset_forced_email.html",
                )

        return JsonResponse({"status": "success", "message": "passwords reset"})

    @has_perm_class("requires_superuser")
    @ajax_request_class
    @action(detail=True, methods=["GET"])
    def insert_sample_data(self, request, pk=None):
        """
        Create a button for new users to import data below if no data exists
        """
        org = Organization.objects.get(id=pk)
        cycles = Cycle.objects.filter(organization=org)
        if cycles.count() == 0:
            return JsonResponse({"status": "error", "message": "there must be at least 1 cycle"}, status=status.HTTP_400_BAD_REQUEST)

        cycle = cycles.first()
        if PropertyView.objects.filter(cycle=cycle).count() > 0 or TaxLotView.objects.filter(cycle=cycle).count() > 0:
            return JsonResponse(
                {"status": "error", "message": "the cycle must not contain any properties or tax lots"}, status=status.HTTP_400_BAD_REQUEST
            )

        taxlot_details = {
            "jurisdiction_tax_lot_id": "A-12345",
            "city": "Boring",
            "organization_id": pk,
            "extra_data": {"Note": "This is my first note"},
        }

        taxlot_state = TaxLotState(**taxlot_details)
        taxlot_state.save()
        taxlot_1 = TaxLot.objects.create(organization=org)
        taxview = TaxLotView.objects.create(taxlot=taxlot_1, cycle=cycle, state=taxlot_state)

        TaxLotAuditLog.objects.create(organization=org, state=taxlot_state, record_type=AUDIT_IMPORT, name="Import Creation")

        filename_pd = "property_sample_data.json"
        filepath_pd = f"{Path(__file__).parent.absolute()}/../../tests/data/{filename_pd}"

        with open(filepath_pd, encoding=locale.getpreferredencoding(False)) as file:
            property_details = json.load(file)

        property_views = []
        properties = []
        ids = []
        for dic in property_details:
            dic["organization_id"] = pk

            state = PropertyState(**dic)
            state.save()
            ids.append(state.id)

            property_1 = Property.objects.create(organization=org)
            properties.append(property_1)
            propertyview = PropertyView.objects.create(property=property_1, cycle=cycle, state=state)
            property_views.append(propertyview)

            # create labels and add to records
            new_label, _created = Label.objects.get_or_create(color="red", name="Housing", super_organization=org)
            if state.extra_data.get("Note") == "Residential":
                propertyview.labels.add(new_label)

            PropertyAuditLog.objects.create(organization=org, state=state, record_type=AUDIT_IMPORT, name="Import Creation")

            # Geocoding - need mapquest API (should add comment for new users)
            geocode = PropertyState.objects.filter(id__in=ids)
            geocode_buildings(geocode)

        # Create a merge of the last 2 properties
        state_ids_to_merge = ids[-2:]
        merged_state = merge_properties(state_ids_to_merge, pk, "Manual Match")
        view = merged_state.propertyview_set.first()
        match_merge_link(merged_state, view.property.access_level_instance, view.cycle)

        # pair a property to tax lot
        property_id = property_views[0].id
        taxlot_id = taxview.id
        pair_unpair_property_taxlot(property_id, taxlot_id, org, True)

        # create column for Note
        Column.objects.get_or_create(
            organization=org,
            table_name="PropertyState",
            column_name="Note",
            is_extra_data=True,  # Column objects representing raw/header rows are NEVER extra data
        )

        import_record = ImportRecord.objects.create(name="Auto-Populate", super_organization=org, access_level_instance=self.org.root)

        # Interval Data
        filename = "PM Meter Data.xlsx"  # contains meter data for bsyncr and BETTER
        filepath = f"{Path(__file__).parent.absolute()}/data/{filename}"

        with open(filepath, "rb") as content:
            import_meterdata = ImportFile.objects.create(
                import_record=import_record,
                source_type=SEED_DATA_SOURCES[PORTFOLIO_METER_USAGE][1],
                uploaded_filename=filename,
                file=SimpleUploadedFile(name=filename, content=content.read()),
                cycle=cycle,
            )

        save_raw_data(import_meterdata.id)

        # Greenbutton Import
        filename = "example-GreenButton-data.xml"
        filepath = f"{Path(__file__).parent.absolute()}/data/{filename}"

        with open(filepath, "rb") as content:
            import_greenbutton = ImportFile.objects.create(
                import_record=import_record,
                source_type=SEED_DATA_SOURCES[GREEN_BUTTON][1],
                uploaded_filename=filename,
                file=SimpleUploadedFile(name=filename, content=content.read()),
                cycle=cycle,
                matching_results_data={"property_id": properties[7].id},
            )

        save_raw_data(import_greenbutton.id)

        return JsonResponse({"status": "success"})

    @ajax_request_class
    def public_feed_json(self, request, pk):
        """
        Returns all property and taxlot state data for a given organization as a json object. The results are ordered by "state.update".

        Optional and configurable url query_params:
        :query_param labels: comma separated list of case sensitive label names. Results will include inventory that has any of the listed labels. Default is all inventory
        :query_param cycles: comma separated list of cycle ids. Results include inventory from the listed cycles. Default is all cycles
        :query_param properties: boolean to return properties. Default is True
        :query_param taxlots: boolean to return taxlots. Default is True
        :query_param page: integer page number
        :query_param per_page: integer results per page

        Example requests:
        {seed_url}/api/v3/organizations/public_feed.json?{query_param1}={value1}&{query_param2}={value2}
        dev1.seed-platform.org/api/v3/organizations/1/public_feed.json
        dev1.seed-platform.org/api/v3/organizations/1/public_feed.json?page=2&labels=Compliant&cycles=1,2,3&taxlots=False
        """
        try:
            org = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return JsonResponse({"error": "Organization does not exist"}, status=status.HTTP_404_NOT_FOUND)

        feed = public_feed(org, request)

        return JsonResponse(feed, json_dumps_params={"indent": 4}, status=status.HTTP_200_OK)

    @ajax_request_class
    @has_perm_class("requires_viewer")
    @action(detail=True, methods=["GET"])
    def report_configurations(self, request, pk):
        user_ali = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        configs = ReportConfiguration.objects.filter(
            organization_id=pk,
            access_level_instance__lft__gte=user_ali.lft,
            access_level_instance__rgt__lte=user_ali.rgt,
        )
        return JsonResponse({"data": ReportConfigurationSerializer(configs, many=True).data}, status=status.HTTP_200_OK)

# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
import logging
from collections import defaultdict
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from xlsxwriter import Workbook

from seed import tasks
from seed.data_importer.models import ImportFile, ImportRecord
from seed.data_importer.tasks import save_raw_data
from seed.decorators import ajax_request_class
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.decorators import (
    has_hierarchy_access,
    has_perm_class
)
from seed.lib.superperms.orgs.models import (
    ROLE_MEMBER,
    ROLE_OWNER,
    ROLE_VIEWER,
    AccessLevelInstance,
    Organization,
    OrganizationUser
)
from seed.models import (
    AUDIT_IMPORT,
    GREEN_BUTTON,
    PORTFOLIO_METER_USAGE,
    SEED_DATA_SOURCES,
    Column,
    Cycle,
    Property,
    PropertyAuditLog,
    PropertyState,
    PropertyView
)
from seed.models import StatusLabel as Label
from seed.models import TaxLot, TaxLotAuditLog, TaxLotState, TaxLotView
from seed.serializers.column_mappings import (
    SaveColumnMappingsRequestPayloadSerializer
)
from seed.serializers.organizations import (
    SaveSettingsSerializer,
    SharedFieldsReturnSerializer
)
from seed.serializers.pint import apply_display_unit_preferences
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.generic import median, round_down_hundred_thousand
from seed.utils.geocode import geocode_buildings
from seed.utils.match import match_merge_link
from seed.utils.merge import merge_properties
from seed.utils.organizations import (
    create_organization,
    create_suborganization
)
from seed.utils.properties import pair_unpair_property_taxlot
from seed.utils.salesforce import toggle_salesforce_sync
from seed.utils.users import get_js_role

_log = logging.getLogger(__name__)


def _dict_org(request, organizations):
    """returns a dictionary of an organization's data."""

    orgs = []
    for o in organizations:
        org_cycles = Cycle.objects.filter(organization=o).only('id', 'name').order_by('name')
        cycles = []
        for c in org_cycles:
            cycles.append({
                'name': c.name,
                'cycle_id': c.pk,
                'num_properties': PropertyView.objects.filter(cycle=c).count(),
                'num_taxlots': TaxLotView.objects.filter(cycle=c).count()
            })

        # We don't wish to double count sub organization memberships.
        org_users = OrganizationUser.objects.select_related('user').only(
            'role_level', 'user__first_name', 'user__last_name', 'user__email', 'user__id'
        ).filter(organization=o)

        owners = []
        role_level = None
        user_is_owner = False
        for ou in org_users:
            if ou.role_level == ROLE_OWNER:
                owners.append({
                    'first_name': ou.user.first_name,
                    'last_name': ou.user.last_name,
                    'email': ou.user.email,
                    'id': ou.user.id
                })

                if ou.user == request.user:
                    user_is_owner = True

            if ou.user == request.user:
                role_level = get_js_role(ou.role_level)

        org = {
            'name': o.name,
            'org_id': o.id,
            'id': o.id,
            'number_of_users': len(org_users),
            'user_is_owner': user_is_owner,
            'user_role': role_level,
            'owners': owners,
            'sub_orgs': _dict_org(request, o.child_orgs.all()),
            'is_parent': o.is_parent,
            'parent_id': o.parent_id,
            'display_units_eui': o.display_units_eui,
            'display_units_ghg': o.display_units_ghg,
            'display_units_ghg_intensity': o.display_units_ghg_intensity,
            'display_units_area': o.display_units_area,
            'display_decimal_places': o.display_decimal_places,
            'cycles': cycles,
            'created': o.created.strftime('%Y-%m-%d') if o.created else '',
            'mapquest_api_key': o.mapquest_api_key or '',
            'geocoding_enabled': o.geocoding_enabled,
            'better_analysis_api_key': o.better_analysis_api_key or '',
            'better_host_url': settings.BETTER_HOST,
            'property_display_field': o.property_display_field,
            'taxlot_display_field': o.taxlot_display_field,
            'display_meter_units': dict(sorted(o.display_meter_units.items(), key=lambda item: (item[0], item[1]))),
            'thermal_conversion_assumption': o.thermal_conversion_assumption,
            'comstock_enabled': o.comstock_enabled,
            'new_user_email_from': o.new_user_email_from,
            'new_user_email_subject': o.new_user_email_subject,
            'new_user_email_content': o.new_user_email_content,
            'new_user_email_signature': o.new_user_email_signature,
            'at_organization_token': o.at_organization_token,
            'audit_template_user': o.audit_template_user,
            'audit_template_password': o.audit_template_password,
            'at_host_url': settings.AUDIT_TEMPLATE_HOST,
            'audit_template_report_type': o.audit_template_report_type,
            'salesforce_enabled': o.salesforce_enabled,
            'ubid_threshold': o.ubid_threshold,
            'inventory_count': o.property_set.count() + o.taxlot_set.count(),
            'access_level_names': o.access_level_names,
        }
        orgs.append(org)

    return orgs


def _dict_org_brief(request, organizations):
    """returns a brief dictionary of an organization's data."""

    organization_roles = list(OrganizationUser.objects.filter(user=request.user).values(
        'organization_id', 'role_level'
    ))

    role_levels = {}
    for r in organization_roles:
        role_levels[r['organization_id']] = get_js_role(r['role_level'])

    orgs = []
    for o in organizations:
        user_role = None
        try:
            user_role = role_levels[o.id]
        except KeyError:
            pass

        org = {
            'name': o.name,
            'org_id': o.id,
            'parent_id': o.parent_org_id,
            'is_parent': o.is_parent,
            'id': o.id,
            'user_role': user_role,
            'display_decimal_places': o.display_decimal_places,
            'salesforce_enabled': o.salesforce_enabled,
            'access_level_names': o.access_level_names,
        }
        orgs.append(org)

    return orgs


class OrganizationViewSet(viewsets.ViewSet):
    # allow using `pk` in url path for authorization (i.e., for has_perm_class)
    authz_org_id_kwarg = 'pk'

    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=True, methods=['DELETE'])
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
                    'status': 'success',
                    'column_mappings_deleted_count': cm_count,
                    'columns_deleted_count': c_count,
                }
            )
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization with with id {} does not exist'.format(pk)
            }, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_integer_field(
                'import_file_id', required=True, description='Import file id'),
            openapi.Parameter(
                'id', openapi.IN_PATH, type=openapi.TYPE_INTEGER, description='Organization id'),
        ],
        request_body=SaveColumnMappingsRequestPayloadSerializer,
        responses={
            200: 'success response'
        }
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @has_hierarchy_access(param_import_file_id='import_file_id')
    @action(detail=True, methods=['POST'])
    def column_mappings(self, request, pk=None):
        """
        Saves the mappings between the raw headers of an ImportFile and the
        destination fields in the `to_table_name` model which should be either
        PropertyState or TaxLotState

        Valid source_type values are found in ``seed.models.SEED_DATA_SOURCES``
        """
        import_file_id = request.query_params.get('import_file_id')
        if import_file_id is None:
            return JsonResponse({
                'status': 'error',
                'message': 'Query param `import_file_id` is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            ImportFile.objects.get(pk=import_file_id)
            organization = Organization.objects.get(pk=pk)
        except ImportFile.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'No import file found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'No organization found'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            Column.create_mappings(
                request.data.get('mappings', []),
                organization,
                request.user,
                import_file_id
            )
        except PermissionError as e:
            return JsonResponse({'status': 'error', "message": str(e)})

        else:
            return JsonResponse({'status': 'success'})

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_boolean_field(
            'brief',
            required=False,
            description='If true, only return high-level organization details'
        )]
    )
    @api_endpoint_class
    @ajax_request_class
    def list(self, request):
        """
        Retrieves all orgs the user has access to.
        """

        # if brief==true only return high-level organization details
        brief = json.loads(request.query_params.get('brief', 'false'))

        if brief:
            if request.user.is_superuser:
                qs = Organization.objects.only('id', 'name', 'parent_org_id', 'display_decimal_places')
            else:
                qs = request.user.orgs.only('id', 'name', 'parent_org_id', 'display_decimal_places')

            orgs = _dict_org_brief(request, qs)
            if len(orgs) == 0:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Your SEED account is not associated with any organizations. '
                               'Please contact a SEED administrator.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            else:
                return JsonResponse({'organizations': orgs})
        else:
            if request.user.is_superuser:
                qs = Organization.objects.all()
            else:
                qs = request.user.orgs.all()

            orgs = _dict_org(request, qs)
            if len(orgs) == 0:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Your SEED account is not associated with any organizations. '
                               'Please contact a SEED administrator.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            else:
                return JsonResponse({'organizations': orgs})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def destroy(self, request, pk=None):
        """
        Starts a background task to delete an organization and all related data.
        """

        return JsonResponse(tasks.delete_organization(pk))

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def retrieve(self, request, pk=None):
        """
        Retrieves a single organization by id.
        """
        org_id = pk
        brief = json.loads(request.query_params.get('brief', 'false'))

        if org_id is None:
            return JsonResponse({
                'status': 'error',
                'message': 'no organization_id sent'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization does not exist'
            }, status=status.HTTP_404_NOT_FOUND)
        if (
            not request.user.is_superuser and
            not OrganizationUser.objects.filter(
                user=request.user,
                organization=org,
                role_level__in=[ROLE_OWNER, ROLE_MEMBER, ROLE_VIEWER]
            ).exists()
        ):
            # TODO: better permission and return 401 or 403
            return JsonResponse({
                'status': 'error',
                'message': 'user is not the owner of the org'
            }, status=status.HTTP_403_FORBIDDEN)

        if brief:
            org = _dict_org_brief(request, [org])[0]
        else:
            org = _dict_org(request, [org])[0]

        return JsonResponse({
            'status': 'success',
            'organization': org,
        })

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory(
            {
                'organization_name': 'string',
                'user_id': 'integer',
            },
            required=['organization_name', 'user_id'],
            description='Properties:\n'
                        '- organization_name: The new organization name\n'
                        '- user_id: The user ID (primary key) to be used as the owner of the new organization'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    def create(self, request):
        """
        Creates a new organization.
        """
        body = request.data
        user = User.objects.get(pk=body['user_id'])
        org_name = body['organization_name']

        if not request.user.is_superuser and request.user.id != user.id:
            return JsonResponse({
                'status': 'error',
                'message': 'not authorized'
            }, status=status.HTTP_403_FORBIDDEN)

        if Organization.objects.filter(name=org_name).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Organization name already exists'
            }, status=status.HTTP_409_CONFLICT)

        org, _, _ = create_organization(user, org_name, org_name)
        return JsonResponse(
            {
                'status': 'success',
                'message': 'Organization created',
                'organization': _dict_org(request, [org])[0]
            }
        )

    @api_endpoint_class
    @ajax_request_class
    @method_decorator(permission_required('seed.can_access_admin'))
    @action(detail=True, methods=['DELETE'])
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
    @has_perm_class('requires_owner')
    @action(detail=True, methods=['PUT'])
    def save_settings(self, request, pk=None):
        """
        Saves an organization's settings: name, query threshold, shared fields, etc
        """
        body = request.data
        org = Organization.objects.get(pk=pk)
        posted_org = body.get('organization', None)
        if posted_org is None:
            return JsonResponse({'status': 'error', 'message': 'malformed request'},
                                status=status.HTTP_400_BAD_REQUEST)

        desired_threshold = posted_org.get('query_threshold', None)
        if desired_threshold is not None:
            org.query_threshold = desired_threshold

        desired_name = posted_org.get('name', None)
        if desired_name is not None:
            org.name = desired_name

        def is_valid_choice(choice_tuples, s):
            """choice_tuples is std model ((value, label), ...)"""
            return (s is not None) and (s in [choice[0] for choice in choice_tuples])

        def warn_bad_pint_spec(kind, unit_string):
            if unit_string is not None:
                _log.warn("got bad {0} unit string {1} for org {2}".format(
                    kind, unit_string, org.name))

        def warn_bad_units(kind, unit_string):
            _log.warn("got bad {0} unit string {1} for org {2}".format(
                kind, unit_string, org.name))

        desired_display_units_eui = posted_org.get('display_units_eui')
        if is_valid_choice(Organization.MEASUREMENT_CHOICES_EUI, desired_display_units_eui):
            org.display_units_eui = desired_display_units_eui
        else:
            warn_bad_pint_spec('eui', desired_display_units_eui)

        desired_display_units_ghg = posted_org.get('display_units_ghg')
        if is_valid_choice(Organization.MEASUREMENT_CHOICES_GHG, desired_display_units_ghg):
            org.display_units_ghg = desired_display_units_ghg
        else:
            warn_bad_pint_spec('ghg', desired_display_units_ghg)

        desired_display_units_ghg_intensity = posted_org.get('display_units_ghg_intensity')
        if is_valid_choice(Organization.MEASUREMENT_CHOICES_GHG_INTENSITY, desired_display_units_ghg_intensity):
            org.display_units_ghg_intensity = desired_display_units_ghg_intensity
        else:
            warn_bad_pint_spec('ghg_intensity', desired_display_units_ghg_intensity)

        desired_display_units_area = posted_org.get('display_units_area')
        if is_valid_choice(Organization.MEASUREMENT_CHOICES_AREA, desired_display_units_area):
            org.display_units_area = desired_display_units_area
        else:
            warn_bad_pint_spec('area', desired_display_units_area)

        desired_display_decimal_places = posted_org.get('display_decimal_places')
        if isinstance(desired_display_decimal_places, int) and desired_display_decimal_places >= 0:
            org.display_decimal_places = desired_display_decimal_places
        elif desired_display_decimal_places is not None:
            _log.warn("got bad sig figs {0} for org {1}".format(
                desired_display_decimal_places, org.name))

        desired_display_meter_units = posted_org.get('display_meter_units')
        if desired_display_meter_units:
            org.display_meter_units = desired_display_meter_units

        desired_thermal_conversion_assumption = posted_org.get('thermal_conversion_assumption')
        if is_valid_choice(Organization.THERMAL_CONVERSION_ASSUMPTION_CHOICES, desired_thermal_conversion_assumption):
            org.thermal_conversion_assumption = desired_thermal_conversion_assumption

        # Update MapQuest API Key if it's been changed
        mapquest_api_key = posted_org.get('mapquest_api_key', '')
        if mapquest_api_key != org.mapquest_api_key:
            org.mapquest_api_key = mapquest_api_key

        # Update geocoding_enabled option
        geocoding_enabled = posted_org.get('geocoding_enabled', True)
        if geocoding_enabled != org.geocoding_enabled:
            org.geocoding_enabled = geocoding_enabled

        # Update BETTER Analysis API Key if it's been changed
        better_analysis_api_key = posted_org.get('better_analysis_api_key', '').strip()
        if better_analysis_api_key != org.better_analysis_api_key:
            org.better_analysis_api_key = better_analysis_api_key

        # Update property_display_field option
        property_display_field = posted_org.get('property_display_field', 'address_line_1')
        if property_display_field != org.property_display_field:
            org.property_display_field = property_display_field

        # Update taxlot_display_field option
        taxlot_display_field = posted_org.get('taxlot_display_field', 'address_line_1')
        if taxlot_display_field != org.taxlot_display_field:
            org.taxlot_display_field = taxlot_display_field

        # update new user email from option
        new_user_email_from = posted_org.get('new_user_email_from')
        if new_user_email_from != org.new_user_email_from:
            org.new_user_email_from = new_user_email_from
        if not org.new_user_email_from:
            org.new_user_email_from = Organization._meta.get_field('new_user_email_from').get_default()

        # update new user email subject option
        new_user_email_subject = posted_org.get('new_user_email_subject')
        if new_user_email_subject != org.new_user_email_subject:
            org.new_user_email_subject = new_user_email_subject
        if not org.new_user_email_subject:
            org.new_user_email_subject = Organization._meta.get_field('new_user_email_subject').get_default()

        # update new user email content option
        new_user_email_content = posted_org.get('new_user_email_content')
        if new_user_email_content != org.new_user_email_content:
            org.new_user_email_content = new_user_email_content
        if not org.new_user_email_content:
            org.new_user_email_content = Organization._meta.get_field('new_user_email_content').get_default()
        if '{{sign_up_link}}' not in org.new_user_email_content:
            org.new_user_email_content += '\n\nSign up here: {{sign_up_link}}'

        # update new user email signature option
        new_user_email_signature = posted_org.get('new_user_email_signature')
        if new_user_email_signature != org.new_user_email_signature:
            org.new_user_email_signature = new_user_email_signature
        if not org.new_user_email_signature:
            org.new_user_email_signature = Organization._meta.get_field('new_user_email_signature').get_default()

        comstock_enabled = posted_org.get('comstock_enabled', False)
        if comstock_enabled != org.comstock_enabled:
            org.comstock_enabled = comstock_enabled

        at_organization_token = posted_org.get('at_organization_token', False)
        if at_organization_token != org.at_organization_token:
            org.at_organization_token = at_organization_token

        audit_template_user = posted_org.get('audit_template_user', False)
        if audit_template_user != org.audit_template_user:
            org.audit_template_user = audit_template_user

        audit_template_password = posted_org.get('audit_template_password', False)
        if audit_template_password != org.audit_template_password:
            org.audit_template_password = audit_template_password

        audit_template_report_type = posted_org.get('audit_template_report_type', False)
        if audit_template_report_type != org.audit_template_report_type:
            org.audit_template_report_type = audit_template_report_type

        salesforce_enabled = posted_org.get('salesforce_enabled', False)
        if salesforce_enabled != org.salesforce_enabled:
            org.salesforce_enabled = salesforce_enabled
            # if salesforce_enabled was toggled, must start/stop auto sync functionality
            toggle_salesforce_sync(salesforce_enabled, org.id)

        # update the ubid threshold option
        ubid_threshold = posted_org.get('ubid_threshold')
        if ubid_threshold is not None and ubid_threshold != org.ubid_threshold:
            if not type(ubid_threshold) in (float, int) or ubid_threshold < 0 or ubid_threshold > 1:
                return JsonResponse({
                    'status': 'error',
                    'message': 'ubid_threshold must be a float between 0 and 1'
                }, status=status.HTTP_400_BAD_REQUEST)

            org.ubid_threshold = ubid_threshold

        org.save()

        # Update the selected exportable fields.
        new_public_column_names = posted_org.get('public_fields', None)
        if new_public_column_names is not None:
            old_public_columns = Column.objects.filter(organization=org,
                                                       shared_field_type=Column.SHARED_PUBLIC)
            # turn off sharing in the old_pub_fields
            for col in old_public_columns:
                col.shared_field_type = Column.SHARED_NONE
                col.save()

            # for now just iterate over this to grab the new columns.
            for col in new_public_column_names:
                new_col = Column.objects.filter(organization=org, id=col['id'])
                if len(new_col) == 1:
                    new_col = new_col.first()
                    new_col.shared_field_type = Column.SHARED_PUBLIC
                    new_col.save()

        return JsonResponse({'status': 'success'})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['GET'])
    def query_threshold(self, request, pk=None):
        """
        Returns the "query_threshold" for an org.  Searches from
        members of sibling orgs must return at least this many buildings
        from orgs they do not belong to, or else buildings from orgs they
        don't belong to will be removed from the results.
        """
        org = Organization.objects.get(pk=pk)
        return JsonResponse({
            'status': 'success',
            'query_threshold': org.query_threshold
        })

    @swagger_auto_schema(
        responses={
            200: SharedFieldsReturnSerializer
        }
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['GET'])
    def shared_fields(self, request, pk=None):
        """
        Retrieves all fields marked as shared for the organization. Will only return used fields.
        """
        result = {
            'status': 'success',
            'public_fields': []
        }

        columns = Column.retrieve_all(pk, 'property', True)
        for c in columns:
            if c['sharedFieldType'] == 'Public':
                new_column = {
                    'table_name': c['table_name'],
                    'name': c['name'],
                    'column_name': c['column_name'],
                    # this is the field name in the db. The other name can have tax_
                    'display_name': c['display_name']
                }
                result['public_fields'].append(new_column)

        return JsonResponse(result)

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory(
            {
                'sub_org_name': 'string',
                'sub_org_owner_email': 'string',
            },
            required=['sub_org_name', 'sub_org_owner_email'],
            description='Properties:\n'
                        '- sub_org_name: Name of the new sub organization\n'
                        '- sub_org_owner_email: Email of the owner of the sub organization, which must already exist',
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['POST'])
    def sub_org(self, request, pk=None):
        """
        Creates a child org of a parent org.
        """
        body = request.data
        org = Organization.objects.get(pk=pk)
        email = body['sub_org_owner_email'].lower()
        try:
            user = User.objects.get(username=email)
        except User.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'User with email address (%s) does not exist' % email
            }, status=status.HTTP_400_BAD_REQUEST)

        created, mess_or_org, _ = create_suborganization(user, org, body['sub_org_name'],
                                                         ROLE_OWNER)
        if created:
            return JsonResponse({
                'status': 'success',
                'organization_id': mess_or_org.pk
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': mess_or_org
            }, status=status.HTTP_409_CONFLICT)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['GET'])
    def matching_criteria_columns(self, request, pk=None):
        """
        Retrieve all matching criteria columns for an org.
        """
        try:
            org = Organization.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(pk)},
                                status=status.HTTP_404_NOT_FOUND)

        matching_criteria_column_names = dict(
            org.column_set.
            filter(is_matching_criteria=True).
            values('table_name').
            annotate(column_names=ArrayAgg('column_name')).
            values_list('table_name', 'column_names')
        )

        return JsonResponse(matching_criteria_column_names)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['GET'])
    def geocoding_columns(self, request, pk=None):
        """
        Retrieve all geocoding columns for an org.
        """
        try:
            org = Organization.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(pk)},
                                status=status.HTTP_404_NOT_FOUND)

        geocoding_columns_qs = org.column_set.\
            filter(geocoding_order__gt=0).\
            order_by('geocoding_order').\
            values('table_name', 'column_name')

        geocoding_columns = {
            'PropertyState': [],
            'TaxLotState': [],
        }

        for col in geocoding_columns_qs:
            geocoding_columns[col['table_name']].append(col['column_name'])

        return JsonResponse(geocoding_columns)

    def get_data(self, property_view, x_var, y_var, matching_columns):
        result = {}
        state = property_view.state

        # set matching columns
        for matching_column in matching_columns:
            name = matching_column.column_name
            if matching_column.is_extra_data:
                result[name] = state.extra_data.get(name)
            else:
                result[name] = getattr(state, name)

        # set x
        if x_var == "Count":
            result["x"] = 1
        else:
            try:
                result["x"] = getattr(state, x_var)
            except AttributeError:
                # check extra data
                try:
                    result["x"] = state.extra_data.get(x_var)
                except AttributeError:
                    return {}

        # set y
        try:
            result["y"] = getattr(state, y_var)
        except AttributeError:
            # check extra data
            try:
                result["y"] = state.extra_data.get(y_var)
            except AttributeError:
                return {}

        return result

    def get_raw_report_data(self, organization_id, access_level_instance, cycles, x_var, y_var, addtional_columns=[]):
        all_property_views = PropertyView.objects.select_related(
            'property', 'state'
        ).filter(
            property__organization_id=organization_id,
            property__access_level_instance__lft__gte=access_level_instance.lft,
            property__access_level_instance__rgt__lte=access_level_instance.rgt,
            cycle_id__in=cycles
        ).order_by('id')
        organization = Organization.objects.get(pk=organization_id)
        results = []
        for cycle in cycles:
            property_views = all_property_views.filter(cycle_id=cycle)
            count_total = []
            count_with_data = []
            data = []
            for property_view in property_views:
                property_pk = property_view.property_id
                count_total.append(property_pk)
                result = self.get_data(property_view, x_var, y_var, addtional_columns)
                if result:
                    result['yr_e'] = cycle.end.strftime('%Y')
                    de_unitted_result = apply_display_unit_preferences(organization, result)
                    data.append(de_unitted_result)
                    count_with_data.append(property_pk)
            result = {
                "cycle_id": cycle.pk,
                "chart_data": data,
                "property_counts": {
                    "yr_e": cycle.end.strftime('%Y'),
                    "num_properties": len(count_total),
                    "num_properties_w-data": len(count_with_data),
                },
            }
            results.append(result)
        return results

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_string_field(
                'x_var',
                required=True,
                description='Raw column name for x axis'
            ),
            AutoSchemaHelper.query_string_field(
                'y_var',
                required=True,
                description='Raw column name for y axis'
            ),
            AutoSchemaHelper.query_string_field(
                'start',
                required=True,
                description='Start time, in the format "2018-12-31T23:53:00-08:00"'
            ),
            AutoSchemaHelper.query_string_field(
                'end',
                required=True,
                description='End time, in the format "2018-12-31T23:53:00-08:00"'
            ),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=True, methods=['GET'])
    def report(self, request, pk=None):
        """Retrieve a summary report for charting x vs y
        """
        access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        params = {
            "x_var": request.query_params.get("x_var", None),
            "y_var": request.query_params.get("y_var", None),
            "cycle_ids": request.query_params.getlist("cycle_ids", None),
        }

        excepted_params = ["x_var", "y_var", "cycle_ids"]
        missing_params = [p for p in excepted_params if p not in params]
        if missing_params:
            return Response(
                {'status': 'error', 'message': "Missing params: {}".format(", ".join(missing_params))},
                status=status.HTTP_400_BAD_REQUEST
            )

        cycles = Cycle.objects.filter(id__in=params["cycle_ids"])
        data = self.get_raw_report_data(pk, access_level_instance, cycles, params['x_var'], params['y_var'])
        data = {
            "chart_data": sum([d["chart_data"] for d in data], []),
            "property_counts": [d["property_counts"] for d in data]
        }

        return Response(
            {'status': 'success', 'data': data},
            status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_string_field(
                'x_var',
                required=True,
                description='Raw column name for x axis'
            ),
            AutoSchemaHelper.query_string_field(
                'y_var',
                required=True,
                description='Raw column name for y axis, must be one of: "gross_floor_area", "property_type", "year_built"'
            ),
            AutoSchemaHelper.query_string_field(
                'start',
                required=True,
                description='Start time, in the format "2018-12-31T23:53:00-08:00"'
            ),
            AutoSchemaHelper.query_string_field(
                'end',
                required=True,
                description='End time, in the format "2018-12-31T23:53:00-08:00"'
            ),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=True, methods=['GET'])
    def report_aggregated(self, request, pk=None):
        """Retrieve a summary report for charting x vs y aggregated by y_var
        """
        access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)

        # get params
        params = {
            "x_var": request.query_params.get("x_var", None),
            "y_var": request.query_params.get("y_var", None),
            "cycle_ids": request.query_params.getlist("cycle_ids", None)
        }

        # error if missing
        excepted_params = ["x_var", "y_var", "cycle_ids"]
        missing_params = [p for p in excepted_params if p not in params]
        if missing_params:
            return Response(
                {'status': 'error', 'message': "Missing params: {}".format(", ".join(missing_params))},
                status=status.HTTP_400_BAD_REQUEST
            )

        # error if y_var invalid
        valid_y_values = ['gross_floor_area', 'property_type', 'year_built']
        if params["y_var"] not in valid_y_values:
            return Response(
                {'status': 'error', 'message': f"{params['y_var']} is not a valid value for y_var"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # get data
        cycles = Cycle.objects.filter(id__in=params["cycle_ids"])
        data = self.get_raw_report_data(pk, access_level_instance, cycles, params["x_var"], params["y_var"])

        chart_data = []
        property_counts = []
        for datum in data:
            buildings = datum['chart_data']
            yr_e = datum['property_counts']['yr_e']
            chart_data.extend(self.aggregate_data(yr_e, params["x_var"], params["y_var"], buildings)),
            property_counts.append(datum['property_counts'])

        # Send back to client
        result = {
            'status': 'success',
            'aggregated_data': {
                'chart_data': chart_data,
                'property_counts': property_counts
            },
        }

        return Response(result, status=status.HTTP_200_OK)

    def aggregate_data(self, yr_e, x_var, y_var, buildings):
        aggregation_method = {
            'property_type': self.aggregate_property_type,
            'year_built': self.aggregate_year_built,
            'gross_floor_area': self.aggregate_gross_floor_area,


        }
        return aggregation_method[y_var](yr_e, x_var, buildings)

    def aggregate_property_type(self, yr_e, x_var, buildings):
        # Group buildings in this year_ending group into uses
        chart_data = []
        grouped_uses = defaultdict(list)
        for b in buildings:
            grouped_uses[str(b['y']).lower()].append(b)

        # Now iterate over use groups to make each chart item
        for use, buildings_in_uses in grouped_uses.items():
            x = [b['x'] for b in buildings_in_uses]
            chart_data.append({
                'x': sum(x) if x_var == "Count" else median(x),
                'y': use.capitalize(),
                'yr_e': yr_e
            })
        return chart_data

    def aggregate_year_built(self, yr_e, x_var, buildings):
        # Group buildings in this year_ending group into decades
        chart_data = []
        grouped_decades = defaultdict(list)
        for b in buildings:
            grouped_decades['%s0' % str(b['y'])[:-1]].append(b)

        # Now iterate over decade groups to make each chart item
        for decade, buildings_in_decade in grouped_decades.items():
            x = [b['x'] for b in buildings_in_decade]
            chart_data.append({
                'x': sum(x) if x_var == "Count" else median(x),
                'y': '%s-%s' % (decade, '%s9' % str(decade)[:-1]),  # 1990-1999
                'yr_e': yr_e
            })
        return chart_data

    def aggregate_gross_floor_area(self, yr_e, x_var, buildings):
        chart_data = []
        y_display_map = {
            0: '0-99k',
            100000: '100-199k',
            200000: '200k-299k',
            300000: '300k-399k',
            400000: '400-499k',
            500000: '500-599k',
            600000: '600-699k',
            700000: '700-799k',
            800000: '800-899k',
            900000: '900-999k',
            1000000: 'over 1,000k',
        }
        max_bin = max(y_display_map)

        # Group buildings in this year_ending group into ranges
        grouped_ranges = defaultdict(list)
        for b in buildings:
            area = b['y']
            # make sure anything greater than the biggest bin gets put in
            # the biggest bin
            range_bin = min(max_bin, round_down_hundred_thousand(area))
            grouped_ranges[range_bin].append(b)

        # Now iterate over range groups to make each chart item
        for range_floor, buildings_in_range in grouped_ranges.items():
            x = [b['x'] for b in buildings_in_range]
            chart_data.append({
                'x': sum(x) if x_var == "Count" else median(x),
                'y': y_display_map[range_floor],
                'yr_e': yr_e
            })
        return chart_data

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_string_field(
                'x_var',
                required=True,
                description='Raw column name for x axis'
            ),
            AutoSchemaHelper.query_string_field(
                'x_label',
                required=True,
                description='Label for x axis'
            ),
            AutoSchemaHelper.query_string_field(
                'y_var',
                required=True,
                description='Raw column name for y axis'
            ),
            AutoSchemaHelper.query_string_field(
                'y_label',
                required=True,
                description='Label for y axis'
            ),
            AutoSchemaHelper.query_string_field(
                'start',
                required=True,
                description='Start time, in the format "2018-12-31T23:53:00-08:00"'
            ),
            AutoSchemaHelper.query_string_field(
                'end',
                required=True,
                description='End time, in the format "2018-12-31T23:53:00-08:00"'
            ),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=True, methods=['GET'])
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
            "cycle_ids": request.query_params.getlist("cycle_ids", None)
        }

        # error if missing
        excepted_params = ["x_var", "x_label", "y_var", "y_label", "cycle_ids"]
        missing_params = [p for p in excepted_params if p not in params]
        if missing_params:
            return Response(
                {'status': 'error', 'message': "Missing params: {}".format(", ".join(missing_params))},
                status=status.HTTP_400_BAD_REQUEST
            )

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="report-data"'

        # Create WB
        output = BytesIO()
        wb = Workbook(output, {'remove_timezone': True})

        # Create sheets
        count_sheet = wb.add_worksheet('Counts')
        base_sheet = wb.add_worksheet('Raw')
        agg_sheet = wb.add_worksheet('Agg')

        # Enable bold format and establish starting cells
        bold = wb.add_format({'bold': True})
        data_row_start = 0
        data_col_start = 0

        # Write all headers across all sheets
        count_sheet.write(data_row_start, data_col_start, 'Year Ending', bold)
        count_sheet.write(data_row_start, data_col_start + 1, 'Properties with Data', bold)
        count_sheet.write(data_row_start, data_col_start + 2, 'Total Properties', bold)

        agg_sheet.write(data_row_start, data_col_start, request.query_params.get('x_label'), bold)
        agg_sheet.write(data_row_start, data_col_start + 1, request.query_params.get('y_label'), bold)
        agg_sheet.write(data_row_start, data_col_start + 2, 'Year Ending', bold)

        # Gather base data
        cycles = Cycle.objects.filter(id__in=params["cycle_ids"])
        matching_columns = Column.objects.filter(organization_id=pk, is_matching_criteria=True, table_name="PropertyState")
        data = self.get_raw_report_data(
            pk, access_level_instance, cycles, params['x_var'], params['y_var'], matching_columns
        )

        base_sheet.write(data_row_start, data_col_start, 'ID', bold)

        for i, matching_column in enumerate(matching_columns):
            base_sheet.write(data_row_start, data_col_start + i, matching_column.display_name, bold)
        base_sheet.write(data_row_start, data_col_start + len(matching_columns) + 0, request.query_params.get('x_label'), bold)
        base_sheet.write(data_row_start, data_col_start + len(matching_columns) + 1, request.query_params.get('y_label'), bold)
        base_sheet.write(data_row_start, data_col_start + len(matching_columns) + 2, 'Year Ending', bold)

        base_row = data_row_start + 1
        agg_row = data_row_start + 1
        count_row = data_row_start + 1

        for cycle_results in data:
            total_count = cycle_results['property_counts']['num_properties']
            with_data_count = cycle_results['property_counts']['num_properties_w-data']
            yr_e = cycle_results['property_counts']['yr_e']

            # Write Counts
            count_sheet.write(count_row, data_col_start, yr_e)
            count_sheet.write(count_row, data_col_start + 1, with_data_count)
            count_sheet.write(count_row, data_col_start + 2, total_count)

            count_row += 1

            # Write Base/Raw Data
            data_rows = cycle_results['chart_data']
            for datum in data_rows:
                for i, k in enumerate(datum.keys()):
                    base_sheet.write(base_row, data_col_start + i, datum.get(k))

                base_row += 1

            # Gather and write Agg data
            for agg_datum in self.aggregate_data(yr_e, params['x_var'], params['y_var'], data_rows):
                agg_sheet.write(agg_row, data_col_start, agg_datum.get('x'))
                agg_sheet.write(agg_row, data_col_start + 1, agg_datum.get('y'))
                agg_sheet.write(agg_row, data_col_start + 2, agg_datum.get('yr_e'))

                agg_row += 1

        wb.close()

        xlsx_data = output.getvalue()

        response.write(xlsx_data)

        return response

    @has_perm_class('requires_member')
    @ajax_request_class
    @action(detail=True, methods=['GET'])
    def geocode_api_key_exists(self, request, pk=None):
        """
        Returns true if the organization has a mapquest api key
        """
        org = Organization.objects.get(id=pk)

        if org.mapquest_api_key:
            return True
        else:
            return False

    @has_perm_class('requires_member')
    @ajax_request_class
    @action(detail=True, methods=['GET'])
    def geocoding_enabled(self, request, pk=None):
        """
        Returns the organization's geocoding_enabled setting
        """
        org = Organization.objects.get(id=pk)

        return org.geocoding_enabled

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=True, methods=['POST'])
    def reset_all_passwords(self, request, pk=None):
        """
        Resets all user passwords in organization
        """
        org_users = OrganizationUser.objects.filter(organization=pk).select_related('user')
        for org_user in org_users:
            form = PasswordResetForm({'email': org_user.user.email})
            if form.is_valid():
                org_user.user.password = ''
                org_user.user.save()
                form.save(
                    from_email=settings.PASSWORD_RESET_EMAIL,
                    subject_template_name='landing/password_reset_subject.txt',
                    email_template_name='landing/password_reset_forced_email.html'
                )

        return JsonResponse(
            {
                'status': 'success',
                'message': 'passwords reset'
            }
        )

    @has_perm_class('requires_superuser')
    @ajax_request_class
    @action(detail=True, methods=['GET'])
    def insert_sample_data(self, request, pk=None):
        """
        Create a button for new users to import data below if no data exists
        """
        org = Organization.objects.get(id=pk)
        cycles = Cycle.objects.filter(organization=org)
        if cycles.count() == 0:
            return JsonResponse({
                'status': 'error',
                'message': 'there must be at least 1 cycle'
            }, status=status.HTTP_400_BAD_REQUEST)

        cycle = cycles.first()
        if PropertyView.objects.filter(cycle=cycle).count() > 0 or TaxLotView.objects.filter(cycle=cycle).count() > 0:
            return JsonResponse({
                'status': 'error',
                'message': 'the cycle must not contain any properties or tax lots'
            }, status=status.HTTP_400_BAD_REQUEST)

        taxlot_details = {
            'jurisdiction_tax_lot_id': 'A-12345',
            'city': 'Boring',
            'organization_id': pk,
            'extra_data': {'Note': 'This is my first note'}
        }

        taxlot_state = TaxLotState(**taxlot_details)
        taxlot_state.save()
        taxlot_1 = TaxLot.objects.create(organization=org)
        taxview = TaxLotView.objects.create(taxlot=taxlot_1, cycle=cycle, state=taxlot_state)

        TaxLotAuditLog.objects.create(
            organization=org,
            state=taxlot_state,
            record_type=AUDIT_IMPORT,
            name='Import Creation'
        )

        filename_pd = 'property_sample_data.json'
        filepath_pd = f"{Path(__file__).parent.absolute()}/../../tests/data/{filename_pd}"

        with open(filepath_pd) as file:
            property_details = json.load(file)

        property_views = []
        properties = []
        ids = []
        for dic in property_details:

            dic['organization_id'] = pk

            state = PropertyState(**dic)
            state.save()
            ids.append(state.id)

            property_1 = Property.objects.create(organization=org)
            properties.append(property_1)
            propertyview = PropertyView.objects.create(property=property_1, cycle=cycle, state=state)
            property_views.append(propertyview)

            # create labels and add to records
            new_label, created = Label.objects.get_or_create(color='red', name='Housing', super_organization=org)
            if state.extra_data.get('Note') == 'Residential':
                propertyview.labels.add(new_label)

            PropertyAuditLog.objects.create(
                organization=org,
                state=state,
                record_type=AUDIT_IMPORT,
                name='Import Creation'
            )

            # Geocoding - need mapquest API (should add comment for new users)
            geocode = PropertyState.objects.filter(id__in=ids)
            geocode_buildings(geocode)

        # Create a merge of the last 2 properties
        state_ids_to_merge = ids[-2:]
        merged_state = merge_properties(state_ids_to_merge, pk, 'Manual Match')
        view = merged_state.propertyview_set.first()
        match_merge_link(merged_state.id, 'PropertyState', view.property.access_level_instance, view.cycle)

        # pair a property to tax lot
        property_id = property_views[0].id
        taxlot_id = taxview.id
        pair_unpair_property_taxlot(property_id, taxlot_id, org, True)

        # create column for Note
        Column.objects.get_or_create(
            organization=org,
            table_name='PropertyState',
            column_name='Note',
            is_extra_data=True  # Column objects representing raw/header rows are NEVER extra data
        )

        import_record = ImportRecord.objects.create(name='Auto-Populate', super_organization=org, access_level_instance=self.org.root)

        # Interval Data
        filename = 'PM Meter Data.xlsx'  # contains meter data for bsyncr and BETTER
        filepath = f"{Path(__file__).parent.absolute()}/data/{filename}"

        import_meterdata = ImportFile.objects.create(
            import_record=import_record,
            source_type=SEED_DATA_SOURCES[PORTFOLIO_METER_USAGE][1],
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=cycle
        )

        save_raw_data(import_meterdata.id)

        # Greenbutton Import
        filename = 'example-GreenButton-data.xml'
        filepath = f"{Path(__file__).parent.absolute()}/data/{filename}"

        import_greenbutton = ImportFile.objects.create(
            import_record=import_record,
            source_type=SEED_DATA_SOURCES[GREEN_BUTTON][1],
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=cycle,
            matching_results_data={'property_id': properties[7].id}
        )

        save_raw_data(import_greenbutton.id)

        return JsonResponse({
            'status': 'success'
        })

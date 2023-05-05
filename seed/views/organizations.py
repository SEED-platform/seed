# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import logging
from random import randint

from celery import shared_task
from django.contrib.auth.decorators import permission_required
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action

from seed import tasks
from seed.decorators import ajax_request_class
from seed.landing.models import SEEDUser as User
from seed.lib.progress_data.progress_data import ProgressData
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import (
    ROLE_MEMBER,
    ROLE_OWNER,
    ROLE_VIEWER,
    Organization,
    OrganizationUser
)
from seed.models import Column, Cycle, PropertyView, TaxLotView
from seed.tasks import invite_to_organization
from seed.utils.api import api_endpoint_class
from seed.utils.cache import get_cache_raw, set_cache_raw
from seed.utils.match import (
    matching_criteria_column_names,
    whole_org_match_merge_link
)
from seed.utils.organizations import (
    create_organization,
    create_suborganization
)


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
                role_level = _get_js_role(ou.role_level)

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
            'display_units_area': o.display_units_area,
            'display_decimal_places': o.display_decimal_places,
            'cycles': cycles,
            'created': o.created.strftime('%Y-%m-%d') if o.created else '',
            'mapquest_api_key': o.mapquest_api_key or '',
            'display_meter_units': o.display_meter_units,
            'thermal_conversion_assumption': o.thermal_conversion_assumption,
            'comstock_enabled': o.comstock_enabled,
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
        role_levels[r['organization_id']] = _get_js_role(r['role_level'])

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
            'id': o.id,
            'user_role': user_role
        }
        orgs.append(org)

    return orgs


def _get_js_role(role):
    """return the JS friendly role name for user

    :param role: role as defined in superperms.models
    :returns: (string) JS role name
    """
    roles = {
        ROLE_OWNER: 'owner',
        ROLE_VIEWER: 'viewer',
        ROLE_MEMBER: 'member',
    }
    return roles.get(role, 'viewer')


def _get_role_from_js(role):
    """return the OrganizationUser role_level from the JS friendly role name

    :param role: 'member', 'owner', or 'viewer'
    :returns: int role as defined in superperms.models
    """
    roles = {
        'owner': ROLE_OWNER,
        'viewer': ROLE_VIEWER,
        'member': ROLE_MEMBER,
    }
    return roles[role]


def _get_match_merge_link_key(identifier):
    return "org_match_merge_link_result__%s" % identifier


@shared_task(serializer='pickle', ignore_result=True)
def cache_match_merge_link_result(summary, identifier, progress_key):
    result_key = _get_match_merge_link_key(identifier)
    set_cache_raw(result_key, summary)

    progress_data = ProgressData.from_key(progress_key)
    progress_data.finish_with_success()


_log = logging.getLogger(__name__)


class SaveSettingsOrgFieldSerializer(serializers.Serializer):
    sort_column = serializers.CharField()


class SaveSettingsOrganizationSerializer(serializers.Serializer):
    query_threshold = serializers.IntegerField()
    name = serializers.CharField(max_length=100)
    fields = SaveSettingsOrgFieldSerializer(many=True)
    public_fields = SaveSettingsOrgFieldSerializer(many=True)


class SaveSettingsSerializer(serializers.Serializer):
    organization = SaveSettingsOrganizationSerializer()


class SharedFieldSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    sort_column = serializers.CharField(max_length=100)
    field_class = serializers.CharField(max_length=100)
    title_class = serializers.CharField(max_length=100)
    type = serializers.CharField(max_length=100)
    field_type = serializers.CharField(max_length=100)
    sortable = serializers.CharField(max_length=100)


class SharedFieldsReturnSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=100)
    shared_fields = SharedFieldSerializer(many=True)
    public_fields = SharedFieldSerializer(many=True)


class SharedFieldsActualReturnSerializer(serializers.Serializer):
    shared_fields = SharedFieldsReturnSerializer(many=True)


class OrganizationUserSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=100)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    user_id = serializers.IntegerField()
    role = serializers.CharField(max_length=100)
    access_level_instance_id = serializers.CharField(max_length=100)


class OrganizationUsersSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=100)
    users = OrganizationUserSerializer(many=True)


class OrganizationViewSet(viewsets.ViewSet):
    raise_exception = True

    def _start_whole_org_match_merge_link(self, org_id, state_class_name, proposed_columns=[]):
        identifier = randint(100, 100000)
        result_key = _get_match_merge_link_key(identifier)
        set_cache_raw(result_key, {})

        progress_data = ProgressData(func_name='org_match_merge_link', unique_id=identifier)
        progress_data.delete()

        whole_org_match_merge_link.apply_async(
            args=(org_id, state_class_name, proposed_columns),
            link=cache_match_merge_link_result.s(identifier, progress_data.key)
        )

        return progress_data.key

    @api_endpoint_class
    @ajax_request_class
    def list(self, request):
        """
        Retrieves all orgs the user has access to.
        ---
        type:
            organizations:
                required: true
                type: array[organizations]
                description: Returns an array where each item is a full organization structure, including
                             keys ''name'', ''org_id'', ''number_of_users'', ''user_is_owner'',
                             ''user_role'', ''sub_orgs'', ...
        """

        # if brief==true only return high-level organization details
        brief = request.GET.get('brief', '') == 'true'

        if brief:
            if request.user.is_superuser:
                qs = Organization.objects.only('id', 'name', 'parent_org_id')
            else:
                qs = request.user.orgs.only('id', 'name', 'parent_org_id')

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

    @method_decorator(permission_required('seed.can_access_admin'))
    @api_endpoint_class
    @ajax_request_class
    def destroy(self, request, pk=None):
        """
        Starts a background task to delete an organization and all related data.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              type: integer
              description: Organization ID (primary key)
              required: true
              paramType: path
        type:
            status:
                description: success or error
                type: string
                required: true
            progress_key:
                description: ID of background job, for retrieving job progress
                type: string
                required: true
        """

        return JsonResponse(tasks.delete_organization(pk))

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def retrieve(self, request, pk=None):
        """
        Retrieves a single organization by id.
        ---
        type:
            status:
                required: true
                type: string
                description: success, or error
            organization:
                required: true
                type: array[organizations]
                description: Returns an array where each item is a full organization structure, including
                             keys ''name'', ''org_id'', ''number_of_users'', ''user_is_owner'',
                             ''user_role'', ''sub_orgs'', ...
        """
        org_id = pk

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

        return JsonResponse({
            'status': 'success',
            'organization': _dict_org(request, [org])[0],
        })

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['GET'])
    def users(self, request, pk=None):
        """
        Retrieve all users belonging to an org.
        ---
        response_serializer: OrganizationUsersSerializer
        parameter_strategy: replace
        parameters:
            - name: pk
              type: integer
              description: Organization ID (primary key)
              required: true
              paramType: path
        """
        try:
            org = Organization.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(pk)},
                                status=status.HTTP_404_NOT_FOUND)
        users = []
        for u in org.organizationuser_set.all():
            user = u.user

            user_orgs = OrganizationUser.objects.filter(user=user).count()

            users.append({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'number_of_orgs': user_orgs,
                'user_id': user.pk,
                'role': _get_js_role(u.role_level)
            })

        return JsonResponse({'status': 'success', 'users': users})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=True, methods=['DELETE'])
    def remove_user(self, request, pk=None):
        """
        Removes a user from an organization and deletes orphaned users.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
            - name: user_id
              description: User ID (Primary key) of the user to remove from the organization
        type:
            status:
                type: string
                description: success or error
                required: true
            message:
                type: string
                description: info/error message, if any
                required: false
        """
        body = request.data

        try:
            org = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        if body.get('user_id') is None:
            return JsonResponse({
                'status': 'error',
                'message': 'missing the user_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(pk=body['user_id'])
        except User.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'user does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        # A super user can remove a user. The superuser logic is also part of the decorator which
        # checks if super permissions have been limited per the ALLOW_SUPER_USER_PERMS setting.
        org_owner = OrganizationUser.objects.filter(
            user=request.user, organization=org, role_level=ROLE_OWNER
        ).exists()
        if not request.user.is_superuser and not org_owner:
            return JsonResponse({
                'status': 'error',
                'message': 'only the organization owner or superuser can remove a member'
            }, status=status.HTTP_403_FORBIDDEN)

        is_last_member = not OrganizationUser.objects.filter(
            organization=org,
        ).exclude(user=user).exists()

        if is_last_member:
            return JsonResponse({
                'status': 'error',
                'message': 'an organization must have at least one member'
            }, status=status.HTTP_409_CONFLICT)

        is_last_owner = not OrganizationUser.objects.filter(
            organization=org,
            role_level=ROLE_OWNER,
        ).exclude(user=user).exists()

        if is_last_owner:
            return JsonResponse({
                'status': 'error',
                'message': 'an organization must have at least one owner level member'
            }, status=status.HTTP_409_CONFLICT)

        ou = OrganizationUser.objects.get(user=user, organization=org)
        ou.delete()

        # check the user and make sure they still have a valid organization to belong to
        user_orgs = OrganizationUser.objects.filter(user=user)

        if user_orgs.count() == 0:
            # Deactivate orphaned user
            user.is_active = False
            user.save()
        elif user.default_organization == org:
            first_org = user_orgs.order_by('id').first()
            user.default_organization = first_org.organization
            user.save()

        return JsonResponse({'status': 'success'})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    def create(self, request):
        """
        Creates a new organization.
        ---
        parameters:
            - name: organization_name
              description: The new organization name
              type: string
              required: true
            - name: user_id
              description: The user ID (primary key) to be used as the owner of the new organization
              type: integer
              required: true
        type:
           status:
               type: string
               description: success or error
               required: true
           message:
               type: string
               description: error/informational message, if any
               required: false
           organization:
               type: dict
               description: A dictionary of the organization created
               required: false
        """
        body = request.data
        user = User.objects.get(pk=body['user_id'])
        org_name = body['organization_name']

        if Organization.objects.filter(name=org_name).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'organization name already exists'
            }, status=status.HTTP_409_CONFLICT)

        org, _, _ = create_organization(user, org_name, org_name)
        return JsonResponse(
            {
                'status': 'success',
                'message': 'organization created',
                'organization': _dict_org(request, [org])[0]
            }
        )

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=True, methods=['PUT'])
    def add_user(self, request, pk=None):
        """
        Adds an existing user to an organization.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
            - name: user_id
              description: User ID (Primary key) of the user to add to the organization
        type:
            status:
                type: string
                description: success or error
                required: true
            message:
                type: string
                description: info/error message, if any
                required: false
        """
        body = request.data
        org = Organization.objects.get(pk=pk)
        user = User.objects.get(pk=body['user_id'])

        _orguser, status = org.add_member(user, access_level_instance_id=org.root.id)

        # Send an email if a new user has been added to the organization
        if status:
            try:
                domain = request.get_host()
            except Exception:
                domain = 'seed-platform.org'
            invite_to_organization(
                domain, user, request.user.username, org
            )

        return JsonResponse({'status': 'success'})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=True, methods=['PUT'])
    def save_settings(self, request, pk=None):
        """
        Saves an organization's settings: name, query threshold, shared fields
        ---
        type:
            status:
                description: success or error
                type: string
                required: true
            message:
                description: Error message, if any
                type: string
                required: false
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
            - name: body
              description: JSON body containing organization settings information
              paramType: body
              pytype: SaveSettingsSerializer
              required: true
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

        comstock_enabled = posted_org.get('comstock_enabled', False)
        if comstock_enabled != org.comstock_enabled:
            org.comstock_enabled = comstock_enabled

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
    @action(detail=True, methods=['GET'])
    def query_threshold(self, request, pk=None):
        """
        Returns the "query_threshold" for an org.  Searches from
        members of sibling orgs must return at least this many buildings
        from orgs they do not belong to, or else buildings from orgs they
        don't belong to will be removed from the results.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
        type:
            status:
                type: string
                required: true
                description: success or error
            query_threshold:
                type: integer
                required: true
                description: Minimum number of buildings that must be returned from a search to avoid
                             squelching non-member-org results
        """
        org = Organization.objects.get(pk=pk)
        return JsonResponse({
            'status': 'success',
            'query_threshold': org.query_threshold
        })

    # TODO: Shared fields structure has a "class" attribute that won't serialize
    @api_endpoint_class
    @ajax_request_class
    @action(detail=True, methods=['GET'])
    def shared_fields(self, request, pk=None):
        """
        Retrieves all fields marked as shared for the organization. Will only return used fields.

        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
        response_serializer: SharedFieldsActualReturnSerializer
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

    @api_endpoint_class
    @ajax_request_class
    @action(detail=True, methods=['POST'])
    def sub_org(self, request, pk=None):
        """
        Creates a child org of a parent org.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
            - name: sub_org_name
              description: Name of the new sub organization
              type: string
              required: true
            - name: sub_org_owner_email
              description: Email of the owner of the sub organization, which must already exist
              type: string
              required: true
        type:
            status:
                type: string
                description: success or error
                required: true
            message:
                type: string
                description: error message, if any
                required: true
            organization_id:
                type: integer
                description: ID of newly-created org
                required: true
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
        ---
        response_serializer: OrganizationUsersSerializer
        parameter_strategy: replace
        parameters:
            - name: pk
              type: integer
              description: Organization ID (primary key)
              required: true
              paramType: path
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
    @action(detail=True, methods=['POST'])
    def match_merge_link(self, request, pk=None):
        """
        Run match_merge_link for an org.
        ---
        parameters:
            - name: pk
              type: integer
              description: Organization ID (primary key)
              required: true
              paramType: path
        """
        inventory_type = request.data.get('inventory_type', None)
        if inventory_type not in ['properties', 'taxlots']:
            return JsonResponse({'status': 'error',
                                 'message': 'Provided inventory type should either be "properties" or "taxlots".'},
                                status=status.HTTP_404_NOT_FOUND)

        try:
            org = Organization.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(pk)},
                                status=status.HTTP_404_NOT_FOUND)

        state_class_name = 'PropertyState' if inventory_type == 'properties' else 'TaxLotState'

        progress_key = self._start_whole_org_match_merge_link(org.id, state_class_name)

        return JsonResponse({'progress_key': progress_key})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['POST'])
    def match_merge_link_preview(self, request, pk=None):
        """
        Run match_merge_link preview for an org and record type.
        ---
        parameters:
            - name: pk
              type: integer
              description: Organization ID (primary key)
              required: true
              paramType: path
        """
        inventory_type = request.data.get('inventory_type', None)
        if inventory_type not in ['properties', 'taxlots']:
            return JsonResponse({'status': 'error',
                                 'message': 'Provided inventory type should either be "properties" or "taxlots".'},
                                status=status.HTTP_404_NOT_FOUND)

        try:
            org = Organization.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(pk)},
                                status=status.HTTP_404_NOT_FOUND)

        state_class_name = 'PropertyState' if inventory_type == 'properties' else 'TaxLotState'

        current_columns = matching_criteria_column_names(org.id, state_class_name)

        add = set(request.data.get('add', []))
        remove = set(request.data.get('remove', []))

        provided_columns = Column.objects.filter(
            column_name__in=add.union(remove),
            organization_id=org.id,
            table_name=state_class_name
        )
        if provided_columns.count() != (len(add) + len(remove)):
            return JsonResponse({'status': 'error',
                                 'message': 'Invalid column names provided.'},
                                status=status.HTTP_404_NOT_FOUND)

        proposed_columns = current_columns.union(add).difference(remove)

        progress_key = self._start_whole_org_match_merge_link(org.id, state_class_name, list(proposed_columns))

        return JsonResponse({'progress_key': progress_key})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['GET'])
    def match_merge_link_result(self, request, pk=None):
        try:
            Organization.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(pk)},
                                status=status.HTTP_404_NOT_FOUND)

        identifier = request.query_params['match_merge_link_id']
        result_key = _get_match_merge_link_key(identifier)

        return JsonResponse(get_cache_raw(result_key))

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['GET'])
    def geocoding_columns(self, request, pk=None):
        """
        Retrieve all geocoding columns for an org.
        ---
        response_serializer: OrganizationUsersSerializer
        parameter_strategy: replace
        parameters:
            - name: pk
              type: integer
              description: Organization ID (primary key)
              required: true
              paramType: path
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

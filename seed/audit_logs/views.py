# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
# system imports
import json

# django imports
from django.contrib.auth.decorators import login_required

# app imports
from seed.decorators import ajax_request, require_organization_id
from seed.lib.superperms.orgs.decorators import has_perm
from seed.utils.api import api_endpoint
from seed.models import CanonicalBuilding
from seed.audit_logs.models import AuditLog, NOTE


# TODO: CLEANUP move to deprecate
@require_organization_id
@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_building_logs(request):
    """
    Retrieves logs for a building.

    :GET: Expects the CanonicalBuildings's id in the query string as
        building_id.
        Expects an organization_id (to which project belongs) in the query
        string.

    Returns::

        'audit_logs' : [
            {
                'user': {
                    'first_name': user's firstname,
                    'last_name': user's last_name,
                    'id': user's id,
                    'email': user's email address
                },
                'id': audit log's id,
                'audit_type': 'Log' or 'Note',
                'created': DateTime,
                'modified': DateTime,
                'action': method triggering log entry,
                'action_response': response of action,
                'action_note': the note body if Note or further description
                'organization': {
                    'name': name of org,
                    'id': id of org
                }
            }, ...
        ],
        'status': 'success'

    """
    cb = CanonicalBuilding.objects.get(
        pk=request.GET.get('building_id')
    )
    org_id = request.GET['organization_id']
    log_qs = cb.audit_logs.filter(organization=org_id)

    audit_logs = [log.to_dict() for log in log_qs]
    return {
        'status': 'success',
        'audit_logs': audit_logs
    }


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def create_note(request):
    """
    Retrieves logs for a building.

    :POST: Expects the CanonicalBuildings's id in the JSON payload as
        building_id.
        Expects an organization_id (to which project belongs) in the query
        string.
        Expects the action_note to be in the JSON payload as action_note

    Returns::

        'audit_log' : {
            'user': {
                'first_name': user's firstname,
                'last_name': user's last_name,
                'id': user's id,
                'email': user's email address
            },
            'id': audit log's id,
            'audit_type': 'Note',
            'created': DateTime,
            'modified': DateTime,
            'action': method triggering log entry,
            'action_response': response of action,
            'action_note': the note body
            'organization': {
                'name': name of org,
                'id': id of org
        },
        'status': 'success'

    """
    body = json.loads(request.body)
    cb = CanonicalBuilding.objects.get(
        pk=body['building_id']
    )
    org_id = body['organization_id']
    audit_log = AuditLog.objects.log_action(
        request, cb, org_id, action_note=body['action_note'], audit_type=NOTE
    )
    return {
        'status': 'success',
        'audit_log': audit_log.to_dict()
    }


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def update_note(request):
    """
    Retrieves logs for a building.

    :PUT: Expects the CanonicalBuildings's id in the JSON payload as
        building_id.
        Expects an organization_id (to which project belongs) in the query
        string.
        Expects the action_note to be in the JSON payload as action_note
        Expects the audit_log_id to be in the JSON payload as audit_log_id

    Returns::

        'audit_log' : {
            'user': {
                'first_name': user's firstname,
                'last_name': user's last_name,
                'id': user's id,
                'email': user's email address
            },
            'id': audit log's id,
            'audit_type': 'Note',
            'created': DateTime,
            'modified': DateTime,
            'action': method triggering log entry,
            'action_response': response of action,
            'action_note': the note body
            'organization': {
                'name': name of org,
                'id': id of org
        },
        'status': 'success'

    """
    body = json.loads(request.body)
    audit_log = AuditLog.objects.get(pk=body['audit_log_id'])
    audit_log.action_note = body['action_note']
    audit_log.user = request.user
    audit_log.save()
    return {
        'status': 'success',
        'audit_log': audit_log.to_dict()
    }

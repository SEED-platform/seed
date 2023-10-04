# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
import logging
import os
import subprocess

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from rest_framework import status
from rest_framework.decorators import api_view

from seed.celery import app
from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.utils.api import api_endpoint
from seed.utils.users import get_js_role

_log = logging.getLogger(__name__)


def angular_js_tests(request):
    """Jasmine JS unit test code covering AngularJS unit tests"""
    debug = settings.DEBUG
    return render(request, 'seed/jasmine_tests/AngularJSTests.html', locals())


def _get_default_org(user):
    """Gets the default org for a user and returns the id, name, and
    role_level. If no default organization is set for the user, the first
    organization the user has access to is set as default if it exists.

    :param user: the user to get the default org
    :returns: tuple (Organization id, Organization name, OrganizationUser role)
    """
    org = user.default_organization
    # check if user is still in the org, i.e., they weren't removed from their
    # default org or did not have a set org and try to set the first one
    if not org or not user.orgs.exists():
        org = user.orgs.first()
        user.default_organization = org
        user.save()
    if org:
        org_id = org.pk
        org_name = org.name
        ou = user.organizationuser_set.filter(organization=org).first()
        # parent org owner has no role (None) yet has access to the sub-org
        org_user_role = get_js_role(ou.role_level) if ou else ""
        ali_name = ou.access_level_instance.name
        ali_id = ou.access_level_instance.id
        is_ali_root = ou.access_level_instance == ou.organization.root
        return org_id, org_name, org_user_role, ali_name, ali_id, is_ali_root
    else:
        return "", "", "", "", "", ""


@login_required
def home(request):
    """the main view for the app
        Sets in the context for the django template:

        * **app_urls**: a json object of all the URLs that is loaded in the JS global namespace
        * **username**: the request user's username (first and last name)
    """
    username = request.user.first_name + " " + request.user.last_name
    initial_org_id, initial_org_name, initial_org_user_role, access_level_instance_name, access_level_instance_id, is_ali_root = _get_default_org(
        request.user
    )
    debug = settings.DEBUG
    return render(request, 'seed/index.html', locals())


@api_endpoint
@ajax_request
@api_view(['GET'])
@has_perm_class('requires_superuser', False)
def celery_queue(request):
    """
    Returns the number of running and queued celery tasks. This action can only be performed by superusers

    Returns::

        {
            'active': {'total': n, 'tasks': []}, // Tasks that are currently being executed
            'reserved': {'total': n, 'tasks': []}, // Tasks waiting to be executed
            'scheduled': {'total': n, 'tasks': []}, // Tasks reserved by the worker when they have an eta or countdown
            'maxConcurrency': The maximum number of active tasks
        }
    """
    celery_tasks = app.control.inspect()
    results = {}

    methods = ('active', 'reserved', 'scheduled', 'stats')
    for method in methods:
        result = getattr(celery_tasks, method)()
        if result is None or 'error' in result:
            results[method] = 'Error'
            continue
        for worker, response in result.items():
            if method == 'stats':
                results['maxConcurrency'] = response['pool']['max-concurrency']
            else:
                if response is not None:
                    total = len(response)
                    results[method] = {'total': total}
                    if total > 0:
                        results[method]['tasks'] = list(set([t['name'] for t in response]))
                else:
                    results[method] = {'total': 0}

    return JsonResponse(results)


@api_endpoint
@ajax_request
@api_view(['GET'])
def version(request):
    """
    Returns the SEED version and current git sha
    """
    manifest_path = os.path.dirname(
        os.path.realpath(__file__)) + '/../../package.json'
    with open(manifest_path, encoding='utf-8') as package_json:
        manifest = json.load(package_json)

    sha = subprocess.check_output(
        ['git', 'rev-parse', '--short=9', 'HEAD']).strip()

    return JsonResponse({
        'version': manifest['version'],
        'sha': sha.decode('utf-8')
    })


def error404(request, exception):
    if '/api/' in request.path:
        return JsonResponse({
            "status": "error",
            "message": "Endpoint could not be found",
        }, status=status.HTTP_404_NOT_FOUND)
    else:
        return redirect('/app/#?http_error=404')


def error410(request):
    if '/api/' in request.path:
        return JsonResponse({
            "status": "error",
            "message": "Deprecated API endpoint",
        }, status=status.HTTP_410_GONE)
    else:
        return redirect('/app/#?http_error=410')


def error500(request):
    if '/api/' in request.path:
        return JsonResponse({
            "status": "error",
            "message": "Internal server error",
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return redirect('/app/#?http_error=500')

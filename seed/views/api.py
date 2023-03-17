# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from seed.decorators import ajax_request
from seed.utils.api import (
    api_endpoint,
    format_api_docstring,
    get_api_endpoints
)


@api_endpoint
@ajax_request
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
def get_api_schema(request):
    """
    Returns a hash of all API endpoints and their descriptions.

    Returns::

        {
            '/example/url/here': {
                'name': endpoint name,
                'description': endpoint description
            }...
        }

    .. todo:: Format docstrings better.
    """

    endpoints = get_api_endpoints()

    resp = {}
    for url, fn in endpoints.items():
        desc = format_api_docstring(fn.__doc__)
        endpoint_details = {'name': fn.__name__, 'description': desc}
        resp[url] = endpoint_details
    return JsonResponse(resp)

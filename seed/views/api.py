# !/usr/bin/env python
# encoding: utf-8
#
# :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
# :author

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from seed.decorators import ajax_request
from seed.utils.api import (
    get_api_endpoints, format_api_docstring, api_endpoint
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

# !/usr/bin/env python
# encoding: utf-8
#
# :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
# :author

from seed.decorators import ajax_request
from seed.utils.api import (
    get_api_endpoints, format_api_docstring, api_endpoint
)
from rest_framework.decorators import api_view
from rest_framework import serializers

class APIEndpointSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()

class APISchemaSerializer(serializers.Serializer):
    endpoints = serializers.DictField(
        child = APIEndpointSerializer()
    )

@api_view(['GET'])
@api_endpoint
@ajax_request
def get_api_schema(request):
    """
    Returns a hash of all API endpoints and their descriptions.
    ---
    response_serializer: APISchemaSerializer
    """

    """
    Returns::

        {
            '/example/url/here': {
                'name': endpoint name,
                'description': endpoint description
            }...
        }


    .. todo:: Should this require authentication?  Should it limit the return to endpoints the user has authorization for?

    .. todo:: Format docstrings better.
    """
    endpoints = get_api_endpoints()

    resp = {}
    for url, fn in endpoints.items():
        desc = format_api_docstring(fn.func_doc)
        endpoint_details = {'name': fn.func_name,
                            'description': desc}
        resp[url] = endpoint_details
    return resp

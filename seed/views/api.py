# !/usr/bin/env python
# encoding: utf-8
#
# :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
# :author

from seed.decorators import ajax_request
from seed.utils.api import (
    get_api_endpoints, format_api_docstring, api_endpoint
)

from django.core.urlresolvers import reverse_lazy

from rest_framework.reverse import reverse


@api_endpoint
@ajax_request
def test_view_with_arg(request, pk=None):
    """
    Hi
    :param request: some stuff
    :param pk: more stuff
    :return: nothing
    """
    return {'value of pk': pk}


@api_endpoint
@ajax_request
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


    .. todo:: Should this require authentication?  Should it limit the return to endpoints the user has authorization for?

    .. todo:: Format docstrings better.
    """
    i = {}
    i['api:testviewarg'] = reverse('api:testviewarg', args=[1])
    i['seed:get_column_mapping_suggestions'] = reverse('seed:get_column_mapping_suggestions')
    i['apiv2:datasets-list'] = reverse('apiv2:datasets-list')
    # i = reverse('seed:get_building', args=['pk'])
    return str(i)

    endpoints = get_api_endpoints()

    resp = {}
    for url, fn in endpoints.items():
        desc = format_api_docstring(fn.func_doc)
        endpoint_details = {'name': fn.func_name,
                            'description': desc}
        resp[url] = endpoint_details
    return resp

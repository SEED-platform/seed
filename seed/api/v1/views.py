# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import json

from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import list_route

from seed.authentication import SEEDAuthentication
from seed.decorators import ajax_request_class, require_organization_id_class
from seed.utils.api import api_endpoint_class
from seed.utils.buildings import (
    get_columns as utils_get_columns,
)

DEFAULT_CUSTOM_COLUMNS = [
    'project_id',
    'project_building_snapshots__status_label__name',
    'address_line_1',
    'city',
    'state_province',
]


class ColumnViewSetV1(viewsets.ViewSet):
    raise_exception = True
    authentication_classes = (SessionAuthentication, SEEDAuthentication)

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    def list(self, request):
        """
        Returns a JSON list of columns a user can select as his/her default

        Requires the organization_id as a query parameter.

        This was formally /get_columns
        """
        all_fields = request.query_params.get('all_fields', '')
        all_fields = True if all_fields.lower() == 'true' else False
        return JsonResponse(utils_get_columns(request.query_params['organization_id'], all_fields))

    @api_endpoint_class
    @ajax_request_class
    @list_route(methods=['GET'])
    def get_default_columns(self, request):
        """
        Get default columns for building list view.

        front end is expecting a JSON object with an array of field names

        Returns::

            {
                "columns": ["project_id", "name", "gross_floor_area"]
            }
        """
        columns = request.user.default_custom_columns

        if columns == '{}' or isinstance(columns, dict):
            columns = DEFAULT_CUSTOM_COLUMNS
        if isinstance(columns, unicode):
            # PostgreSQL 9.1 stores JSONField as unicode
            columns = json.loads(columns)

        return JsonResponse({
            'columns': columns,
        })

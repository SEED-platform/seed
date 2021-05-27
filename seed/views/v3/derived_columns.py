# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.http import JsonResponse
from rest_framework import viewsets

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import DerivedColumn
from seed.serializers.derived_columns import DerivedColumnSerializer
from seed.utils.api import api_endpoint_class, OrgMixin


class DerivedColumnViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = DerivedColumnSerializer
    model = DerivedColumn

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        org = self.get_organization(request)

        filter_params = {
            'organization': org,
        }

        inventory_type = {
            'properties': DerivedColumn.PROPERTY_TYPE,
            'taxlots': DerivedColumn.TAXLOT_TYPE,
        }.get(request.query_params.get('inventory_type'))

        if inventory_type is not None:
            filter_params['inventory_type'] = inventory_type

        queryset = DerivedColumn.objects.filter(**filter_params)

        return JsonResponse({
            'status': 'success',
            'derived_columns': DerivedColumnSerializer(queryset, many=True).data
        })

# !/usr/bin/env python
# encoding: utf-8

from rest_framework import viewsets
from rest_framework.decorators import list_route

from seed.decorators import ajax_request_class

from seed.lib.superperms.orgs.decorators import has_perm_class

from seed.models.properties import PropertyState

from seed.utils.api import api_endpoint_class
from seed.utils.ubid import decode_ubids


class UbidViews(viewsets.ViewSet):
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @list_route(methods=['POST'])
    def decode_by_ids(self, request):
        body = dict(request.data)
        property_ids = body.get('property_ids')

        if property_ids:
            properties = PropertyState.objects.filter(id__in=property_ids)
            decode_ubids(properties)

    @ajax_request_class
    @list_route(methods=['POST'])
    def decode_results(self, request):
        body = dict(request.data)
        property_ids = body.get('property_ids')
        properties = PropertyState.objects.filter(id__in=property_ids)

        ubid_unpopulated = len(properties.filter(ubid__isnull=True))
        ubid_successfully_decoded = len(properties.filter(ubid__isnull=False, bounding_box__isnull=False, centroid__isnull=False))

        # for ubid_not_decoded, bounding_box could be populated from a GeoJSON import
        ubid_not_decoded = len(properties.filter(ubid__isnull=False, centroid__isnull=True))

        result = {
            "ubid_unpopulated": ubid_unpopulated,
            "ubid_successfully_decoded": ubid_successfully_decoded,
            "ubid_not_decoded": ubid_not_decoded
        }

        return result

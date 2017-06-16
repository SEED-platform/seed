# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
# import json

from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import list_route
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer

from seed.authentication import SEEDAuthentication
from seed.models import (
    Measure,
)
from seed.pagination import NoPagination


class MeasureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API View for measures. This only includes retrieve and list since the measures are immutable.

    The reset POST method is for reseting the measures back to the default list provided
    by BuildingSync enumeration.json file.
    """
    # serializer_class = MeasureSerializer
    authentication_classes = [SessionAuthentication, SEEDAuthentication]
    parser_classes = (JSONParser, FormParser,)
    renderer_classes = (JSONRenderer,)
    queryset = Measure.objects.all()
    pagination_class = NoPagination

    @list_route(methods=['POST'])
    def reset(self, request):
        """
        Reset all the measures back to the defaults (as provided by BuildingSync)
        ---
        parameters: {}
        type:
            status:
                required: true
                type: string
                description: Either success or error
            measures:
                required: true
                type: list
                description: list of measures
        """
        Measure.populate_measures()
        data = dict(measures=list(Measure.objects.order_by('id').values()))

        data['status'] = 'success'
        return JsonResponse(data)

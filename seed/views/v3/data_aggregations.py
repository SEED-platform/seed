# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from copy import deepcopy
import django.core.exceptions
from django.http import JsonResponse
from seed.decorators import ajax_request_class
from seed.serializers.data_aggregations import DataAggregationSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from rest_framework import viewsets
from seed.models.data_aggregations import DataAggregation



class DataAggregationViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = DataAggregationSerializer
    model = DataAggregation

    @api_endpoint_class
    @ajax_request_class
    def list(self, request):
        data_aggregation_queryset = DataAggregation.objects.all()

        return JsonResponse({
            'status': 'success',
            'message': DataAggregationSerializer(data_aggregation_queryset, many=True).data
        })

    @api_endpoint_class
    @ajax_request_class
    def create(self, request):
        breakpoint()
        data = deepcopy(request.data)
        serializer = DataAggregationSerializer(data=data)

        try: 
            serializer.save()
            return JsonResponse({
                'status': 'sucess',
                'data_aggregation': serializer.data
            })
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict

        


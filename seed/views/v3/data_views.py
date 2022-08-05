# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from copy import deepcopy
import logging

import django.core.exceptions
from django.core import serializers
from django.http import JsonResponse
from django.forms.models import model_to_dict
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.models.data_views import DataView
from seed.serializers.data_views import DataViewSerializer
from seed.serializers.cycles import CycleSerializer
from seed.serializers.columns import ColumnSerializer
from seed.serializers.data_aggregations import DataAggregationSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import (
    AutoSchemaHelper,
    swagger_auto_schema_org_query_param
)

from seed.models import Column, Cycle, DataAggregation


class DataViewViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = DataViewSerializer
    model = DataView

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        organization_id = self.get_organization(request)
        data_view_queryset = DataView.objects.filter(organization=organization_id)

        return JsonResponse({
            'status': 'success',
            'message': DataViewSerializer(data_view_queryset, many=True).data
        })

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def retrieve(self, request, pk):
        organization = self.get_organization(request)

        try:
            data_view = DataView.objects.get(id=pk, organization=organization)
            return JsonResponse({
                'status': 'success',
                'data_view': {
                    'id': data_view.id,
                    'name': data_view.name,
                    'organization': data_view.organization.id
                }
            })
        except DataView.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'DataView with id {pk} does not exist'
            })


    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def destroy(self, request, pk):
        organization_id = self.get_organization(request)

        try:
            DataView.objects.get(id=pk, organization=organization_id).delete()
        except DataView.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'DataView with id {pk} does not exist'
            })

        return JsonResponse({
            'status': 'success',
            'message': f'Successfully deleted DataView ID {pk}'
        })

    def validate_data(self, data):
        error_message = ''
        if not data.get('name'):
            error_message += 'Data View Name required \n'
        if not data.get('organization'):
            error_message += 'Data View Organization required \n'
        if not data.get('filter_group'):
            error_message += 'Data View FilterGroup required \n'
        if not data.get('columns'):
            error_message += 'Data View Columns required \n'
        if not data.get('cycles'):
            error_message += 'Data View Cycles required \n'
        if not data.get('data_aggregations'):
            error_message += 'Data View DataAggregation required \n'
        if error_message: 
            return JsonResponse({
                'status': 'error',
                'message': error_message
            })

            

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'name': 'string',
                'columns': ['integer'],
                'cycles': ['integer'],
                'data_aggregations': ['integer'],
            },
        )
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def create(self, request):
        org_id = self.get_organization(request)
        data = deepcopy(request.data)
        data.update({'organization': org_id})
        serializer = DataViewSerializer(data=data)

        if not serializer.is_valid():
            logging.error('SERIALIZER IS NOT VALID')
            error_response = {
                'status': 'error',
                'message': 'Data Validation Error',
                'errors': serializer.errors
            }
          
            return JsonResponse(error_response)

        # validation_error = self.validate_data(data)
        # if validation_error: 
        #     return validation_error

        
        # data2 = deepcopy(request.data)
        # data3 = deepcopy(request.data)
        # data4 = deepcopy(request.data)
        # data5 = deepcopy(request.data)
        # organization = Organization.objects.get(id=org_id)
        # columns = Column.objects.filter(id__in=data['columns'])
        # data2['columns'] = [model_to_dict(col) for col in columns]
        # data3['columns'] = [col.__dict__ for col in columns]
        # data4['columns'] = [ColumnSerializer(col) for col in columns]

        # cycles = Cycle.objects.filter(id__in=data['cycles'])
        # data2['cycles'] = [model_to_dict(cycle) for cycle in cycles]
        # data3['cycles'] = [cycle.__dict__ for cycle in cycles]
        # data4['cycles'] = [CycleSerializer(cycle) for cycle in cycles]


        # data_aggregations = DataAggregation.objects.filter(id__in=data['data_aggregations'])
        # data2['data_aggregations'] = [model_to_dict(da) for da in data_aggregations]
        # data3['data_aggregations'] = [da.__dict__ for da in data_aggregations]
        # data4['data_aggregations'] = [DataAggregationSerializer(da) for da in data_aggregations]


        # data5 = deepcopy(data2)
        # [col.pop('merge_protection') for col in data5['columns']]

        # for col in data5['columns']:
        #     col['shared_field_type'] = None
        # type_conversion = {0: 'Average', 1: 'Count', 2: 'Max', 3: 'Min', 4: 'Sum'}
        # for da in data5['data_aggregations']:
        #     da['type'] = type_conversion[da['type']]

        # breakpoint()


        # data_view = DataView.objects.create(name=data['name'], filter_group=data['filter_group'], organization=organization)
        # data_view.columns.set(columns)
        # data_view.cycles.set(cycles)
        # data_view.data_aggregations.set(data_aggregations)

        # try:
        #     data_view.save()
        #     return JsonResponse({
        #         'status': 'success',
        #         'data_view': {
        #             'id': data_view.id,
        #             'name': data_view.name,
        #             'organization': data_view.organization.id,
        #         }
        #     })
        try:
            serializer.save()
            return JsonResponse({
                'status': 'success',
                'data_view': serializer.data
            })
        except django.core.exceptions.ValidationError as e:
            logging.error('SERIALIZER.SAVE FAIL')

            message_dict = e.message_dict
            return JsonResponse({
                'status': 'error',
                'message': 'Bad Request',
                'errors': message_dict
            })



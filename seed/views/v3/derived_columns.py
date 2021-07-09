# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from copy import deepcopy

from django.http import JsonResponse
import django.core.exceptions

from rest_framework import viewsets, status
from rest_framework.decorators import action

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema, no_body

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import DerivedColumn, TaxLotView, PropertyView
from seed.serializers.derived_columns import DerivedColumnSerializer
from seed.utils.api import api_endpoint_class, OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param, AutoSchemaHelper


class DerivedColumnViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = DerivedColumnSerializer
    model = DerivedColumn

    @swagger_auto_schema_org_query_param
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

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def retrieve(self, request, pk):
        org = self.get_organization(request)

        try:
            return JsonResponse({
                'status': 'success',
                'derived_column': DerivedColumnSerializer(
                    DerivedColumn.objects.get(organization=org, id=pk)
                ).data
            })
        except DerivedColumn.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'Derived column with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def create(self, request):
        org_id = self.get_organization(request)

        data = deepcopy(request.data)
        data.update({'organization': org_id})
        serializer = DerivedColumnSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({
                'status': 'error',
                'message': 'Bad request',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save()
            return JsonResponse({
                'status': 'success',
                'derived_column': serializer.data,
            }, status=status.HTTP_200_OK)
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict

            # rename key __all__ to general to make it more user friendly
            if '__all__' in message_dict:
                message_dict['general'] = message_dict.pop('__all__')
            return JsonResponse({
                'status': 'error',
                'message': 'Bad request',
                'errors': message_dict,
            }, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def update(self, request, pk):
        org_id = self.get_organization(request)

        derived_column = None
        try:
            derived_column = DerivedColumn.objects.get(id=pk, organization_id=org_id)
        except DerivedColumn.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'Derived column with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        data = deepcopy(request.data)
        data.update({'organization': org_id})
        serializer = DerivedColumnSerializer(derived_column, data=data, partial=True)
        if not serializer.is_valid():
            return JsonResponse({
                'status': 'error',
                'message': 'Bad request',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save()
            return JsonResponse({
                'status': 'success',
                'derived_column': serializer.data,
            }, status=status.HTTP_200_OK)
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict

            # rename key __all__ to general to make it more user friendly
            if '__all__' in message_dict:
                message_dict['general'] = message_dict.pop('__all__')
            return JsonResponse({
                'status': 'error',
                'message': 'Bad request',
                'errors': message_dict,
            }, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def destroy(self, request, pk):
        org_id = self.get_organization(request)

        try:
            DerivedColumn.objects.get(id=pk, organization_id=org_id).delete()
        except DerivedColumn.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'Derived column with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse({
            'status': 'success',
            'message': 'Successfully deleted derived column',
        })

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                name='cycle_id',
                required=True,
                description='Cycle to evaluate'
            ),
            openapi.Parameter(
                'inventory_ids',
                openapi.IN_QUERY,
                description='List of inventory IDs (i.e. Property or TaxLot)',
                required=True,
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_INTEGER
                )
            )
        ],
        request_body=no_body
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=True, methods=['GET'])
    def evaluate(self, request, pk):
        org = self.get_organization(request)

        cycle_id, inventory_ids = None, None
        try:
            cycle_id = request.query_params['cycle_id']
            inventory_ids = [int(x) for x in request.query_params['inventory_ids'].split(',')]
        except (KeyError, ValueError):
            return JsonResponse({
                'status': 'error',
                'message': 'Bad request',
            }, status=status.HTTP_400_BAD_REQUEST)

        derived_column = None
        try:
            derived_column = DerivedColumn.objects.get(id=pk, organization=org)
        except DerivedColumn.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'Derived column with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        inventory_map = {
            DerivedColumn.PROPERTY_TYPE: ('property', PropertyView),
            DerivedColumn.TAXLOT_TYPE: ('taxlot', TaxLotView),
        }
        inventory_name, view_model = inventory_map[derived_column.inventory_type]

        inventory_views = view_model.objects.filter(**{
            f'{inventory_name}_id__in': inventory_ids,
            f'{inventory_name}__organization': org,
            'cycle_id': cycle_id,
        }).prefetch_related('state', inventory_name)

        results = []
        for view in inventory_views:
            results.append({
                'id': getattr(view, inventory_name).id,
                'value': derived_column.evaluate(view.state)
            })

        return JsonResponse({
            'status': 'success',
            'results': results
        })

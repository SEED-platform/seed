# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Paul Munday<paul@paulmunday.net>
"""
import datetime

from django.forms.models import model_to_dict
from django.http import JsonResponse
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import Cycle, PropertyView, TaxLotView
from seed.serializers.cycles import CycleSerializer
from seed.utils.api import api_endpoint_class


class CycleView(GenericViewSet):
    renderer_classes = (JSONRenderer,)
    serializer_class = CycleSerializer

    @api_endpoint_class
    @ajax_request_class
    def retrieve(self, request, pk=None):
        """
        Retrieves a cycle
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        # make sure query org id is in this user's orgs
        org_id_in_query = request.query_params.get('organization_id', None)
        cycles = Cycle.objects.filter(
            organization_id=org_id_in_query, pk=pk
        )
        if cycles.exists():
            cycle = cycles[0]
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Could not access cycle with id={}'.format(pk)
            }, status=status.HTTP_403_FORBIDDEN)
        return JsonResponse({'status': 'success', 'cycle': model_to_dict(cycle)})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        """
        List all the cycles
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        org_id = int(request.query_params.get('organization_id', None))
        valid_orgs = OrganizationUser.objects.filter(
            user_id=request.user.id
        ).values_list('organization_id', flat=True).order_by('organization_id')
        if org_id not in valid_orgs:
            return JsonResponse({
                'status': 'error',
                'message': 'Cannot access cycles for this organization id',
            }, status=status.HTTP_403_FORBIDDEN)

        tmp_cycles = Cycle.objects.filter(
            organization_id=org_id
        ).order_by('name')
        cycles = []
        for cycle in tmp_cycles:
            cycles.append(model_to_dict(cycle))
        return JsonResponse({'status': 'success', 'cycles': cycles})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    def create(self, request):
        """
        Creates a new cycle.
        ---
        parameters:
            - name: organization_id
              description: The organization_id
              required: true
              paramType: query
        """

        body = request.data
        org_id = int(request.query_params.get('organization_id', None))
        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'organization_id not provided'},
                                status=status.HTTP_400_BAD_REQUEST)
        record = Cycle.objects.create(
            organization=org,
            user=request.user,
            name=body['name'],
            start=body['start'],
            end=body['end'],
            created=datetime.datetime.now()
        )
        return JsonResponse({'status': 'success', 'id': record.pk, 'name': record.name})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    def update(self, request, pk=None):
        """
        Updates a cycle
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            message:
                type: string
                description: error message, if any
        parameters:
            - name: organization_id
              description: The organization_id
              required: true
              paramType: query
        """
        body = request.data
        organization_id = int(
            request.query_params.get('organization_id', None))
        cycle = Cycle.objects.filter(pk=pk, organization_id=organization_id)
        cycle.update(
            name=body['name'],
            start=body['start'],
            end=body['end']
        )
        cycle = cycle[0]
        return JsonResponse({'status': 'success', 'cycles': model_to_dict(cycle)})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    def destroy(self, request, pk=None):
        """
        Deletes a cycle
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            message:
                type: string
                description: error message, if any
        parameters:
            - name: organization_id
              description: The organization_id
              required: true
              paramType: query
        """

        organization_id = int(
            request.query_params.get('organization_id', None))
        # check if user has access to the dataset
        cycle = Cycle.objects.filter(
            organization_id=organization_id, pk=pk
        )
        if not cycle.exists():
            return JsonResponse({
                'status': 'error',
                'message': 'cannot access cycle at this organization id and cycle id',
            }, status=status.HTTP_403_FORBIDDEN)
        else:
            cycle = cycle[0]

        # Check that cycle is empty
        num_properties = PropertyView.objects.filter(cycle=cycle).count()
        num_taxlots = TaxLotView.objects.filter(cycle=cycle).count()

        if num_properties > 0 or num_taxlots > 0:
            return {'status': 'error', 'message': 'Cycle not empty'}
        else:
            cycle.delete()

        return JsonResponse({'status': 'success'})

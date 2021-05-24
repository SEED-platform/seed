# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:authors Paul Munday<paul@paulmunday.net> Fable Turas <fable@raintechpdx.com>
"""
from django.http import JsonResponse
from django.utils.decorators import method_decorator

from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import Cycle, PropertyView, TaxLotView
from seed.serializers.cycles import CycleSerializer
from seed import tasks
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet
from seed.utils.api_schema import swagger_auto_schema_org_query_param


@method_decorator(
    name='list',
    decorator=swagger_auto_schema_org_query_param)
@method_decorator(
    name='create',
    decorator=swagger_auto_schema_org_query_param)
@method_decorator(
    name='retrieve',
    decorator=swagger_auto_schema_org_query_param)
@method_decorator(
    name='update',
    decorator=swagger_auto_schema_org_query_param)
class CycleViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """API endpoint for viewing and creating cycles (time periods).

        Returns::
            {
                'status': 'success',
                'cycles': [
                    {
                        'id': Cycle`s primary key,
                        'name': Name given to cycle,
                        'start': Start date of cycle,
                        'end': End date of cycle,
                        'created': Created date of cycle,
                        'properties_count': Count of properties in cycle,
                        'taxlots_count': Count of tax lots in cycle,
                        'organization': Id of organization cycle belongs to,
                        'user': Id of user who created cycle
                    }
                ]
            }


    retrieve:
          Return a cycle instance by pk if it is within user`s specified org.

    list:

        Return all cycles available to user through user`s specified org.

    create:
        Create a new cycle within user`s specified org.

    delete:
        Remove an existing cycle.

    update:
        Update a cycle record.

    """
    serializer_class = CycleSerializer
    pagination_class = None
    model = Cycle
    data_name = 'cycles'

    def get_queryset(self):
        org_id = self.get_organization(self.request)
        # Order cycles by name because if the user hasn't specified then the front end WILL default to the first
        return Cycle.objects.filter(organization_id=org_id).order_by('name')

    def perform_create(self, serializer):
        org_id = self.get_organization(self.request)
        user = self.request.user
        serializer.save(organization_id=org_id, user=user)

    @swagger_auto_schema_org_query_param
    @has_perm_class('requires_owner')
    def destroy(self, request, pk):
        organization_id = self.get_organization(request)
        try:
            cycle = Cycle.objects.get(pk=pk, organization_id=organization_id)
        except Cycle.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Cycle not found'
            }, status=HTTP_404_NOT_FOUND)

        has_inventory = PropertyView.objects.filter(cycle=cycle).exists() or TaxLotView.objects.filter(cycle=cycle).exists()
        if has_inventory:
            return JsonResponse({
                'status': 'error',
                'message': 'Cycle has properties or taxlots that must must be removed before it can be deleted.'
            }, status=HTTP_409_CONFLICT)

        result = tasks.delete_organization_cycle(pk, organization_id)
        return JsonResponse(result)

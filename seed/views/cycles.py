# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Paul Munday<paul@paulmunday.net>
"""
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from seed.decorators import DecoratorMixin
from seed.models import Cycle
from seed.serializers.cycles import CycleSerializer
from seed.utils.api import drf_api_endpoint


class CycleView(DecoratorMixin(drf_api_endpoint), ModelViewSet):
    renderer_classes = (JSONRenderer,)
    serializer_class = CycleSerializer

    def get_queryset(self):
        return Cycle.objects.filter(
            organization_id=self.request.GET['organization_id']
        ).order_by('name')

    def get_object(self):
        """Override this so we can easily use the UpdateModelMixin."""
        # self.cycle_pk set in update_cycle()
        pk = getattr(self, 'cycle_pk', None)
        return Cycle.objects.get(pk=pk)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        if not qs:
            result = {'status': 'error', 'message': 'No cycles found.'}
            status_code = status.HTTP_404_NOT_FOUND
        else:
            cycles = [
                self.get_serializer(cycle).data for cycle in qs
            ]
            result = {'status': 'success', 'cycles': cycles}
            status_code = status.HTTP_200_OK
        return Response(result, status=status_code)

    def delete_cycle(self, request, cycle_pk):
        self.cycle_pk = cycle_pk
        return self.destroy(request)

    def create_cycle(self, request):
        return self.create(request)

    def update_cycle(self, request, cycle_pk):
        self.cycle_pk = cycle_pk
        return self.update(request)

    def partial_update_cycle(self, request, cycle_pk):
        self.cycle_pk = cycle_pk
        return self.partial_update(request)

    def get_cycle(self, request, cycle_pk):
        self.cycle_pk = cycle_pk
        return self.retrieve(request)

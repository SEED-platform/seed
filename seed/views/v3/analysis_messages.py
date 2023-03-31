# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.status import HTTP_409_CONFLICT

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import AnalysisMessage
from seed.serializers.analysis_messages import AnalysisMessageSerializer
from seed.utils.api import OrgMixin, api_endpoint_class


class AnalysisMessageViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = AnalysisMessageSerializer
    model = AnalysisMessage

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def list(self, request, analysis_pk, view_pk=None):
        if int(analysis_pk) < 1:
            messages_queryset = AnalysisMessage.objects.filter(analysis__organization=self.get_organization(request)).order_by('-id')
        elif view_pk is None:
            messages_queryset = AnalysisMessage.objects.filter(analysis=analysis_pk).order_by('-id')
        else:
            messages_queryset = AnalysisMessage.objects.filter(analysis=analysis_pk, analysis_property_view=view_pk).order_by('-id')

        return JsonResponse({
            'status': 'success',
            'messages': AnalysisMessageSerializer(messages_queryset, many=True).data
        })

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def retrieve(self, request, pk, analysis_pk, view_pk=None):
        try:
            if view_pk is None:
                message_queryset = AnalysisMessage.objects.get(id=pk, analysis=analysis_pk)
            else:
                message_queryset = AnalysisMessage.objects.get(id=pk, analysis=analysis_pk, analysis_property_view=view_pk)
        except AnalysisMessage.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': "Requested analysis message doesn't exist in this organization and/or analysis."
            }, status=HTTP_409_CONFLICT)

        return JsonResponse({
            'status': 'success',
            'message': AnalysisMessageSerializer(message_queryset).data
        })

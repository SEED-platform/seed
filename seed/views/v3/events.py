"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from rest_framework import status, viewsets

from seed.lib.superperms.orgs.decorators import (
    has_hierarchy_access,
    has_perm_class
)
from seed.models import Event
from seed.serializers.events import EventSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param


class EventViewSet(viewsets.ViewSet, OrgMixin):

    @swagger_auto_schema_org_query_param
    @has_perm_class('requires_viewer')
    @has_hierarchy_access(property_id_kwarg="property_pk")
    def list(self, request, property_pk):
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 100000)

        events = Event.objects.filter(property_id=property_pk).order_by("-created").select_subclasses()

        paginator = Paginator(events, per_page)
        try:
            events = paginator.page(page).object_list
            page = int(page)
        except PageNotAnInteger:
            events = paginator.page(1).object_list
            page = 1
        except EmptyPage:
            events = paginator.page(paginator.num_pages).object_list
            page = paginator.num_pages

        return JsonResponse(
            {
                "status": 'success',
                'pagination': {
                    'page': page,
                    'start': paginator.page(page).start_index(),
                    'end': paginator.page(page).end_index(),
                    'num_pages': paginator.num_pages,
                    'has_next': paginator.page(page).has_next(),
                    'has_previous': paginator.page(page).has_previous(),
                    'total': paginator.count
                },
                "data": EventSerializer(events, many=True).data
            },
            status=status.HTTP_200_OK
        )

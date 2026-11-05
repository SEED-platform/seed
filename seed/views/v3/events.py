"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_serializer
from rest_framework import serializers, status, viewsets

from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import Event
from seed.serializers.events import EventSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import AutoSchemaHelper


class EventListPaginationSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    start = serializers.IntegerField()
    end = serializers.IntegerField()
    num_pages = serializers.IntegerField()
    has_next = serializers.BooleanField()
    has_previous = serializers.BooleanField()
    total = serializers.IntegerField()


@extend_schema_serializer(many=False)
class EventListResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    pagination = EventListPaginationSerializer()
    data = EventSerializer(
        many=True,
        help_text="Events, newest first. Each event also includes its `event_type` (ATEvent, AnalysisEvent, or NoteEvent), "
        "the fields of that type (e.g., `analysis` or `note`, with the `user_id` of its creator), and the `cycle_end_date`",
    )


class EventViewSet(viewsets.ViewSet, OrgMixin):
    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.path_id_field("Property ID", name="property_pk"),
            AutoSchemaHelper.query_integer_field("page", False, "Page number. Default is 1"),
            AutoSchemaHelper.query_integer_field("per_page", False, "Events per page. Default is all events"),
        ],
        responses={200: EventListResponseSerializer},
    )
    @method_decorator(
        [
            has_perm("requires_viewer"),
            has_hierarchy_access(property_id_kwarg="property_pk"),
        ]
    )
    def list(self, request, property_pk):
        page = request.query_params.get("page", 1)
        per_page = request.query_params.get("per_page", 100000)

        # Tie-break on id so event ordering is deterministic on created ties.
        events = Event.objects.filter(property_id=property_pk).order_by("-created", "-id").select_subclasses()

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
                "status": "success",
                "pagination": {
                    "page": page,
                    "start": paginator.page(page).start_index(),
                    "end": paginator.page(page).end_index(),
                    "num_pages": paginator.num_pages,
                    "has_next": paginator.page(page).has_next(),
                    "has_previous": paginator.page(page).has_previous(),
                    "total": paginator.count,
                },
                "data": EventSerializer(events, many=True).data,
            },
            status=status.HTTP_200_OK,
        )

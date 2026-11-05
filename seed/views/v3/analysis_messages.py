"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_serializer
from rest_framework import serializers, viewsets
from rest_framework.status import HTTP_409_CONFLICT

from seed.decorators import ajax_request, require_organization_id
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import AnalysisMessage
from seed.serializers.analysis_messages import AnalysisMessageSerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper


# The serializers below are only used to document responses
@extend_schema_serializer(many=False)
class AnalysisMessageListResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    messages = AnalysisMessageSerializer(many=True)


class AnalysisMessageRetrieveResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = AnalysisMessageSerializer()


@extend_schema(
    parameters=[
        AutoSchemaHelper.query_org_id_field(),
        AutoSchemaHelper.path_id_field("Analysis ID", name="analysis_pk"),
        # only on the `/analyses/{analysis_pk}/views/{views_pk}/views_messages/` routes
        AutoSchemaHelper.path_id_field("Analysis property view ID", name="views_pk"),
    ]
)
class AnalysisMessageViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = AnalysisMessageSerializer
    model = AnalysisMessage

    @extend_schema(
        responses={200: AnalysisMessageListResponseSerializer},
        description="List the messages of an analysis (optionally of one of its property views). An analysis ID of 0 lists the "
        "messages of all analyses in the organization that are within the user's access level instance.",
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(analysis_id_kwarg="analysis_pk"),
        ]
    )
    def list(self, request, analysis_pk, views_pk=None):
        if int(analysis_pk) < 1:
            access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
            messages_queryset = AnalysisMessage.objects.filter(
                analysis__organization=self.get_organization(request),
                analysis__access_level_instance__lft__gte=access_level_instance.lft,
                analysis__access_level_instance__rgt__lte=access_level_instance.rgt,
            ).order_by("-id")
        elif views_pk is None:
            messages_queryset = AnalysisMessage.objects.filter(analysis=analysis_pk).order_by("-id")
        else:
            messages_queryset = AnalysisMessage.objects.filter(analysis=analysis_pk, analysis_property_view=views_pk).order_by("-id")

        return JsonResponse({"status": "success", "messages": AnalysisMessageSerializer(messages_queryset, many=True).data})

    @extend_schema(
        parameters=[AutoSchemaHelper.path_id_field("AnalysisMessage ID")],
        responses={200: AnalysisMessageRetrieveResponseSerializer},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(analysis_id_kwarg="analysis_pk"),
        ]
    )
    def retrieve(self, request, pk, analysis_pk, views_pk=None):
        try:
            if views_pk is None:
                message_queryset = AnalysisMessage.objects.get(id=pk, analysis=analysis_pk)
            else:
                message_queryset = AnalysisMessage.objects.get(id=pk, analysis=analysis_pk, analysis_property_view=views_pk)
        except AnalysisMessage.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Requested analysis message doesn't exist in this organization and/or analysis."},
                status=HTTP_409_CONFLICT,
            )

        return JsonResponse({"status": "success", "message": AnalysisMessageSerializer(message_queryset).data})

"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from rest_framework import status

from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.models import GoalNote
from seed.serializers.goal_notes import GoalNoteSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.goal_notes import get_permission_data
from seed.utils.viewsets import UpdateWithoutPatchModelMixin


class GoalNoteViewSet(UpdateWithoutPatchModelMixin, OrgMixin):
    # Update is the only necessary endpoint
    # Create is handled on Goal create through post_save signal
    # List and Retrieve are handled on a per property basis
    # Delete is handled through Goal or Property cascade deletes

    serializer_class = GoalNoteSerializer
    queryset = GoalNote.objects.all()

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_member")
    @has_hierarchy_access(property_id_kwarg="property_pk")  # should this be nested under the goal or properties router?
    def update(self, request, property_pk, pk):
        try:
            goal_note = GoalNote.objects.get(property=property_pk, pk=pk)
        except GoalNote.DoesNotExist:
            return JsonResponse({"status": "error", "errors": "No such resource."}, status=status.HTTP_404_NOT_FOUND)

        data = get_permission_data(request.data, request.access_level_instance_id)
        serializer = GoalNoteSerializer(goal_note, data=data, partial=True)

        if not serializer.is_valid():
            return JsonResponse(
                {
                    "status": "error",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()

        return JsonResponse(serializer.data)


"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status

from seed.lib.superperms.orgs.decorators import (
    has_hierarchy_access,
    has_perm_class
)
from seed.models import AccessLevelInstance, GoalNote
from seed.serializers.goal_notes import GoalNoteSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import ModelViewSetWithoutPatch


@method_decorator(
    name='retrieve',
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class('requires_viewer'),
        has_hierarchy_access(goal_id_kwarg='goal_pk')
    ]
)
@method_decorator(
    name='destroy',
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class('requires_member'),
        has_hierarchy_access(goal_id_kwarg="goal_pk")
    ]
)
@method_decorator(
    name='create',
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class('requires_member'),
        has_hierarchy_access(goal_id_kwarg="goal_pk")
    ]
)
class GoalNoteViewSet(ModelViewSetWithoutPatch, OrgMixin):
    serializer_class = GoalNoteSerializer
    queryset = GoalNote.objects.all()

    @swagger_auto_schema_org_query_param
    @has_perm_class('requires_viewer')
    def list(self, request, goal_pk):
        """ 
        IS THIS ENDPOINT NECESSAY?
        when would I need to access all goalnotes for a single goal?
        notes are on a property by property basis
        Id rather get the notes when I get the properties with select-related
        """
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        organization = access_level_instance.organization

        goal_notes = GoalNote.objects.filter(
            goal=goal_pk,
            goal__organization=organization.id,
            goal__access_level_instance__lft__gte=access_level_instance.lft,
            goal__access_level_instance__rgt__lte=access_level_instance.rgt
        )

        return JsonResponse({
            'status': 'success',
            'data': self.serializer_class(goal_notes, many=True).data
        })

    @swagger_auto_schema_org_query_param
    @has_perm_class('requires_member')
    @has_hierarchy_access(goal_id_kwarg='pk') # what are we doing here?
    def update(self, request, pk):
        try:
            goal_note = GoalNote.objects.get(pk=pk)
        except GoalNote.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'errors': "No such resource."
            })

        serializer = GoalNoteSerializer(goal_note, data=request.data, partial=True)

        if not serializer.is_valid():
            return JsonResponse({
                'status': 'error',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        return JsonResponse(serializer.data)
    
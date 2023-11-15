"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.http import JsonResponse
from rest_framework import status, viewsets

from seed.lib.superperms.orgs.decorators import (
    has_hierarchy_access,
    has_perm_class
)
from seed.models import Goal, AccessLevelInstance
from seed.serializers.goals import GoalSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param


class GoalViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = GoalSerializer

    @swagger_auto_schema_org_query_param
    @has_perm_class('requires_viewer')
    def list(self, request):
        organization_id = self.get_organization(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)

        goals = Goal.objects.filter(
            organization=organization_id,
            access_level_instance__lft__gte=access_level_instance.lft,
            access_level_instance__rgt__lte=access_level_instance.rgt
        )

        return JsonResponse({
            'status': 'success',
            'goals': self.serializer_class(goals, many=True).data 
        })
    
    @swagger_auto_schema_org_query_param
    @has_perm_class('requires_viewer')
    def retrieve(self, request, pk):
        organization_id = self.get_organization(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        ali = access_level_instance

        try:
            goal = Goal.objects.get(
                organization=organization_id,
                pk=pk,
                access_level_instance__lft__gte=access_level_instance.lft,
                access_level_instance__rgt__lte=access_level_instance.rgt
            )
            return JsonResponse({
                'status': 'success',
                'goal': self.serializer_class(goal).data
            })
        except Goal.DoesNotExist:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': 'No such resource.'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        

    # @has_hierarchy_access(property_id_kwarg="property_pk")

    # def create(self)

    # def retreive(self)
        
    # def delete(self)
        
    # def update(self)
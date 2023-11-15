"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.http import JsonResponse
from rest_framework import status, viewsets
from django.utils.decorators import method_decorator

from seed.lib.superperms.orgs.decorators import (
    has_hierarchy_access,
    has_perm_class
)
from seed.models import Goal, AccessLevelInstance
from seed.serializers.goals import GoalSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import ModelViewSetWithoutPatch


@method_decorator(
    name='destroy',
    decorator=[has_perm_class('requires_member'), has_hierarchy_access(goal_id_kwarg="pk")]
)
class GoalViewSet(ModelViewSetWithoutPatch, OrgMixin):
    serializer_class = GoalSerializer
    queryset = Goal.objects.all()


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
    @has_hierarchy_access(goal_id_kwarg='pk')
    def retrieve(self, request, pk):
        organization_id = self.get_organization(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        ali = access_level_instance

        goal = Goal.objects.get(
            organization=organization_id,
            pk=pk,
        )
        return JsonResponse({
            'status': 'success',
            'goal': self.serializer_class(goal).data
        })
    
    # @swagger_auto_schema_org_query_param
    # @has_perm_class('required_member')
    # @has_hierarchy_access(goal_id_kwarg='pk')
    # def destroy(self, request, pk):
        
        

        

    # @has_hierarchy_access(property_id_kwarg='property_pk')

    # def create(self)

    # def retreive(self)
        
    # def delete(self)
        
    # def update(self)
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets
from rest_framework.decorators import action
from django.db.models import F, Sum
from django.db.models.functions import Coalesce

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import (
    has_hierarchy_access,
    has_perm_class
)
from seed.models import AccessLevelInstance, Column, Cycle, Goal, PropertyView
from seed.serializers.goals import GoalSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import ModelViewSetWithoutPatch


@method_decorator(
    name='retrieve',
    decorator=[has_perm_class('requires_viewer'), has_hierarchy_access(goal_id_kwarg='pk')]
)
@method_decorator(
    name='destroy',
    decorator=[has_perm_class('requires_member'), has_hierarchy_access(goal_id_kwarg="pk")]
)
@method_decorator(
    name='create',
    decorator=[has_perm_class('requires_member'), has_hierarchy_access(body_ali_id="access_level_instance")]
)
class GoalViewSet(ModelViewSetWithoutPatch, OrgMixin):
    serializer_class = GoalSerializer
    queryset = Goal.objects.all()


    @swagger_auto_schema_org_query_param
    @has_perm_class('requires_viewer')
    def list(self, request):
        organization_id = self.get_organization(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)

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
    @has_perm_class('requires_member')
    @has_hierarchy_access(goal_id_kwarg='pk')
    def update(self, request, pk):
        try:
            goal = Goal.objects.get(pk=pk)
        except Goal.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'error': "No such resource."
            })

        serializer = GoalSerializer(goal, data=request.data, partial=True)

        if not serializer.is_valid():
            return JsonResponse({
                'status': 'error',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
    
        serializer.save()

        return JsonResponse(serializer.data)

    @ajax_request_class
    @has_perm_class('requires_viewer')
    @has_hierarchy_access(goal_id_kwarg='pk')
    @action(detail=True, methods=['GET'])
    def portfolio_summary(self, request, pk):
        """
        Gets a Portfolio Summary dictionary given a goal
        """
        org_id = int(self.get_organization(request))
        goal = Goal.objects.get(pk=pk)
        column_names = goal.column_names()
        preferred_fields = [F(f'state__{name}') for name in column_names]
        summary = {}

        for cycle in [goal.baseline_cycle, goal.current_cycle]:
            # calcualte total_sqft, total_kbtu, and weighted_eui from property_views
            property_views = PropertyView.objects.select_related('property', 'state') \
                .filter(
                    property__organization_id=org_id,
                    cycle_id=cycle.id,
                    property__access_level_instance__lft__gte=goal.access_level_instance.lft,
                    property__access_level_instance__rgt__lte=goal.access_level_instance.rgt,
            )
            
            aggregated_data = property_views.aggregate(
                total_sqft=Sum('state__gross_floor_area'),
                total_kbtu=Sum(
                    Coalesce(*preferred_fields) * F('state__gross_floor_area')
                )
            )

            def get_magnitude(key):
                value = aggregated_data.get(key, 0)
                return int(value.m) if value else 0
        
            total_sqft = get_magnitude('total_sqft')
            total_kbtu = get_magnitude('total_kbtu')
            weighted_eui = int(total_kbtu / total_sqft) if total_sqft else 0

            cycle_type = 'current' if cycle == goal.current_cycle else 'baseline'

            summary[cycle_type] = {
                'cycle_name': cycle.name,
                'total_sqft': total_sqft,
                'total_kbtu': total_kbtu,
                'weighted_eui': weighted_eui
            }
    
        def percentage(a,b):
            return int((a - b) / a * 100) if a != 0 else 0
        
        summary['sqft_change'] = percentage(summary['current']['total_sqft'], summary['baseline']['total_sqft'])
        summary['eui_change'] = percentage(summary['baseline']['weighted_eui'], summary['current']['weighted_eui'])

        return summary
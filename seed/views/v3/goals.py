"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db.models import ExpressionWrapper, F, IntegerField, Sum
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import (
    has_hierarchy_access,
    has_perm_class
)
from seed.models import AccessLevelInstance, Goal, PropertyView
from seed.serializers.goals import GoalSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.goals import get_eui_expression
from seed.utils.viewsets import ModelViewSetWithoutPatch


@method_decorator(
    name='retrieve',
    decorator=[
        swagger_auto_schema_org_query_param, 
        has_perm_class('requires_viewer'), 
        has_hierarchy_access(goal_id_kwarg='pk')
    ]
)
@method_decorator(
    name='destroy',
    decorator=[
        swagger_auto_schema_org_query_param, 
        has_perm_class('requires_member'), 
        has_hierarchy_access(goal_id_kwarg="pk")
    ]
)
@method_decorator(
    name='create',
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class('requires_member'), 
        has_hierarchy_access(body_ali_id="access_level_instance")
        ]
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
                'errors': "No such resource."
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
    @swagger_auto_schema_org_query_param
    @has_perm_class('requires_viewer')
    @has_hierarchy_access(goal_id_kwarg='pk')
    @action(detail=True, methods=['GET'])
    def portfolio_summary(self, request, pk):
        """
        Gets a Portfolio Summary dictionary given a goal
        """
        org_id = int(self.get_organization(request))
        goal = Goal.objects.get(pk=pk)
        summary = {}
        for cycle in [goal.baseline_cycle, goal.current_cycle]:
            property_views = PropertyView.objects.select_related('property', 'state') \
                .filter(
                    property__organization_id=org_id,
                    cycle_id=cycle.id,
                    property__access_level_instance__lft__gte=goal.access_level_instance.lft,
                    property__access_level_instance__rgt__lte=goal.access_level_instance.rgt,
            )

            # Create annotations for kbtu calcs. 'eui' is based on goal column priority
            property_views = property_views.annotate(
                eui=get_eui_expression(goal),
                sqft=ExpressionWrapper(F('state__gross_floor_area'), output_field=IntegerField()),
            ).annotate(
                kbtu=F('eui') * F('sqft')
            )

            aggregated_data = property_views.aggregate(
                total_kbtu=Sum('kbtu'),
                total_sqft=Sum('sqft')
            )

            weighted_eui = int(aggregated_data['total_kbtu'] / aggregated_data['total_sqft']) if aggregated_data['total_sqft'] else None

            cycle_type = 'current' if cycle == goal.current_cycle else 'baseline'

            summary[cycle_type] = {
                'cycle_name': cycle.name,
                'total_sqft': aggregated_data['total_sqft'],
                'total_kbtu': aggregated_data['total_kbtu'],
                'weighted_eui': weighted_eui
            }

        def percentage(a, b):
            if not a or not b:
                return None
            return int((a - b) / a * 100) or 0

        summary['sqft_change'] = percentage(summary['current']['total_sqft'], summary['baseline']['total_sqft'])
        summary['eui_change'] = percentage(summary['baseline']['weighted_eui'], summary['current']['weighted_eui'])

        return summary

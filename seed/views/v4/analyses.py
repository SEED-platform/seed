
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import Analysis, Column, Cycle, PropertyView, PropertyState, AccessLevelInstance
from seed.serializers.analyses import AnalysisSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.models.columns import EXCLUDED_API_FIELDS


class AnalysisViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = AnalysisSerializer
    model = Analysis

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    @action(detail=False, methods=["GET"])
    def stats(self, request):
        """ Get all property and taxlot columns that have data in them for an org """
        org_id = self.get_organization(request)
        cycle_id = request.query_params.get("cycle_id")

        if not cycle_id:
            return JsonResponse({"success": False, "message": "cycle_id parameter is missing"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            Cycle.objects.get(id=cycle_id, organization_id=org_id)
        except Cycle.DoesNotExist:
            return JsonResponse({"success": False, "message": "Cycle does not exist"}, status=status.HTTP_404_NOT_FOUND)

        access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        state_ids = PropertyView.objects.filter(
            property__organization_id=org_id,
            cycle_id=cycle_id,
            property__access_level_instance__lft__gte=access_level_instance.lft,
            property__access_level_instance__rgt__lte=access_level_instance.rgt,
        ).values_list("state_id", flat=True)

        if not state_ids:
            return JsonResponse({"success": False, "message": "No properties found for the given cycle"}, status=status.HTTP_404_NOT_FOUND)

        columns = (
            Column.objects.filter(organization_id=org_id, derived_column=None, table_name="PropertyState")
            .exclude(column_name__in=EXCLUDED_API_FIELDS)
            .only("column_name", "display_name", "is_extra_data")
        )

        extra_data_columns = [c.column_name for c in columns if c.is_extra_data]
        stats = []
        num_of_nonnulls_by_column_name = Column.get_num_of_nonnulls_by_column_name(state_ids, PropertyState, columns)

        for column in columns:
            stat = {
                "column_name": column.column_name,
                "display_name": column.display_name,
                "is_extra_data": column.is_extra_data,
                "count": num_of_nonnulls_by_column_name.get(column.column_name, 0),
            }
            stats.append(stat)    

        return JsonResponse(
            {
                "status": "success",
                "total_records": len(state_ids),
                "number_extra_data_fields": len(extra_data_columns),
                "stats": stats,
            }
        )

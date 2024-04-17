# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from rest_framework import status, viewsets

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import TaxLotView
from seed.serializers.taxlots import BriefTaxlotViewSerializer
from seed.utils.api import OrgMixin, ProfileIdMixin, api_endpoint_class


class TaxlotViewViewSet(viewsets.ViewSet, OrgMixin, ProfileIdMixin):
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    def list(self, request):
        """
        List all the taxlots
        """
        org_id = request.query_params.get("organization_id")
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)

        if not org_id:
            return JsonResponse(
                {"status": "error", "message": "Need to pass organization_id as query parameter"}, status=status.HTTP_400_BAD_REQUEST
            )

        views = TaxLotView.objects.filter(
            taxlot__organization_id=org_id,
            taxlot__access_level_instance__lft__gte=access_level_instance.lft,
            taxlot__access_level_instance__rgt__lte=access_level_instance.rgt,
        )

        taxlot = request.query_params.get("taxlot")
        if taxlot is not None:
            views = views.filter(taxlot_id=taxlot)

        return {"status": "success", "taxlot_views": [BriefTaxlotViewSerializer(view).data for view in views]}

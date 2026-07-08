"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import Analysis
from seed.serializers.analyses import AnalysisSerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.views.v4.property import build_property_stats_response


class AnalysisViewSet(viewsets.ViewSet, OrgMixin):
    """
    Compatibility namespace for v4 analyses routes.

    The `stats` action is inventory/property-view based rather than analysis-run based.
    Canonical placement is `properties-stats`; this endpoint is kept so
    existing clients using `analyses-stats` continue to work.
    """

    serializer_class = AnalysisSerializer
    model = Analysis

    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=False, methods=["GET"])
    def stats(self, request):
        return build_property_stats_response(
            request=request,
            org_id=self.get_organization(request),
            access_level_instance_id=self.request.access_level_instance_id,
        )

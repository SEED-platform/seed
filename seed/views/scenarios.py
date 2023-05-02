# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.models import Scenario
from seed.serializers.scenarios import ScenarioSerializer
from seed.utils.viewsets import SEEDOrgReadOnlyModelViewSet


class ScenarioViewSet(SEEDOrgReadOnlyModelViewSet):
    """
    API View for Scenarios. This only includes retrieve and list for now.
    """
    serializer_class = ScenarioSerializer
    parser_classes = (JSONParser, FormParser,)
    renderer_classes = (JSONRenderer,)
    queryset = Scenario.objects.all()
    pagination_class = None
    orgfilter = 'property_state__organization_id'

    def get_queryset(self):
        org_id = self.get_organization(self.request)
        return Scenario.objects.filter(property_state__organization_id=org_id).order_by('id')

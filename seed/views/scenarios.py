# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer

from seed.models import (
    Scenario,
)
from seed.serializers.scenarios import ScenarioSerializer
from seed.utils.viewsets import (
    SEEDOrgReadOnlyModelViewSet
)


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

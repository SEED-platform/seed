# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.utils.decorators import method_decorator

from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer

from seed.models import (
    Scenario,
)
from seed.serializers.scenarios import ScenarioSerializer
from seed.utils.viewsets import (
    SEEDOrgReadOnlyModelViewSet
)
from seed.utils.api_schema import swagger_auto_schema_org_query_param


@method_decorator(name='list', decorator=swagger_auto_schema_org_query_param)
@method_decorator(name='retrieve', decorator=swagger_auto_schema_org_query_param)
class PropertyScenarioViewSet(SEEDOrgReadOnlyModelViewSet):
    """
    API View for Scenarios. This only includes retrieve and list for now.
    """
    serializer_class = ScenarioSerializer
    parser_classes = (JSONParser, FormParser,)
    renderer_classes = (JSONRenderer,)
    pagination_class = None
    orgfilter = 'property_state__organization_id'

    def get_queryset(self):
        # Authorization is partially implicit in that users can't try to query
        # on an org_id for an Organization that they are not a member of.
        org_id = self.get_organization(self.request)
        property_view_id = self.kwargs.get('property_pk')

        return Scenario.objects.filter(
            property_state__organization_id=org_id,
            property_state__propertyview=property_view_id,
        ).order_by('id')

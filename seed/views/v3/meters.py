# !/usr/bin/env python
# encoding: utf-8

from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.models import Meter
from seed.serializers.meters import MeterSerializer
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


class MeterViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """API endpoint for managing meters."""

    serializer_class = MeterSerializer
    renderer_classes = (JSONRenderer,)
    pagination_class = None
    model = Meter
    parser_classes = (JSONParser, FormParser)
    orgfilter = 'property__organization'

    def get_queryset(self):
        # get all the meters for the organization
        org_id = self.get_organization(self.request)
        return Meter.objects.filter(property__organization_id=org_id, property_id=self.kwargs.get('property_pk'))

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from django.utils.decorators import method_decorator
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.models import PropertyMeasure
from seed.serializers.scenarios import PropertyMeasureSerializer
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgModelViewSet



@method_decorator(name='list', decorator=swagger_auto_schema_org_query_param)
@method_decorator(name='retrieve', decorator=swagger_auto_schema_org_query_param)
@method_decorator(name='destroy', decorator=swagger_auto_schema_org_query_param)
class PropertyMeasureViewSet(SEEDOrgModelViewSet):
    """
    API view for PropertyMeasures
    """
    serializer_class = PropertyMeasureSerializer   
    model = PropertyMeasure 
    parser_classes = (JSONParser, FormParser,)
    renderer_classes = (JSONRenderer,)
    pagination_class = None
    orgfilter = 'property_state__organization_id'

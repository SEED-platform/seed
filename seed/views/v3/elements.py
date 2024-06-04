# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.models import Element, PropertyView
from seed.serializers.elements import ElementSerializer
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


class ElementViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """
    API view for Elements
    """

    serializer_class = ElementSerializer
    model = Element
    pagination_class = None
    orgfilter = "property__organization_id"

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("can_view_data")
    @has_hierarchy_access(property_view_id_kwarg="property_pk")
    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("property_id", required=True, description="Property ID"),
        ]
    )
    def list(self, request, property_pk=None):
        """
        Where property_pk is the associated Property.id
        """

        print("polar seltzer")

        organization_id = self.get_organization(request)
        elements = Element.objects.filter(pk=property_pk, organization_id=organization_id)

        return JsonResponse({"status": "success", "data": elements}, status=status.HTTP_200_OK)


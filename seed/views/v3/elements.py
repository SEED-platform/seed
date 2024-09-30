"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer
from tkbl import bsync_by_uniformat_code, federal_bps_by_uniformat_code, filter_by_uniformat_code

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.lib.tkbl.tkbl import SCOPE_ONE_EMISSION_CODES
from seed.lib.uniformat.uniformat import uniformat_codes
from seed.models import Element, Uniformat
from seed.serializers.elements import ElementPropertySerializer, ElementSerializer
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet, SEEDOrgReadOnlyModelViewSet


@method_decorator(
    name="list",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_viewer"),
    ],
)
@method_decorator(
    name="retrieve",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_viewer"),
    ],
)
class OrgElementViewSet(SEEDOrgReadOnlyModelViewSet):
    """
    API view for all Elements within an organization
    """

    lookup_field = "element_id"
    model = Element
    renderer_classes = (JSONRenderer,)
    serializer_class = ElementSerializer

    def get_queryset(self):
        if hasattr(self.request, "access_level_instance_id"):
            element_fields = [field.name for field in Element._meta.get_fields()]

            access_level_instance = AccessLevelInstance.objects.only("lft", "rgt").get(pk=self.request.access_level_instance_id)
            return (
                self.model.objects.filter(
                    organization_id=self.get_organization(self.request),
                    property__access_level_instance__lft__gte=access_level_instance.lft,
                    property__access_level_instance__rgt__lte=access_level_instance.rgt,
                )
                .select_related("code")
                .only(*element_fields, "code__code")
            )
        return self.model.objects.none()

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_enum_field(name="code", description=Uniformat._meta.get_field("code").help_text, enum=uniformat_codes),
        ],
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    @action(detail=False, methods=["GET"])
    def filter(self, request):
        """
        Filter all Properties within an organization that have Elements under a specific Uniformat code
        """
        code = request.query_params.get("code")
        if code not in uniformat_codes:
            return JsonResponse({"status": "error", "message": f"Invalid Uniformat code '{code}'"}, status=status.HTTP_400_BAD_REQUEST)

        elements = self.get_queryset().filter(code__code__startswith=code)
        page = self.paginator.paginate_queryset(elements, request)

        return self.paginator.get_paginated_response(self.serializer_class(page, many=True).data)


@method_decorator(
    name="list",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_viewer"),
        has_hierarchy_access(property_id_kwarg="property_pk"),
    ],
)
@method_decorator(
    name="retrieve",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_viewer"),
        has_hierarchy_access(property_id_kwarg="property_pk"),
    ],
)
@method_decorator(
    name="create",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_member"),
        has_hierarchy_access(property_id_kwarg="property_pk"),
    ],
)
@method_decorator(
    name="update",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_member"),
        has_hierarchy_access(property_id_kwarg="property_pk"),
    ],
)
@method_decorator(
    name="destroy",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_member"),
        has_hierarchy_access(property_id_kwarg="property_pk"),
    ],
)
class ElementViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """
    API view for Elements belonging to a Property
    """

    lookup_field = "element_id"
    model = Element
    pagination_class = None
    renderer_classes = (JSONRenderer,)
    serializer_class = ElementPropertySerializer

    def get_queryset(self):
        return self.model.objects.filter(
            organization_id=self.get_organization(self.request),
            property_id=self.kwargs.get("property_pk"),
        ).select_related("code")

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, args, kwargs)
        except IntegrityError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={
            200: AutoSchemaHelper.schema_factory(
                [
                    {
                        "code": "string",
                        "remaining_service_life": "number",
                        "description": "string",
                        "tkbl": {
                            "sftool": [
                                {
                                    "category": "string",
                                    "subcategory": "string",
                                    "uniformat code": "string",
                                    "uniformat description": "string",
                                    "url": "string",
                                    "title": "string",
                                }
                            ],
                            "estcp": [
                                {
                                    "category": "string",
                                    "subcategory": "string",
                                    "uniformat code": "string",
                                    "uniformat description": "string",
                                    "url": "string",
                                    "title": "string",
                                }
                            ],
                            "bsync_measures": ["string"],
                            "federal_bps_measures": ["string"],
                        },
                    }
                ]
            )
        },
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(property_id_kwarg="property_pk")
    @action(detail=False, methods=["GET"])
    def tkbl(self, request, *args, **kwargs):
        """
        Technologies Knowledge Base Library recommendations for Elements belonging to a Property with the lowest remaining service life
        """

        tkbl_elements = self.get_queryset().filter(code__code__in=SCOPE_ONE_EMISSION_CODES).order_by("remaining_service_life")[:3]

        results = []
        for e in tkbl_elements:
            links = json.loads(filter_by_uniformat_code(e.code.code))
            sftool_links = [link for link in links if link["category"] != "ESTCP"]
            estcp_links = [link for link in links if link["category"] == "ESTCP"]
            bsync = [x["eem_name"] for x in bsync_by_uniformat_code(e.code.code)]
            federal_bps = [x["Federal BPS Prescriptive Measures"] for x in federal_bps_by_uniformat_code(e.code.code)]
            results.append(
                {
                    "code": e.code.code,
                    "remaining_service_life": e.remaining_service_life,
                    "description": e.description,
                    "tkbl": {"sftool": sftool_links, "estcp": estcp_links, "bsync_measures": bsync, "federal_bps_measures": federal_bps},
                }
            )

        return results

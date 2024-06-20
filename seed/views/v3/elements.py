# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status

from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import Element
from seed.serializers.elements import ElementPropertySerializer, ElementSerializer
from seed.utils.api_schema import swagger_auto_schema_org_query_param
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
    serializer_class = ElementSerializer

    def get_queryset(self):
        if hasattr(self.request, "access_level_instance_id"):
            access_level_instance = AccessLevelInstance.objects.only("lft", "rgt").get(pk=self.request.access_level_instance_id)
            return self.model.objects.filter(
                organization_id=self.get_organization(self.request),
                property__access_level_instance__lft__gte=access_level_instance.lft,
                property__access_level_instance__rgt__lte=access_level_instance.rgt,
            )
        return self.model.objects.none()


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
    serializer_class = ElementPropertySerializer

    def get_queryset(self):
        return self.model.objects.filter(
            organization_id=self.get_organization(self.request),
            property_id=self.kwargs.get("property_pk"),
        )

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request)
        except IntegrityError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

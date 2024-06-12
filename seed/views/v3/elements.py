# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.utils.decorators import method_decorator

from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import Element
from seed.serializers.elements import ElementSerializer
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
            access_level_instance = AccessLevelInstance.objects.only('lft', 'rgt').get(pk=self.request.access_level_instance_id)
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
        # swagger_auto_schema(
        #     manual_parameters=[
        #         AutoSchemaHelper.base_field(
        #             name="property_pk",
        #             location_attr="IN_PATH",
        #             type_attr="TYPE_INTEGER",
        #             required=True,
        #             description="ID of the property view where the meter is associated.",
        #         ),
        #     ],
        #     request_body=AutoSchemaHelper.schema_factory(
        #         {
        #             "type": Meter.ENERGY_TYPES,
        #             "alias": "string",
        #             "source": Meter.SOURCES,
        #             "source_id": "string",
        #             "scenario_id": "integer",
        #             "is_virtual": "boolean",
        #         },
        #         required=["type", "source"],
        #         description="New meter to add. The type must be taken from a constrained list.",
        #     ),
        # ),
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
    orgfilter = "property__organization"
    pagination_class = None
    serializer_class = ElementSerializer

    def get_queryset(self):
        return self.model.objects.filter(
            organization_id=self.get_organization(self.request),
            property_id=self.kwargs.get("property_pk"),
        )

    # def perform_create(self, serializer):
    #     org_id = self.get_organization(self.request)
    #     if self.kwargs.get("property_pk", None):
    #         property = Property.objects.get(pk=self.kwargs.get("property_pk"), organization_id=org_id)
    #         Element.objects.create(property=property)

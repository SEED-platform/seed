"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import Meter, PropertyView, Service
from seed.serializers.meters import MeterSerializer
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.meters import update_meter_connection
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


@extend_schema_view(
    create=extend_schema(
        request=AutoSchemaHelper.json_body(
            {
                "type": Meter.ENERGY_TYPES,
                "connection_type": ((Meter.IMPORTED, "Imported"), (Meter.EXPORTED, "Exported")),
                "alias": "string",
                "source": Meter.SOURCES,
                "source_id": "string",
                "scenario_id": "integer",
                "is_virtual": "boolean",
            },
            required=["type", "connection_type", "source"],
            description="New meter to add. The type must be taken from a constrained list.",
        ),
    ),
    update=extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "alias": {"type": "string"},
                    # `update_meter_connection` requires the direction whenever a connection_config is provided
                    "connection_config": AutoSchemaHelper.schema_factory(
                        {
                            "direction": (("imported", "imported"), ("exported", "exported")),
                            "use": (("outside", "outside"), ("using", "using"), ("offering", "offering")),
                            "service_id": "integer",
                        },
                        required=["direction"],
                    ),
                },
                "description": "Only the provided alias and/or connection configuration are updated.",
            }
        },
    ),
)
@extend_schema(
    parameters=[
        AutoSchemaHelper.query_org_id_field(),
        AutoSchemaHelper.path_id_field("ID of the property view where the meter is associated.", name="property_pk"),
    ]
)
@method_decorator(
    [
        has_perm("requires_viewer"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
    name="list",
)
@method_decorator(
    [
        has_perm("requires_viewer"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
    name="retrieve",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
    name="create",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
    name="update",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
    name="destroy",
)
class MeterViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """API endpoint for managing meters."""

    serializer_class = MeterSerializer
    renderer_classes = (JSONRenderer,)
    pagination_class = None
    model = Meter
    parser_classes = (JSONParser, FormParser)
    orgfilter = "property__organization"

    def get_queryset(self):
        # get all the meters for the organization
        org_id = self.get_organization(self.request)
        # get the property id - since the meter is associated with the property (not the property view)

        # even though it is named 'property_pk' it is really the property view id
        property_view_pk = self.kwargs.get("property_pk", None)
        if not property_view_pk:
            # Return None otherwise swagger will not be able to process the request
            return Meter.objects.none()

        try:
            property_view = PropertyView.objects.get(pk=property_view_pk)
        except PropertyView.DoesNotExist:
            return Meter.objects.none()

        self.property_pk = property_view.property_id
        return Meter.objects.filter(property__organization_id=org_id, property_id=self.property_pk)

    def perform_create(self, serializer):
        """On create, make sure to add in the property id which comes from the URL kwargs."""

        # check permissions?
        if self.property_pk:
            serializer.save(property_id=self.property_pk)
        else:
            raise ValueError("No property_pk (property view id) provided in URL to create the meter")

    @method_decorator(
        [
            has_perm("can_modify_data"),
            has_hierarchy_access(property_view_id_kwarg="property_pk"),
        ]
    )
    def update(self, request, property_pk, pk):
        meter = self.get_queryset().filter(pk=pk).first()
        if meter is None:
            return JsonResponse({"status": "error", "message": "No such resource."}, status=status.HTTP_404_NOT_FOUND)
        alias = request.data.get("alias")
        connection_config = request.data.get("connection_config")

        try:
            if alias:
                meter.alias = alias
                meter.save()
            if connection_config:
                update_meter_connection(meter, connection_config)
        except IntegrityError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Service.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such service."}, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse(MeterSerializer(meter).data, status=status.HTTP_200_OK)

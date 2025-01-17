"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import Meter, PropertyView
from seed.serializers.meters import MeterSerializer
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param
from seed.utils.meters import update_meter_connection
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


@method_decorator(
    [
        swagger_auto_schema_org_query_param,
        has_perm("requires_viewer"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
    name="list",
)
@method_decorator(
    [
        swagger_auto_schema_org_query_param,
        has_perm("requires_viewer"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
    name="retrieve",
)
@method_decorator(
    [
        swagger_auto_schema(
            manual_parameters=[
                AutoSchemaHelper.query_org_id_field(),
                AutoSchemaHelper.base_field(
                    name="property_pk",
                    location_attr="IN_PATH",
                    type_attr="TYPE_INTEGER",
                    required=True,
                    description="ID of the property view where the meter is associated.",
                ),
            ],
            request_body=AutoSchemaHelper.schema_factory(
                {
                    "type": Meter.ENERGY_TYPES,
                    "alias": "string",
                    "source": Meter.SOURCES,
                    "source_id": "string",
                    "scenario_id": "integer",
                    "is_virtual": "boolean",
                },
                required=["type", "source"],
                description="New meter to add. The type must be taken from a constrained list.",
            ),
        ),
        has_perm("requires_member"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
    name="create",
)
@method_decorator(
    [
        swagger_auto_schema_org_query_param,
        has_perm("requires_member"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
    name="update",
)
@method_decorator(
    [
        swagger_auto_schema_org_query_param,
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

        property_view = PropertyView.objects.get(pk=property_view_pk)
        self.property_pk = property_view.property_id
        return Meter.objects.filter(property__organization_id=org_id, property_id=self.property_pk)

    def perform_create(self, serializer):
        """On create, make sure to add in the property id which comes from the URL kwargs."""

        # check permissions?
        if self.property_pk:
            serializer.save(property_id=self.property_pk)
        else:
            raise Exception("No property_pk (property view id) provided in URL to create the meter")

    @method_decorator(
        [
            has_perm("can_modify_data"),
            has_hierarchy_access(property_view_id_kwarg="property_pk"),
        ]
    )
    @action(detail=True, methods=["PUT"])
    def update_connection(self, request, property_pk, pk):
        meter = self.get_queryset().filter(pk=pk).first()
        meter_config = request.data.get("meter_config")
        try:
            update_meter_connection(meter, meter_config)
        except IntegrityError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse({}, status=status.HTTP_200_OK)

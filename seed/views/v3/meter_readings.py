# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import FormParser, JSONParser

from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.models import MeterReading, PropertyView
from seed.serializers.meter_readings import MeterReadingSerializer
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


@method_decorator(
    name="list",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_viewer"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
)
@method_decorator(
    name="retrieve",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_viewer"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
)
@method_decorator(
    name="create",
    decorator=[
        has_perm_class("requires_member"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
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
                AutoSchemaHelper.base_field(
                    name="meter_pk",
                    location_attr="IN_PATH",
                    type_attr="TYPE_INTEGER",
                    required=True,
                    description="ID of the meter to attached the meter readings.",
                ),
            ],
            request_body=openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=AutoSchemaHelper.schema_factory(
                    {
                        "start_time": "datetime",
                        "end_time": "datetime",
                        "reading": "number",
                        "source_unit": "string",
                        "conversion_factor": "number",
                    },
                    required=["start_time", "end_time", "reading", "source_unit", "conversion_factor"],
                ),
                description="Dictionary or list of dictionaries of meter readings to add.",
            ),
        ),
    ],
)
@method_decorator(
    name="update",
    decorator=[
        has_perm_class("requires_member"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
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
                AutoSchemaHelper.base_field(
                    name="meter_pk",
                    location_attr="IN_PATH",
                    type_attr="TYPE_INTEGER",
                    required=True,
                    description="ID of the meter to attached the meter readings.",
                ),
            ],
            request_body=AutoSchemaHelper.schema_factory(
                {
                    "start_time": "datetime",
                    "end_time": "datetime",
                    "reading": "number",
                    "source_unit": "string",
                    "conversion_factor": "number",
                },
                required=["start_time", "end_time", "reading", "source_unit", "conversion_factor"],
            ),
            description="Meter reading to update.",
        ),
    ],
)
@method_decorator(
    name="destroy",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_member"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
)
class MeterReadingViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """API endpoint for managing meters."""

    serializer_class = MeterReadingSerializer
    pagination_class = None
    model = MeterReading
    parser_classes = (JSONParser, FormParser)

    def get_queryset(self):
        # return the organization id from the request. This also check
        # the permissions for the user
        org_id = self.get_organization(self.request)
        # get the property id - since the meter is associated with the property (not the property view)

        # even though it is named 'property_pk' it is really the property view id
        property_view_pk = self.kwargs.get("property_pk", None)
        if not property_view_pk:
            # Return None otherwise swagger will not be able to process the request
            return MeterReading.objects.none()

        try:
            property_view = PropertyView.objects.get(pk=property_view_pk)
        except PropertyView.DoesNotExist:
            return MeterReading.objects.none()

        self.property_pk = property_view.property_id

        # Grab the meter id
        meter_pk = self.kwargs.get("meter_pk", None)
        if not meter_pk:
            # Return None otherwise swagger will not be able to process the request
            return MeterReading.objects.none()
        self.meter_pk = meter_pk

        return MeterReading.objects.filter(
            meter__property__organization_id=org_id, meter__property=self.property_pk, meter_id=meter_pk
        ).order_by("start_time", "end_time")

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get("data", {}), list):
            kwargs["many"] = True

        return super().get_serializer(*args, **kwargs)

    def perform_create(self, serializer):
        """On create, make sure to add in the property id which comes from the URL kwargs."""

        # check permissions?
        if self.meter_pk:
            serializer.save(meter_id=self.meter_pk)
        else:
            raise Exception("No meter_pk provided in URL to create the meter reading")

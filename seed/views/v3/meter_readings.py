"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import Meter, MeterReading, PropertyView
from seed.serializers.meter_readings import MeterReadingSerializer
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

DETAIL_PARAMETERS = [
    AutoSchemaHelper.path_string_field("id", "Start time of the reading (its ID), e.g., 2024-01-01T00:00:00Z"),
    AutoSchemaHelper.query_string_field(
        "end_time",
        required=False,
        description="End time of the reading, required only when several of the meter's readings share the start_time in the URL.",
    ),
]
# Request timestamps are parsed as local times in SEED's default time zone, so time zone offsets are rejected
LOCAL_DATETIME_SCHEMA = {"type": "string", "example": "2024-01-01T00:00:00", "description": "ISO 8601 time without a time zone offset"}
METER_READING_REQUEST_FIELDS = {
    "start_time": LOCAL_DATETIME_SCHEMA,
    "end_time": LOCAL_DATETIME_SCHEMA,
    "reading": {"type": "number", "nullable": True},
    "source_unit": {"type": "string", "nullable": True},
    "conversion_factor": {"type": "number"},
}
METER_READING_REQUEST_SCHEMA = {
    "type": "object",
    "properties": METER_READING_REQUEST_FIELDS,
    "required": ["start_time", "end_time", "conversion_factor"],
}
# `MeterReadingSerializer.to_representation` adds the id and unit conversion fields
METER_READING_RESPONSE_SCHEMA = AutoSchemaHelper.schema_factory(
    {
        "id": "datetime",
        "start_time": "datetime",
        "end_time": "datetime",
        "reading": "number",
        "source_unit": "string",
        "conversion_factor": "number",
        "units": "string",
        "converted_value": "number",
        "converted_units": "string",
    }
)


@extend_schema_view(
    list=extend_schema(responses={200: METER_READING_RESPONSE_SCHEMA}),
    retrieve=extend_schema(parameters=DETAIL_PARAMETERS, responses={200: METER_READING_RESPONSE_SCHEMA}),
    create=extend_schema(
        request={
            "application/json": {
                "oneOf": [METER_READING_REQUEST_SCHEMA, {"type": "array", "items": METER_READING_REQUEST_SCHEMA}],
                "description": "Meter reading or list of meter readings to add (existing readings with the same start and end times are updated).",
            }
        },
        responses={
            201: OpenApiResponse(
                {"oneOf": [METER_READING_RESPONSE_SCHEMA, {"type": "array", "items": METER_READING_RESPONSE_SCHEMA}]},
                description="The added meter reading, or a list of them when a list was posted",
            )
        },
    ),
    update=extend_schema(
        parameters=DETAIL_PARAMETERS,
        request={
            "application/json": {
                "type": "object",
                "properties": METER_READING_REQUEST_FIELDS,
                "required": ["start_time", "end_time"],
                "description": "Meter reading to update.",
            }
        },
        responses={200: METER_READING_RESPONSE_SCHEMA},
    ),
    destroy=extend_schema(parameters=DETAIL_PARAMETERS),
)
@extend_schema(
    parameters=[
        AutoSchemaHelper.query_org_id_field(),
        AutoSchemaHelper.path_id_field("ID of the property view where the meter is associated.", name="property_pk"),
        AutoSchemaHelper.path_id_field("ID of the meter of the meter readings.", name="meter_pk"),
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
class MeterReadingViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """API endpoint for managing meter readings."""

    serializer_class = MeterReadingSerializer
    renderer_classes = (JSONRenderer,)
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

    def get_object(self):
        # The detail URL's pk is the reading's start_time, which is only unique within the meter together with end_time
        filters = {"start_time": self.kwargs["pk"]}
        if end_time := self.request.query_params.get("end_time"):
            filters["end_time"] = end_time

        try:
            readings = list(self.filter_queryset(self.get_queryset()).filter(**filters)[:2])
        except DjangoValidationError as e:
            raise NotFound() from e
        if not readings:
            raise NotFound()
        if len(readings) > 1:
            raise ValidationError(
                {
                    "status": "error",
                    "message": "Multiple readings start at this time, so specify which one with the end_time query parameter",
                }
            )

        self.check_object_permissions(self.request, readings[0])
        return readings[0]

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get("data", {}), list):
            kwargs["many"] = True

        return super().get_serializer(*args, **kwargs)

    def perform_create(self, serializer):
        """On create, make sure to add in the meter id which comes from the URL kwargs."""

        # has_hierarchy_access only checked the property view, so the meter must belong to its property
        if not Meter.objects.filter(pk=self.meter_pk, property_id=self.property_pk).exists():
            raise NotFound()
        serializer.save(meter_id=self.meter_pk)

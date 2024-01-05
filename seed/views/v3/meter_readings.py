# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db.utils import ProgrammingError
from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.models import MeterReading, PropertyView
from seed.serializers.meter_readings import MeterReadingSerializer
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import SEEDOrgModelViewSet


@method_decorator(
    name='create',
    decorator=swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.base_field(
                name='property_pk',
                location_attr='IN_PATH',
                type='TYPE_INTEGER',
                required=True,
                description='ID of the property view where the meter is associated.'),
            AutoSchemaHelper.base_field(
                name='meter_pk',
                location_attr='IN_PATH',
                type='TYPE_INTEGER',
                required=True,
                description='ID of the meter to attached the meter readings.'),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=AutoSchemaHelper.schema_factory(
                {
                    'start_time': 'string',
                    'end_time': 'string',
                    'reading': 'number',
                    'source_unit': 'string',
                    'conversion_factor': 'number'
                },
                required=['start_time', 'end_time', 'reading', 'source_unit', 'conversion_factor'],
            ),
            description='Dictionary or list of dictionaries of meter readings to add.'
        ),
    ),
)
class MeterReadingViewSet(SEEDOrgModelViewSet):
    """API endpoint for managing meters."""

    serializer_class = MeterReadingSerializer
    renderer_classes = (JSONRenderer,)
    pagination_class = None
    model = MeterReading
    parser_classes = (JSONParser, FormParser)
    orgfilter = 'property__organization'

    def get_queryset(self):
        # return the organization id from the request. This also check
        # the permissions for the user
        org_id = self.get_organization(self.request)
        # get the property id - since the meter is associated with the property (not the property view)

        # even though it is named 'property_pk' it is really the property view id
        property_view_pk = self.kwargs.get('property_pk', None)
        if not property_view_pk:
            # Return None otherwise swagger will not be able to process the request
            return MeterReading.objects.none()

        try:
            property_view = PropertyView.objects.get(pk=property_view_pk)
        except PropertyView.DoesNotExist:
            return MeterReading.objects.none()

        self.property_pk = property_view.property.pk

        # Grab the meter id
        meter_pk = self.kwargs.get('meter_pk', None)
        if not meter_pk:
            # Return None otherwise swagger will not be able to process the request
            return MeterReading.objects.none()
        self.meter_pk = meter_pk

        return MeterReading.objects.filter(
            meter__property__organization_id=org_id, meter__property=self.property_pk, meter_id=meter_pk
        ).order_by('start_time', 'end_time')

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get("data", {}), list):
            kwargs["many"] = True

        return super(MeterReadingViewSet, self).get_serializer(*args, **kwargs)

    def perform_create(self, serializer):
        """On create, make sure to add in the property id which comes from the URL kwargs."""

        # check permissions?
        if self.meter_pk is None:
            raise Exception('No meter_pk provided in URL to create the meter reading')

        try:
            serializer.save(meter_id=self.meter_pk)
        except ProgrammingError:
            raise serializers.ValidationError('No meter_pk provided in URL to create the meter reading')

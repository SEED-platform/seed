# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.models import MeterReading, PropertyView
from seed.serializers.meter_readings import MeterReadingSerializer
from seed.utils.viewsets import SEEDOrgModelViewSet


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
        )

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get("data", {}), list):
            kwargs["many"] = True

        return super(MeterReadingViewSet, self).get_serializer(*args, **kwargs)

    def perform_create(self, serializer):
        """On create, make sure to add in the property id which comes from the URL kwargs."""

        # check permissions?
        if self.meter_pk:
            serializer.save(meter_id=self.meter_pk)
        else:
            raise Exception('No meter_pk provided in URL to create the meter reading')

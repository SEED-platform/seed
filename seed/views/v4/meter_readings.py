"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import Meter, MeterReading
from seed.utils.api import OrgMixin, api_endpoint


class MeterReadingsViewSet(viewsets.ViewSet, OrgMixin):
    """V4 endpoint for retrieving per-meter readings."""

    model = MeterReading

    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    def list(self, request, meter_pk=None):
        """Return all readings for a specific meter."""
        org_id = self.get_organization(request)

        if not meter_pk:
            return JsonResponse(
                {"status": "error", "message": "meter_pk is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify the meter belongs to the organization
        try:
            meter = Meter.objects.get(pk=meter_pk)
        except Meter.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Meter not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check org ownership via property or system
        if meter.property and meter.property.organization_id != org_id:
            return JsonResponse(
                {"status": "error", "message": "Meter not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if meter.system and meter.system.group and meter.system.group.organization_id != org_id:
            return JsonResponse(
                {"status": "error", "message": "Meter not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        readings = MeterReading.objects.filter(meter=meter).order_by("start_time", "end_time")

        data = [
            {
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat(),
                "reading": r.reading,
                "source_unit": r.source_unit,
                "conversion_factor": r.conversion_factor,
            }
            for r in readings
        ]

        return JsonResponse({"status": "success", "data": data, "count": len(data)})

    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=False, methods=["GET"])
    def count(self, request, meter_pk=None):
        """Return the count of readings for a specific meter."""
        org_id = self.get_organization(request)

        if not meter_pk:
            return JsonResponse(
                {"status": "error", "message": "meter_pk is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            meter = Meter.objects.get(pk=meter_pk)
        except Meter.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Meter not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check org ownership
        if meter.property and meter.property.organization_id != org_id:
            return JsonResponse(
                {"status": "error", "message": "Meter not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if meter.system and meter.system.group and meter.system.group.organization_id != org_id:
            return JsonResponse(
                {"status": "error", "message": "Meter not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        count = MeterReading.objects.filter(meter=meter).count()

        return JsonResponse({"status": "success", "data": {"count": count}})

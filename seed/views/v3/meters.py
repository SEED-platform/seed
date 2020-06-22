# !/usr/bin/env python
# encoding: utf-8

from django.db.models import Q

from rest_framework import viewsets
from rest_framework.decorators import action

from seed.data_importer.utils import (
    kbtu_thermal_conversion_factors,
    usage_point_id,
)
from seed.decorators import ajax_request_class
from seed.models import (
    Meter,
    PropertyView,
)
from seed.utils.meters import PropertyMeterReadingsExporter


class MeterViewSet(viewsets.ViewSet):

    @ajax_request_class
    @action(detail=False, methods=['POST'])
    def property_meters(self, request):
        body = dict(request.data)
        property_view_id = body['property_view_id']
        property_view = PropertyView.objects.get(pk=property_view_id)
        property_id = property_view.property.id
        scenario_ids = [s.id for s in property_view.state.scenarios.all()]
        energy_types = dict(Meter.ENERGY_TYPES)

        res = []
        for meter in Meter.objects.filter(Q(property_id=property_id) | Q(scenario_id__in=scenario_ids)):
            if meter.source == meter.GREENBUTTON:
                source = 'GB'
                source_id = usage_point_id(meter.source_id)
            elif meter.source == meter.BUILDINGSYNC:
                source = 'BS'
                source_id = meter.source_id
            else:
                source = 'PM'
                source_id = meter.source_id

            res.append({
                'id': meter.id,
                'type': energy_types[meter.type],
                'source': source,
                'source_id': source_id,
                'scenario_id': meter.scenario.id if meter.scenario is not None else None,
                'scenario_name': meter.scenario.name if meter.scenario is not None else None
            })

        return res

    @ajax_request_class
    @action(detail=False, methods=['POST'])
    def property_meter_usage(self, request):
        body = dict(request.data)
        property_view_id = body['property_view_id']
        interval = body['interval']
        excluded_meter_ids = body['excluded_meter_ids']

        property_view = PropertyView.objects.get(pk=property_view_id)
        property_id = property_view.property.id
        org_id = property_view.cycle.organization_id
        scenario_ids = [s.id for s in property_view.state.scenarios.all()]

        exporter = PropertyMeterReadingsExporter(property_id, org_id, excluded_meter_ids, scenario_ids=scenario_ids)

        return exporter.readings_and_column_defs(interval)

    @ajax_request_class
    @action(detail=False, methods=['GET'])
    def valid_types_units(self, request):
        return {
            type: list(units.keys())
            for type, units
            in kbtu_thermal_conversion_factors("US").items()
        }

# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer

from seed.data_importer.meters_parser import MetersParser
from seed.data_importer.utils import (
    kbtu_thermal_conversion_factors,
    usage_point_id
)
from seed.decorators import ajax_request_class
from seed.lib.mcm import reader
from seed.models import ImportFile, Meter, PropertyView
from seed.serializers.meters import MeterSerializer
from seed.utils.meters import PropertyMeterReadingsExporter
from seed.utils.viewsets import SEEDOrgCreateUpdateModelViewSet


class MeterViewSetV2(SEEDOrgCreateUpdateModelViewSet):
    serializer_class = MeterSerializer
    renderer_classes = (JSONRenderer,)
    pagination_class = None
    model = Meter
    parser_classes = (JSONParser,)
    orgfilter = 'property__organization'

    @ajax_request_class
    @action(detail=False, methods=['POST'])
    def parsed_meters_confirmation(self, request):
        body = dict(request.data)
        file_id = body['file_id']
        org_id = body['organization_id']

        import_file = ImportFile.objects.get(pk=file_id)
        parser = reader.MCMParser(import_file.local_file, sheet_name='Meter Entries')
        raw_meter_data = list(parser.data)

        meters_parser = MetersParser(org_id, raw_meter_data)

        result = {}

        result["validated_type_units"] = meters_parser.validated_type_units()
        result["proposed_imports"] = meters_parser.proposed_imports
        result["unlinkable_pm_ids"] = meters_parser.unlinkable_pm_ids

        return result

    @ajax_request_class
    @action(detail=False, methods=['POST'])
    def greenbutton_parsed_meters_confirmation(self, request):
        body = dict(request.data)
        file_id = body['file_id']
        org_id = body['organization_id']
        view_id = body['view_id']

        import_file = ImportFile.objects.get(pk=file_id)
        parser = reader.GreenButtonParser(import_file.local_file)
        raw_meter_data = list(parser.data)

        property_id = PropertyView.objects.get(pk=view_id).property_id
        meters_parser = MetersParser(org_id, raw_meter_data, source_type=Meter.GREENBUTTON, property_id=property_id)

        result = {}

        result["validated_type_units"] = meters_parser.validated_type_units()
        result["proposed_imports"] = meters_parser.proposed_imports

        import_file.matching_results_data['property_id'] = property_id
        import_file.save()

        return result

    @ajax_request_class
    @action(detail=False, methods=['POST'])
    def property_meters(self, request):
        body = dict(request.data)
        property_view_id = body['property_view_id']
        property_view = PropertyView.objects.get(pk=property_view_id)
        property_id = property_view.property.id
        scenario_ids = [s.id for s in property_view.state.scenarios.all()]

        res = []
        for meter in Meter.objects.filter(Q(property_id=property_id) | Q(scenario_id__in=scenario_ids)):
            if meter.source == meter.GREENBUTTON:
                source_id = usage_point_id(meter.source_id)
            else:
                source_id = meter.source_id

            res.append({
                'id': meter.id,
                'type': meter.get_type_display(),
                'source': meter.get_source_display(),
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

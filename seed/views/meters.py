# !/usr/bin/env python
# encoding: utf-8

from rest_framework import viewsets
from rest_framework.decorators import list_route

from seed.data_importer.meters_parsers import PMMeterParser
from seed.data_importer.utils import kbtu_thermal_conversion_factors
from seed.decorators import ajax_request_class
from seed.lib.mcm import reader
from seed.models import (
    ImportFile,
    PropertyView,
)
from seed.utils.meters import PropertyMeterReadingsExporter


class MeterViewSet(viewsets.ViewSet):

    @ajax_request_class
    @list_route(methods=['POST'])
    def parsed_meters_confirmation(self, request):
        body = dict(request.data)
        file_id = body['file_id']
        org_id = body['organization_id']

        import_file = ImportFile.objects.get(pk=file_id)
        parser = reader.MCMParser(import_file.local_file)
        raw_meter_data = list(parser.data)

        meters_parser = PMMeterParser(org_id, raw_meter_data)

        result = {}

        result["validated_type_units"] = meters_parser.validated_type_units()
        result["proposed_imports"] = meters_parser.proposed_imports()
        result["unlinkable_pm_ids"] = meters_parser.unlinkable_pm_ids

        return result

    @ajax_request_class
    @list_route(methods=['POST'])
    def property_energy_usage(self, request):
        body = dict(request.data)
        property_view_id = body['property_view_id']
        org_id = body['organization_id']
        property_id = PropertyView.objects.get(pk=property_view_id).property.id

        exporter = PropertyMeterReadingsExporter(property_id, org_id)

        return exporter.readings_and_headers()

    @ajax_request_class
    @list_route(methods=['GET'])
    def valid_types_units(self, request):
        return {
            type: list(units.keys())
            for type, units
            in kbtu_thermal_conversion_factors("US").items()
        }

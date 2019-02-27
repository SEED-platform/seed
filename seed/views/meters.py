# !/usr/bin/env python
# encoding: utf-8

from rest_framework import viewsets
from rest_framework.decorators import list_route

from seed.data_importer.meters_parsers import PMMeterParser
from seed.decorators import ajax_request_class
from seed.lib.mcm import reader
from seed.models import ImportFile


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

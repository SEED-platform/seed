# !/usr/bin/env python
# encoding: utf-8

from rest_framework import viewsets
from rest_framework.decorators import action

from seed.data_importer.utils import (
    kbtu_thermal_conversion_factors,
)
from seed.decorators import ajax_request_class


class MeterViewSet(viewsets.ViewSet):

    @ajax_request_class
    @action(detail=False, methods=['GET'])
    def valid_types_units(self, request):
        return {
            type: list(units.keys())
            for type, units
            in kbtu_thermal_conversion_factors("US").items()
        }

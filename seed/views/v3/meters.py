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
        """
        Returns the valid type for units.

        The valid type and unit combinations are built from US Thermal Conversion
        values. As of this writing, the valid combinations are the same as for
        Canadian conversions, even though the actual factors may differ between
        the two.
        (https://portfoliomanager.energystar.gov/pdf/reference/Thermal%20Conversions.pdf)
        """
        return {
            type: list(units.keys())
            for type, units
            in kbtu_thermal_conversion_factors("US").items()
        }

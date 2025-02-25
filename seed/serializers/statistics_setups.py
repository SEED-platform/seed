"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models.statistics_setups import StatisticsSetup


class StatisticsSetupSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(required=True)

    class Meta:
        model = StatisticsSetup
        fields = (
            "id",
            "organization_id",
            "gfa_column",
            "gfa_units",
            "electricity_column",
            "electricity_units",
            "natural_gas_column",
            "natural_gas_units"
        )

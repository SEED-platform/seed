# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework import serializers

from seed.models import Column, TaxLot, TaxLotProperty, TaxLotState, TaxLotView


class TaxLotLabelsField(serializers.RelatedField):
    def to_representation(self, value):
        return value.id


class TaxLotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxLot
        fields = '__all__'


class TaxLotPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxLotProperty
        fields = '__all__'


class TaxLotStateSerializer(serializers.ModelSerializer):
    extra_data = serializers.JSONField()

    class Meta:
        model = TaxLotState
        fields = '__all__'

    def to_representation(self, data):
        """Overwritten to handle extra_data null fields"""
        result = super().to_representation(data)

        if data.extra_data:
            organization = data.organization
            extra_data_columns = Column.objects.filter(
                organization=organization,
                is_extra_data=True,
                table_name='TaxLotState'
            ).values_list('column_name', flat=True)

            prepopulated_extra_data = {
                col_name: data.extra_data.get(col_name, None)
                for col_name
                in extra_data_columns
            }

            result['extra_data'] = prepopulated_extra_data

        return result


class BriefTaxlotViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxLotView
        depth = 1
        fields = ('id', 'cycle', 'taxlot_id')


class TaxLotViewSerializer(serializers.ModelSerializer):
    # list of status labels (rather than the join field)
    labels = TaxLotLabelsField(read_only=True, many=True)

    state = TaxLotStateSerializer()

    class Meta:
        model = TaxLotView
        fields = '__all__'
        depth = 1


class UpdateTaxLotPayloadSerializer(serializers.Serializer):
    state = TaxLotStateSerializer()

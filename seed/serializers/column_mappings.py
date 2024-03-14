#!/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework import serializers

from seed.models import ColumnMapping
from seed.serializers.columns import ColumnSerializer


class ColumnMappingSerializer(serializers.ModelSerializer):
    organization_id = serializers.PrimaryKeyRelatedField(source='super_organization',
                                                         read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(source='user', read_only=True)

    class Meta:
        model = ColumnMapping
        exclude = ('column_raw', 'column_mapped')

    def to_representation(self, obj):
        """Return only the first items in the column_raw and column_mapped"""
        result = super().to_representation(obj)

        if obj.column_raw and obj.column_raw.first():
            result['column_raw'] = ColumnSerializer(obj.column_raw.first()).data

        if obj.column_mapped and obj.column_mapped.first():
            result['column_mapped'] = ColumnSerializer(obj.column_mapped.first()).data

        return result


class ImportMappingSerializer(serializers.Serializer):
    from_field = serializers.CharField()
    from_units = serializers.CharField()
    to_field = serializers.CharField()
    to_field_display_name = serializers.CharField()
    to_table_name = serializers.CharField()


class SaveColumnMappingsRequestPayloadSerializer(serializers.Serializer):
    """
    Note that this is _not_ a model serializer, but used only for saving mappings

    Example:
    {
        "mappings": [
            {
                'from_field': 'eui',  # raw field in import file
                'from_units': 'kBtu/ft**2/year', # pint-parsable units, optional
                'to_field': 'energy_use_intensity',
                'to_field_display_name': 'Energy Use Intensity',
                'to_table_name': 'PropertyState',
            },
            {
                'from_field': 'gfa',
                'from_units': 'ft**2', # pint-parsable units, optional
                'to_field': 'gross_floor_area',
                'to_field_display_name': 'Gross Floor Area',
                'to_table_name': 'PropertyState',
            }
        ]
    }
    """
    mappings = serializers.ListField(child=ImportMappingSerializer())

# !/usr/bin/env python
# encoding: utf-8

from rest_framework import serializers

from seed.serializers.base import ChoiceField
from seed.models import ColumnMappingPreset


class ColumnMappingPresetSerializer(serializers.ModelSerializer):
    preset_type = ChoiceField(choices=ColumnMappingPreset.COLUMN_MAPPING_PRESET_TYPES, default=ColumnMappingPreset.NORMAL)

    class Meta:
        model = ColumnMappingPreset
        fields = '__all__'

    def validate_mappings(self, mappings):
        """if the preset is for BuildingSync, make sure it has valid mappings"""
        preset_types_dict = dict(ColumnMappingPreset.COLUMN_MAPPING_PRESET_TYPES)
        bsync_presets = [
            preset_types_dict[ColumnMappingPreset.BUILDINGSYNC_DEFAULT],
            preset_types_dict[ColumnMappingPreset.BUILDINGSYNC_CUSTOM]
        ]
        preset_type = self.initial_data.get('preset_type')
        if preset_type is None or preset_type not in bsync_presets:
            return mappings

        for mapping in mappings:
            if mapping.get('from_field_value') is None:
                raise serializers.ValidationError(f'All BuildingSync mappings must include "from_field_value": for mapping {mapping["from_field"]}')

        return mappings

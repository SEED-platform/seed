# !/usr/bin/env python
# encoding: utf-8

from rest_framework import serializers

from seed.serializers.base import ChoiceField
from seed.models import ColumnMappingProfile


class ColumnMappingProfileSerializer(serializers.ModelSerializer):
    profile_type = ChoiceField(choices=ColumnMappingProfile.COLUMN_MAPPING_PROFILE_TYPES, default=ColumnMappingProfile.NORMAL)

    class Meta:
        model = ColumnMappingProfile
        fields = '__all__'

    def validate_mappings(self, mappings):
        """if the profile is for BuildingSync, make sure it has valid mappings"""
        profile_types_dict = dict(ColumnMappingProfile.COLUMN_MAPPING_PROFILE_TYPES)
        bsync_profiles = [
            profile_types_dict[ColumnMappingProfile.BUILDINGSYNC_DEFAULT],
            profile_types_dict[ColumnMappingProfile.BUILDINGSYNC_CUSTOM]
        ]
        profile_type = self.initial_data.get('profile_type')
        if profile_type is None or profile_type not in bsync_profiles:
            return mappings

        for mapping in mappings:
            if mapping.get('from_field_value') is None:
                raise serializers.ValidationError(f'All BuildingSync mappings must include "from_field_value": for mapping {mapping["from_field"]}')

        return mappings

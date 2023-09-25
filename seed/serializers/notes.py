# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework import serializers

from seed.models import Note
from seed.serializers.base import ChoiceField


class NoteSerializer(serializers.ModelSerializer):
    note_type = ChoiceField(choices=Note.NOTE_TYPES)
    organization_id = serializers.IntegerField(allow_null=True, read_only=True)
    property_view_id = serializers.IntegerField(allow_null=True, read_only=True)
    taxlot_view_id = serializers.IntegerField(allow_null=True, read_only=True)
    user_id = serializers.IntegerField(allow_null=True, read_only=True)

    class Meta:
        model = Note
        exclude = ('property_view', 'taxlot_view', 'user', 'organization')

    def to_representation(self, instance):
        """Override the to_representation method to remove the property or taxlot view id if it is null"""
        ret = super().to_representation(instance)
        # only show the non-null (taxlot|property)_view_id
        if ret['property_view_id'] is None:
            del ret['property_view_id']
        elif ret['taxlot_view_id'] is None:
            del ret['taxlot_view_id']
        return ret

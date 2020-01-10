# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
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

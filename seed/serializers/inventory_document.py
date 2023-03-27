# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author Katherine Fleming <katherine.fleming@nrel.gov>
"""
from rest_framework import serializers

from seed.models import InventoryDocument
from seed.serializers.base import ChoiceField


class InventoryDocumentSerializer(serializers.ModelSerializer):
    file_type = ChoiceField(choices=InventoryDocument.FILE_TYPES)

    class Meta:
        model = InventoryDocument
        fields = '__all__'

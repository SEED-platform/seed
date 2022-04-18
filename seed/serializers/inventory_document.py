# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Katherine Fleming <katherine.fleming@nrel.gov>
"""

from rest_framework import serializers

from seed.models import (
    InventoryDocument,
)
from seed.serializers.base import ChoiceField


class InventoryDocumentSerializer(serializers.ModelSerializer):
    file_type = ChoiceField(choices=InventoryDocument.FILE_TYPES)

    class Meta:
        model = InventoryDocument
        fields = '__all__'

# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models import Element


class ElementSerializer(serializers.ModelSerializer):
    id = serializers.ModelField(
        model_field=Element._meta.get_field("element_id"), help_text=Element._meta.get_field("element_id").help_text
    )
    code = serializers.SerializerMethodField()

    class Meta:
        model = Element
        exclude = ["element_id", "organization"]

    def get_code(self, element):
        return element.code.code

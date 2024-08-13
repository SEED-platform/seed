# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models import PostOfficeEmail, PostOfficeEmailTemplate


class PostOfficeEmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostOfficeEmailTemplate
        fields = "__all__"
        extra_kwargs = {"user": {"read_only": True}, "organization": {"read_only": True}}


class PostOfficeEmailSerializer(serializers.ModelSerializer):
    to = serializers.ListField(
        child=serializers.EmailField(),
        allow_empty=False,
    )
    cc = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        allow_empty=True,
    )
    bcc = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = PostOfficeEmail
        fields = "__all__"

        extra_kwargs = {
            "user": {"read_only": True},
            "organization": {"read_only": True},
            "inventory_id": {"read_only": True},
            "inventory_type": {"read_only": True},
        }

    def validate(self, data):
        inventory_id = self.initial_data.get("inventory_id")
        if inventory_id is not None and not isinstance(inventory_id, list):
            raise serializers.ValidationError("'inventory_id' must be a list.")
        return data

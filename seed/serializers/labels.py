# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""
from rest_framework import serializers

from seed.models import StatusLabel as Label


class LabelSerializer(serializers.ModelSerializer):
    organization_id = serializers.PrimaryKeyRelatedField(
        source="super_organization",
        read_only=True,
    )
    is_applied = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        """
        Labels always exist in the context of the organization they are
        assigned to.  This serializer requires that the `super_organization`
        for the label be passed into the serializer during initialization so
        that uniqueness constraints involving the `super_organization` can be
        validated by the serializer.

        """
        if 'super_organization' not in kwargs:
            return
        super_organization = kwargs.pop('super_organization')
        super().__init__(*args, **kwargs)
        if getattr(self, 'initial_data', None):
            self.initial_data['super_organization'] = super_organization.pk

    class Meta:
        fields = (
            "id",
            "name",
            "color",
            "organization_id",
            "super_organization",
            "is_applied",
            "show_in_list",
        )
        extra_kwargs = {
            "super_organization": {"write_only": True},
        }
        model = Label

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "is_applied" not in dir(instance):
            del ret['is_applied']

        return ret

    def get_is_applied(self, obj):
        if "is_applied" not in dir(obj):
            return None

        elif obj.is_applied == [None]:
            return []

        else:
            return obj.is_applied

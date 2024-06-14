"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models import PropertyViewLabel


class PropertyViewLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyViewLabel
        fields = "__all__"

    def to_representation(self, obj):
        result = super().to_representation(obj)
        result["show_in_list"] = obj.statuslabel.show_in_list
        result["color"] = obj.statuslabel.color
        result["name"] = obj.statuslabel.name
        return result

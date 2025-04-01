"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models import Organization, OrganizationUser


class SaveSettingsOrgFieldSerializer(serializers.Serializer):
    sort_column = serializers.CharField()


class SaveSettingsOrganizationSerializer(serializers.Serializer):
    query_threshold = serializers.IntegerField()
    name = serializers.CharField(max_length=100)
    fields = SaveSettingsOrgFieldSerializer(many=True)
    public_fields = SaveSettingsOrgFieldSerializer(many=True)
    display_units_eui = serializers.ChoiceField(choices=Organization.MEASUREMENT_CHOICES_EUI)
    display_units_area = serializers.ChoiceField(choices=Organization.MEASUREMENT_CHOICES_AREA)
    display_units_ghg = serializers.ChoiceField(choices=Organization.MEASUREMENT_CHOICES_GHG)
    display_units_ghg_intensity = serializers.ChoiceField(choices=Organization.MEASUREMENT_CHOICES_GHG_INTENSITY)
    display_decimal_places = serializers.IntegerField(min_value=0)
    display_meter_units = serializers.JSONField()
    display_meter_water_units = serializers.JSONField()
    thermal_conversion_assumption = serializers.ChoiceField(choices=Organization.THERMAL_CONVERSION_ASSUMPTION_CHOICES)
    mapquest_api_key = serializers.CharField()
    geocoding_enabled = serializers.BooleanField()
    property_display_field = serializers.CharField()
    taxlot_display_field = serializers.CharField()
    new_user_email_from = serializers.CharField(max_length=128)
    new_user_email_subject = serializers.CharField(max_length=128)
    new_user_email_content = serializers.CharField(max_length=1024)
    new_user_email_signature = serializers.CharField(max_length=128)
    at_organization_token = serializers.CharField(max_length=128)
    audit_template_user = serializers.CharField(max_length=128)
    audit_template_password = serializers.CharField(max_length=128)
    salesforce_enabled = serializers.BooleanField()
    ubid_threshold = serializers.FloatField(min_value=0.0001, max_value=1)


class SaveSettingsSerializer(serializers.Serializer):
    organization = SaveSettingsOrganizationSerializer()


class SharedFieldSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    sort_column = serializers.CharField(max_length=100)
    field_class = serializers.CharField(max_length=100)
    title_class = serializers.CharField(max_length=100)
    type = serializers.CharField(max_length=100)
    field_type = serializers.CharField(max_length=100)
    sortable = serializers.CharField(max_length=100)


class SharedFieldsReturnSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=100)
    shared_fields = SharedFieldSerializer(many=True)
    public_fields = SharedFieldSerializer(many=True)

class OrganizationUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationUser
        fields = ["settings", "role_level", "status", "organization", "user"]

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result["email"] = instance.user.email
        result["first_name"] = instance.user.first_name
        result["last_name"] = instance.user.last_name
        return result


class OrganizationUsersSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=100)
    users = OrganizationUserSerializer(many=True)

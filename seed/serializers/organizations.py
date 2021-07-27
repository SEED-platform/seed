# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers
from seed.models import Organization


class SaveSettingsOrgFieldSerializer(serializers.Serializer):
    sort_column = serializers.CharField()


class SaveSettingsOrganizationSerializer(serializers.Serializer):
    query_threshold = serializers.IntegerField()
    name = serializers.CharField(max_length=100)
    fields = SaveSettingsOrgFieldSerializer(many=True)
    public_fields = SaveSettingsOrgFieldSerializer(many=True)
    display_units_eui = serializers.ChoiceField(choices=Organization.MEASUREMENT_CHOICES_EUI)
    display_units_area = serializers.ChoiceField(choices=Organization.MEASUREMENT_CHOICES_AREA)
    display_significant_figures = serializers.IntegerField(min_value=0)
    display_meter_units = serializers.JSONField()
    thermal_conversion_assumption = serializers.ChoiceField(choices=Organization.THERMAL_CONVERSION_ASSUMPTION_CHOICES)
    mapquest_api_key = serializers.CharField()
    geocoding_enabled = serializers.BooleanField()
    property_display_field = serializers.CharField()
    taxlot_display_field = serializers.CharField()
    new_user_email_from = serializers.CharField(max_length=128)
    new_user_email_subject = serializers.CharField(max_length=128)
    new_user_email_content = serializers.CharField(max_length=1024)
    new_user_email_signature = serializers.CharField(max_length=128)


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


class OrganizationUserSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=100)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    user_id = serializers.IntegerField()
    role = serializers.CharField(max_length=100)


class OrganizationUsersSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=100)
    users = OrganizationUserSerializer(many=True)

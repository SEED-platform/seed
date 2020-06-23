# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from rest_framework import serializers
from seed.models.data_quality import Rule
from seed.models import StatusLabel


class RuleSerializer(serializers.ModelSerializer):
    data_type = serializers.CharField(source='get_data_type_display', required=False)
    status_label = serializers.PrimaryKeyRelatedField(
        queryset=StatusLabel.objects.all(),
        allow_null=True,
        required=False
    )
    severity = serializers.CharField(source='get_severity_display', required=False)

    class Meta:
        model = Rule
        fields = [
            'condition',
            'data_type',
            'enabled',
            'field',
            'id',
            'max',
            'min',
            'not_null',
            'required',
            'rule_type',
            'severity',
            'status_label',
            'table_name',
            'text_match',
            'units',
        ]

    def validate_status_label(self, label):
        """
        Note: DQ Rules can be shared from parent to child but child orgs can
        have their own labels. So, a Rule shouldn't be associated to Labels
        from child orgs. In other words, Rule and associated Label should be
        from the same org.
        """
        if label is not None and label.super_organization_id != self.instance.data_quality_check.organization_id:
            raise serializers.ValidationError(
                f'Label with ID {label.id} not found in organization, {self.instance.data_quality_check.organization.name}.'
            )
        else:
            return label

    def validate(self, data):
        """
        These are validations that involve values between multiple fields.

        Custom validations for field values in isolation should still be
        contained in 'validate_{field_name}' methods which are only checked when
        that field is in 'data'.
        """
        data_invalid = False
        validation_messages = []

        # Rule with SEVERITY setting of "valid" should have a Label.
        severity_is_valid = self.instance.severity == Rule.SEVERITY_VALID
        severity_unchanged = 'get_severity_display' not in data
        severity_will_be_valid = data.get('get_severity_display') == dict(Rule.SEVERITY)[Rule.SEVERITY_VALID]

        if (severity_is_valid and severity_unchanged) or severity_will_be_valid:
            # Defaulting to "FOO" enables a value check of either "" or None (even if key doesn't exist)
            label_will_be_removed = data.get('status_label', "FOO") in ["", None]
            label_is_not_associated = self.instance.status_label is None
            label_unchanged = 'status_label' not in data
            if label_will_be_removed or (label_is_not_associated and label_unchanged):
                data_invalid = True
                validation_messages.append(
                    'Label must be assigned when using \'Valid\' Data Severity.'
                )

        # Rule must NOT include or exclude an empty string.
        is_include_or_exclude = self.instance.condition in [Rule.RULE_INCLUDE, Rule.RULE_EXCLUDE]
        condition_unchanged = 'condition' not in data
        will_be_include_or_exclude = data.get('condition') in [Rule.RULE_INCLUDE, Rule.RULE_EXCLUDE]

        if (is_include_or_exclude and condition_unchanged) or will_be_include_or_exclude:
            # Defaulting to "FOO" enables a value check of either "" or None (only if key exists)
            text_match_will_be_empty = data.get('text_match', "FOO") in ["", None]
            text_match_is_empty = getattr(self.instance, 'text_match', "FOO") in ["", None]
            text_match_unchanged = 'text_match' not in data

            if text_match_will_be_empty or (text_match_is_empty and text_match_unchanged):
                data_invalid = True
                validation_messages.append(
                    'Rule must not include or exclude an empty string.'
                )

        if data_invalid:
            raise serializers.ValidationError({
                'general_validation_error': validation_messages
            })
        else:
            return data

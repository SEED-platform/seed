# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from rest_framework import serializers
from seed.models.data_quality import Rule, DataQualityCheck
from seed.models import StatusLabel


class RuleSerializer(serializers.ModelSerializer):
    status_label = serializers.PrimaryKeyRelatedField(
        queryset=StatusLabel.objects.all(),
        allow_null=True,
        required=False
    )

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
            'for_derived_column',
        ]

    def create(self, validated_data):
        # For now, use an Org ID to find the DQ Check ID to apply (later, use the DQ Check ID directly)
        org_id = self.context['request'].parser_context['kwargs']['nested_organization_id']
        validated_data['data_quality_check_id'] = DataQualityCheck.retrieve(org_id).id

        return Rule.objects.create(**validated_data)

    def validate_status_label(self, label):
        """
        Note: DQ Rules can be shared from parent to child but child orgs can
        have their own labels. So, a Rule shouldn't be associated to Labels
        from child orgs. In other words, Rule and associated Label should be
        from the same org.
        """
        dq_org_id = None
        if self.instance is not None:
            dq_org_id = self.instance.data_quality_check.organization_id
        else:
            if 'request' not in self.context:
                raise serializers.ValidationError('`request` must exist in serializer context when no instance data is provided.')

            dq_org_id = int(self.context['request'].parser_context['kwargs']['nested_organization_id'])

        if label is not None and label.super_organization_id != dq_org_id:
            raise serializers.ValidationError(
                f'Label with ID {label.id} not found in organization, {dq_org_id}.'
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
        validation_message = ''

        # Rule with SEVERITY setting of "valid" should have a Label.
        if self.instance is None:
            # Rule is new
            severity_is_valid = False
            label_is_not_associated = False
        else:
            severity_is_valid = self.instance.severity == Rule.SEVERITY_VALID
            label_is_not_associated = self.instance.status_label is None
        severity_unchanged = 'severity' not in data
        severity_will_be_valid = data.get('severity') == Rule.SEVERITY_VALID

        if (severity_is_valid and severity_unchanged) or severity_will_be_valid:
            # Defaulting to "FOO" enables a value check of either "" or None (even if key doesn't exist)
            label_will_be_removed = data.get('status_label', "FOO") in ["", None]
            label_unchanged = 'status_label' not in data
            if label_will_be_removed or (label_is_not_associated and label_unchanged):
                data_invalid = True
                validation_message += 'Label must be assigned when using \'Valid\' Data Severity. '

        # Rule must NOT include or exclude an empty string.
        if self.instance is None:
            # Rule is new, so severity "could not have been" include or exclude.
            is_include_or_exclude = False
        else:
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
                validation_message += 'Rule must not include or exclude an empty string. '

        if data_invalid:
            raise serializers.ValidationError({
                'message': validation_message
            })
        else:
            return data

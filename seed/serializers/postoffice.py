# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework import serializers

from seed.models import PostOfficeEmail as Email
from seed.models import PostOfficeEmailTemplate as EmailTemplate


class PostOfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = ('id', 'name', 'description', 'subject', 'content', 'html_content', 'created', 'last_updated',
                  'default_template_id', 'language')
        extra_kwargs = {
            'user': {'read_only': True},
            'organization': {'read_only': True}
        }


class PostOfficeEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Email
        fields = ('id', 'from_email', 'to', 'cc', 'bcc', 'subject', 'message', 'html_message', 'status', 'priority',
                  'created', 'last_updated', 'scheduled_time', 'headers', 'context', 'template_id', 'backend_alias',
                  'number_of_retries', 'expires_at')
        extra_kwargs = {
            'user': {'read_only': True},
            'organization': {'read_only': True}
        }

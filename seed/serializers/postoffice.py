# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA

"""
from rest_framework import serializers
from seed.models import PostOfficeEmail as Email, PostOfficeEmailTemplate as EmailTemplate


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

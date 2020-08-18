# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers

from post_office.models import EmailTemplate, Email

import post_office.fields

# , Email


class PostOfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = ('id', 'name','description', 'subject','content' ,'html_content','created','last_updated', 'default_template_id', 'language')


class PostOfficeEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Email
        fields = '__all__'
        # '__all__'
        # ('from_email', 'message')
        # ('from_email','to', 'cc', 'bcc', 'subject', 'message', 'html_message', 'status', 'priority', 'created', 'last_updated', 'scheduled_time', 'expires_at', 'number_of_retries', 'headers', 'template', )
        # 'status'
        # extra_kwargs = {
        #     'organization': {'read_only': True}
        # }

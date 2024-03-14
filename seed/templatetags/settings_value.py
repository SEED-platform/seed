# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

Simple templatetag to return a value from the settings file. e.g., {% settings_value "LOGIN_REDIRECT_URL" %}
"""
import logging

from django import template
from django.conf import settings

_log = logging.getLogger(__name__)

register = template.Library()


@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")

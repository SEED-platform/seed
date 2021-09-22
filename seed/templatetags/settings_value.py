# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

# Simple templatetag to return a value from the settings file. e.g., {% settings_value "LOGIN_REDIRECT_URL" %}

import logging

from django import template
from django.conf import settings

_log = logging.getLogger(__name__)

register = template.Library()


@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")

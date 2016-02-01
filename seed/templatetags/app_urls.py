# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import json

from django import template
from django.conf import settings
from djangular.core.urlresolvers import urls_by_namespace

register = template.Library()


@register.simple_tag
def namespaced_urls():
    """returns all namespaced urls (see urls_by_namespace) into a json object.
    This removes the need to add this code into each view.
    use:
        {% load app_urls %}
    ...
        <script>
            window.config.app_urls ={% namespaced_urls %};
        </script>
    """
    apps = settings.BE_URL_APPS
    app_urls = dict((app, urls_by_namespace(app)) for app in apps)
    app_urls = json.dumps(app_urls)
    return app_urls

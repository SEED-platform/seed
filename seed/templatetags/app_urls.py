"""
:copyright: (c) 2014 Building Energy Inc
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
            window.BE.app_urls ={% namespaced_urls %};
        </script>
    """
    apps = settings.BE_URL_APPS
    app_urls = dict((app, urls_by_namespace(app)) for app in apps)
    app_urls = json.dumps(app_urls)
    return app_urls

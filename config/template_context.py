"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""


def session_key(request):
    from django.conf import settings
    try:
        return {'SESSION_KEY': request.COOKIES[settings.SESSION_COOKIE_NAME]}
    except BaseException:
        return {}


def sentry_js(request):
    from django.conf import settings

    # Exists and isn't None.
    if hasattr(settings, 'SENTRY_JS_DSN') and settings.SENTRY_JS_DSN:
        return {'SENTRY_JS_DSN': settings.SENTRY_JS_DSN}
    return {}

"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
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

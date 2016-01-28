"""
:copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""


def compress_enabled(request):
    from django.conf import settings
    return {'COMPRESS_ENABLED': settings.COMPRESS_ENABLED}


def session_key(request):
    from django.conf import settings
    try:
        return {'SESSION_KEY': request.COOKIES[settings.SESSION_COOKIE_NAME]}
    except:
        return {}

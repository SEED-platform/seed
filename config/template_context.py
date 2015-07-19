"""
:copyright: (c) 2014 Building Energy Inc
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

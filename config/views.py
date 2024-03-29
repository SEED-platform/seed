"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.conf import settings
from django.http import HttpResponse


def robots_txt(request, allow=False):
    env = getattr(settings, 'ENV', 'development').lower()

    if env == 'production' or allow:
        content = 'User-agent: *\nAllow: /'
    else:
        content = 'User-agent: *\nDisallow: /'

    return HttpResponse(content, content_type='text/plain')

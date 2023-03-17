"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.conf import settings
from django.http import HttpResponse


def robots_txt(request, allow=False):
    try:
        if settings.ENV.lower() != "production":
            return HttpResponse(
                "User-agent: *\nDisallow: /", content_type="text/plain"
            )
        else:
            return HttpResponse(
                "User-agent: *\nAllow: /", content_type="text/plain"
            )
    except BaseException:
        pass
    if allow:
        return HttpResponse("User-agent: *\nAllow: /", content_type="text/plain")
    else:
        return HttpResponse(
            "User-agent: *\nDisallow: /", content_type="text/plain"
        )

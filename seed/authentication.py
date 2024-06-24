# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import authentication

from seed.landing.models import SEEDUser as User


class SEEDAuthentication(authentication.BaseAuthentication):
    """
    Django Rest Framework implementation of the `seed.utils.api.get_api_request_user` functionality
    to extract the User from the HTTP_AUTHORIZATION header using an API key.
    """

    def authenticate(self, request):
        return User.process_header_request(request), None  # return None per base class

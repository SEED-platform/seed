# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
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

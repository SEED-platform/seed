# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import authentication
from rest_framework import exceptions


class SEEDAuthentication(authentication.BaseAuthentication):
    """
    Django Rest Framework implementation of the
    `seed.utils.api.get_api_request_user` functionality to extract the User
    from the HTTP_AUTHORIZATION header using an API key.
    """
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')

        if not auth_header:
            return None

        try:
            from seed.landing.models import SEEDUser as User
            username, api_key = auth_header.split(':')
            user = User.objects.get(api_key=api_key, username=username)
            return user, api_key
        except ValueError:
            raise exceptions.AuthenticationFailed("Invalid HTTP_AUTHORIZATION Header")
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API key")

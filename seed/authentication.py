"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import authentication

from seed.landing.models import SEEDUser as User

# WWW-Authenticate challenge for 401 responses, matching the one DRF sends when JWTAuthentication is the first
# authentication class. A Bearer challenge, unlike Basic, does not make browsers show a sign-in prompt.
AUTHENTICATE_HEADER = 'Bearer realm="api"'


class SEEDAuthentication(authentication.BaseAuthentication):
    """
    Django Rest Framework implementation of the `seed.utils.api.get_api_request_user` functionality
    to extract the User from the HTTP_AUTHORIZATION header using an API key.
    """

    def authenticate(self, request):
        return User.process_header_request(request), None  # return None per base class


class SEEDSessionAuthentication(authentication.SessionAuthentication):
    """
    Session authentication that also rejects an invalid Authorization header.

    Session authentication comes before SEEDAuthentication, so for a signed-in session the header would otherwise never
    be checked, and invalid credentials would be ignored. A valid header changes nothing: the request still uses the
    session user and still needs a CSRF token.
    """

    def authenticate(self, request):
        session_user = getattr(request._request, "user", None)
        if session_user and session_user.is_active:
            # Raises AuthenticationFailed for an invalid Authorization header; returns None when there is none
            User.process_header_request(request)
        return super().authenticate(request)

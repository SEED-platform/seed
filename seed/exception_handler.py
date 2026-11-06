"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author Fable Turas <fable@raintechpdx.com>
:description provides function for handling exceptions not otherwise handled by DRF
"""

from django.db.models.deletion import ProtectedError
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from seed.authentication import AUTHENTICATE_HEADER


def custom_exception_handler(exc, context):
    """Handle select errors not handled by DRF's default exception handler."""
    response = exception_handler(exc, context)

    if response is not None and isinstance(exc, exceptions.AuthenticationFailed):
        # DRF returns 403 for invalid credentials when the view's first authentication class has no WWW-Authenticate
        # challenge, as with the SessionAuthentication-first SEEDOrg* viewsets. Invalid credentials are a 401. Missing
        # credentials (NotAuthenticated) still get DRF's response.
        response.status_code = status.HTTP_401_UNAUTHORIZED
        if "WWW-Authenticate" not in response:
            response["WWW-Authenticate"] = AUTHENTICATE_HEADER
        return response

    if response is None and isinstance(exc, ProtectedError):
        # provides handling of ProtectError from use of models
        # ForeignKey on_delete=PROTECT argument.
        msg = _("Cannot delete protected objects while related objects still exist")
        data = {"detail": str(msg)}

        # Set Rollback removed in https://www.django-rest-framework.org/community/release-notes/#374. The
        # method is now handled in the views exception_handler which is called above
        # in exception_handler(exc, context)

        # set_rollback()
        return Response(data, status=status.HTTP_400_BAD_REQUEST)
    return response

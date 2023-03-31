#!/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author Fable Turas <fable@raintechpdx.com>
:description provides function for handling exceptions not otherwise handled by DRF
"""
from django.db.models.deletion import ProtectedError
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Handle select errors not handled by DRF's default exception handler."""
    response = exception_handler(exc, context)

    if response is None:
        if isinstance(exc, ProtectedError):
            # provides handling of ProtectError from use of models
            # ForeignKey on_delete=PROTECT argument.
            msg = _('Cannot delete protected objects while '
                    'related objects still exist')
            data = {'detail': str(msg)}

            # Set Rollback removed in https://www.django-rest-framework.org/community/release-notes/#374. The
            # method is now handled in the views exception_handler which is called above
            # in exception_handler(exc, context)

            # set_rollback()
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
    return response

#!/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.

:author Fable Turas <fable@raintechpdx.com>

provides function for handling exceptions not otherwise handled by DRF
"""

# Imports from Standard Library

# Imports from Third Party Modules

# Imports from Django
from django.db.models.deletion import ProtectedError
from rest_framework.views import exception_handler
from rest_framework import status
from rest_framework.compat import set_rollback
from rest_framework.response import Response
from django.utils import six
from django.utils.translation import ugettext_lazy as _
# Local Imports

# Constants

# Data Structure Definitions

# Private Functions

# Public Classes and Functions


def custom_exception_handler(exc, context):
    """Handle select errors not handled by DRF's default exception handler."""
    response = exception_handler(exc, context)

    if response is None:
        if isinstance(exc, ProtectedError):
            # provides handling of ProtectError from use of models
            # ForeignKey on_delete=PROTECT argument.
            msg = _('Cannot delete protected objects while '
                    'related objects still exist')
            data = {'detail': six.text_type(msg)}

            set_rollback()
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
    return response

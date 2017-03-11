#!/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author: Fable Turas fable@raintechpdx.com

This provides a custom DRF ModelViewSet for rendering SEED API views with the
necessary decorator and organization queryset mixins added, inheriting from
DRF's ModelViewSet and setting SEED relevant defaults to renderer_classes,
parser_classes, authentication_classes, and pagination_classes attributes.
"""

# Imports from Django
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.viewsets import ModelViewSet

# Local Imports
from seed.authentication import SEEDAuthentication
from seed.decorators import DecoratorMixin
from seed.lib.superperms.orgs.permissions import SEEDOrgPermissions
from seed.renderers import SEEDJSONRenderer as JSONRenderer
from seed.utils.api import (OrgCreateUpdateMixin, OrgQuerySetMixin,
                            drf_api_endpoint)
from seed.utils.pagination import ResultsListPagination

# Constants
AUTHENTICATION_CLASSES = (SessionAuthentication, SEEDAuthentication)
PARSER_CLASSES = (FormParser, MultiPartParser, JSONParser)
RENDERER_CLASSES = (JSONRenderer,)
PERMISSIONS_CLASSES = (SEEDOrgPermissions,)


# Public Classes and Functions

class SEEDOrgModelViewSet(DecoratorMixin(drf_api_endpoint), OrgQuerySetMixin,
                          ModelViewSet):
    """Viewset class customized with SEED standard attributes.

    Attributes:
        renderer_classes: Tuple of classes, default set to SEEDJSONRenderer.
        parser_classes: Tuple of classes, default set to drf's JSONParser.
        authentication_classes: Tuple of classes, default set to drf's
            SessionAuthentication and SEEDAuthentication.
        pagination_class: Default set to None to remove pagination key/value
            pairs from Json to ensure SEEDJSONRenderer can return correct
            {'status': 'success', 'data': data} format.
    """
    # TODO: adjust paginator and renderer to fix pagination into desired output
    renderer_classes = RENDERER_CLASSES
    parser_classes = PARSER_CLASSES
    authentication_classes = AUTHENTICATION_CLASSES
    permissions_classes = PERMISSIONS_CLASSES
    pagination_class = None


class SEEDOrgCreateUpdateModelViewSet(OrgCreateUpdateMixin,
                                      SEEDOrgModelViewSet):
    """Extends SEEDModelViewset to add perform_create method to attach org.

    For use on models that have a foreign key relationship to Organization via
    fieldname 'organization'. Models using 'super_organization' or having
    additional foreign key relationships, such as user, should extend
    SEEDOrgModelViewset and override perform_create/perform_update in the view.
    """
    pass

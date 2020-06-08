
# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pmerriam@quickleft.com>'
"""
from collections import namedtuple
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer

from seed.decorators import DecoratorMixin
from seed.filters import (
    LabelFilterBackend,
    InventoryFilterBackendWithInvType,
)
from seed.models import (
    StatusLabel as Label,
)
from seed.serializers.labels import (
    LabelSerializer,
)
from seed.utils.api import drf_api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.labels import _get_labels
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

ErrorState = namedtuple('ErrorState', ['status_code', 'message'])


class LabelsSchema(AutoSchemaHelper):
    def __init__(self, *args):
        super().__init__(*args)

        self.manual_fields = {
            ('GET', 'list'): [self.org_id_field()]
        }


class LabelViewSet(DecoratorMixin(drf_api_endpoint), SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """
    retrieve:
        Return a label instance by pk if it is within user`s specified org.

    list:
        Return all labels available to user through user`s specified org.

    create:
        Create a new label within user`s specified org.

    delete:
        Remove an existing label.

    update:
        Update a label record.
    """
    swagger_schema = LabelsSchema
    serializer_class = LabelSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser, FormParser)
    queryset = Label.objects.none()
    filter_backends = (LabelFilterBackend,)
    pagination_class = None
    _organization = None

    def get_queryset(self):
        labels = Label.objects.filter(
            super_organization=self.get_parent_org(self.request)
        ).order_by("name").distinct()
        return labels

    def get_serializer(self, *args, **kwargs):
        kwargs['super_organization'] = self.get_organization(self.request)
        inventory = InventoryFilterBackendWithInvType().filter_queryset(
            request=self.request, inv_type=None
        )
        kwargs['inventory'] = inventory
        return super().get_serializer(*args, **kwargs)

    def list(self, request):
        """
        Returns a list of all labels
        """
        inv_type = None
        qs = self.get_queryset()
        super_organization = self.get_organization(request)
        return _get_labels(request, qs, super_organization, inv_type)

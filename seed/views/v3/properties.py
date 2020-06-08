"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import viewsets
from collections import namedtuple

from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from seed.models import (
    StatusLabel as Label,
)
from seed.utils.api import OrgMixin
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.labels import _get_labels

ErrorState = namedtuple('ErrorState', ['status_code', 'message'])


class PropertiesSchema(AutoSchemaHelper):
    def __init__(self, *args):
        super().__init__(*args)

        self.manual_fields = {
            ('POST', 'labels'): [self.org_id_field()]
        }


class PropertyLabelsViewSet(viewsets.ViewSet, OrgMixin):
    swagger_schema = PropertiesSchema
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)
    _organization = None

    def get_queryset(self):
        labels = Label.objects.filter(
            super_organization=self.get_parent_org(self.request)
        ).order_by("name").distinct()
        return labels

    @action(detail=False, methods=['POST'])
    def labels(self, request):
        """
        Returns a list of all labels
        """
        inv_type = 'property_view'
        qs = self.get_queryset()
        super_organization = self.get_organization(request)
        return _get_labels(request, qs, super_organization, inv_type)

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pmerriam@quickleft.com>'
"""
import logging

from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer

from seed.models import (
    Note,
)
from seed.serializers.notes import (
    NoteSerializer,
)
from seed.utils.viewsets import SEEDOrgCreateUpdateModelViewSet

_log = logging.getLogger(__name__)


class NoteViewSet(SEEDOrgCreateUpdateModelViewSet):
    """API endpoint for viewing and creating notes.

            Returns::
                [
                    {
                        'id': Note's primary key
                        'name': Superfluous name,
                        'text': Note's text
                    }
                ]

    ---
    """
    serializer_class = NoteSerializer
    renderer_classes = (JSONRenderer,)
    pagination_class = None
    model = Note
    parser_classes = (JSONParser, FormParser)
    orgfilter = 'organization_id'

    def get_queryset(self):
        # check if the request is properties or taxlots
        org_id = self.get_organization(self.request)
        if self.kwargs.get('properties_pk', None):
            return Note.objects.filter(organization_id=org_id, property_view_id=self.kwargs.get('properties_pk'))
        elif self.kwargs.get('taxlots_pk', None):
            return Note.objects.filter(organization_id=org_id, taxlot_view_id=self.kwargs.get('taxlots_pk'))
        else:
            return Note.objects.filter(organization_id=org_id)

    def perform_create(self, serializer):
        org_id = self.get_organization(self.request)
        if self.kwargs.get('properties_pk', None):
            serializer.save(
                organization_id=org_id, user=self.request.user, property_view_id=self.kwargs.get('properties_pk', None)
            )
        elif self.kwargs.get('taxlots_pk', None):
            serializer.save(
                organization_id=org_id, user=self.request.user, taxlot_view_id=self.kwargs.get('taxlots_pk', None)
            )
        else:
            _log.warn("Unable to create model without a property_pk or taxlots_pk")

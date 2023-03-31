# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author 'Piper Merriam <pmerriam@quickleft.com>'
"""
import logging

from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.models import Note
from seed.serializers.notes import NoteSerializer
from seed.utils.viewsets import SEEDOrgCreateUpdateModelViewSet

_log = logging.getLogger(__name__)


class NoteViewSet(SEEDOrgCreateUpdateModelViewSet):
    """API endpoint for creating, retrieving, updating, and deleting notes. If it is an
    automated message which is typically trigger by a manual edit, then log_data will
    be populated with the data that was changed.

            Returns::
                [
                    {
                        'id': Note's primary key,
                        'note_type': Is it a note or automated log message,
                        'name': Superfluous name,
                        'text': Note's text,
                        'log_data': [{
                            "field": Modified field name,
                            "state_id": State's primary key,
                            "new_value": New value,
                            "previous_value": Previous value if any
                        }]
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

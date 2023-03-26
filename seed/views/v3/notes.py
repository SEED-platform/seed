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

from seed.models import Note, PropertyView
from seed.models.events import NoteEvent
from seed.serializers.notes import NoteSerializer
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

_log = logging.getLogger(__name__)


class NoteViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
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
        if self.kwargs.get('property_pk', None):
            return Note.objects.filter(organization_id=org_id, property_view_id=self.kwargs.get('property_pk'))
        elif self.kwargs.get('taxlot_pk', None):
            return Note.objects.filter(organization_id=org_id, taxlot_view_id=self.kwargs.get('taxlot_pk'))
        else:
            return Note.objects.filter(organization_id=org_id)

    def perform_create(self, serializer):
        org_id = self.get_organization(self.request)
        if self.kwargs.get('property_pk', None):
            property_view = PropertyView.objects.get(pk=self.kwargs.get('property_pk', None))
            note = serializer.save(
                organization_id=org_id, user=self.request.user, property_view=property_view
            )
            NoteEvent.objects.create(
                property=property_view.property,
                cycle=property_view.cycle,
                note=note
            )

        elif self.kwargs.get('taxlot_pk', None):
            serializer.save(
                organization_id=org_id, user=self.request.user, taxlot_view_id=self.kwargs.get('taxlot_pk', None)
            )
        else:
            _log.warn("Unable to create model without a property_pk or taxlot_pk")

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pmerriam@quickleft.com>'
"""
from collections import namedtuple

from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer

from seed.models import (
    Note,
)
from seed.serializers.notes import (
    NoteSerializer,
)
from seed.utils.viewsets import SEEDOrgCreateUpdateModelViewSet

ErrorState = namedtuple('ErrorState', ['status_code', 'message'])


class NoteViewSet(SEEDOrgCreateUpdateModelViewSet):
    """API endpoint for viewing and creating notes.

            Returns::
                [
                    {
                        'id': Note's primary key
                        'name': Superfulous name,
                        'text': Note's text
                    }
                ]

    ---
    """
    serializer_class = NoteSerializer
    renderer_classes = (JSONRenderer,)
    model = Note
    parser_classes = (JSONParser, FormParser)
    queryset = Note.objects.none()
    orgfilter = 'organization_id'

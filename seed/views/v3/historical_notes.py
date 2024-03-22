"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""
from django.utils.decorators import method_decorator

from seed.lib.superperms.orgs.decorators import (
    has_hierarchy_access,
    has_perm_class
)
from seed.models import HistoricalNote
from seed.serializers.historical_notes import HistoricalNoteSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import UpdateWithoutPatchModelMixin


@method_decorator(
    name='update',
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class('requires_member'),
        has_hierarchy_access(property_id_kwarg="property_pk")
    ]
)
class HistoricalNoteViewSet(UpdateWithoutPatchModelMixin, OrgMixin):
    # Update is the only necessary endpoint
    # Create is handled on Property create through post_save signal
    # List and Retrieve are handled on a per property basis
    # Delete is handled through Property cascade deletes
    serializer_class = HistoricalNoteSerializer
    queryset = HistoricalNote.objects.all()

"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_view

from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import HistoricalNote
from seed.serializers.historical_notes import HistoricalNoteSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import UpdateWithoutPatchModelMixin


@extend_schema_view(
    update=extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field(), AutoSchemaHelper.path_id_field("Property ID", name="property_pk")]
    )
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(property_id_kwarg="property_pk"),
    ],
    name="update",
)
class HistoricalNoteViewSet(UpdateWithoutPatchModelMixin, OrgMixin):
    """Updates a property's historical note"""

    # Update is the only necessary endpoint
    # Create is handled on Property create through post_save signal
    # List and Retrieve are handled on a per property basis
    # Delete is handled through Property cascade deletes
    serializer_class = HistoricalNoteSerializer
    queryset = HistoricalNote.objects.all()

    def get_queryset(self):
        # only the historical note of the property whose access is checked by `has_hierarchy_access`
        return HistoricalNote.objects.filter(property_id=self.kwargs.get("property_pk"))

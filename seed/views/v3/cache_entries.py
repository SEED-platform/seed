"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import re

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.permissions import get_org_id
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper, EmptySerializer
from seed.utils.cache import get_cache_raw


class CacheEntryViewSet(GenericViewSet, OrgMixin):
    """
    ViewSet for managing redis cache entries.
    """

    queryset = ()
    serializer_class = EmptySerializer

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.path_string_field("id", "The `unique_id` of the export or mapping results task"),
        ],
        responses={200: AutoSchemaHelper.schema_factory("object", description="The cached data, as stored by the task")},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
        ]
    )
    def retrieve(self, request, pk=None):
        """
        Retrieve cached data based on unique_id.
        """
        unique_id = pk
        # Only the authorized organization's task results (keyed by the organization ID and a 5-digit random number,
        # see `start_export` and `mapping_results`) can be retrieved, since other cache entries may hold other
        # organizations' data or credentials
        if not re.fullmatch(rf"{get_org_id(request)}\d{{5}}", str(unique_id)):
            return JsonResponse({"error": "No data found for the provided unique_id"}, status=404)
        data = get_cache_raw(unique_id)
        if not data:
            return JsonResponse({"error": "No data found for the provided unique_id"}, status=404)
        return JsonResponse(data)

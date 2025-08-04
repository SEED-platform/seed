from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.cache import get_cache_raw


class CacheEntryViewSet(GenericViewSet, OrgMixin):
    """
    ViewSet for managing redis cache entries.
    """

    manual_parameters = (
        [
            AutoSchemaHelper.query_org_id_field(),
        ],
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
        data = get_cache_raw(unique_id)
        if not data:
            return JsonResponse({"error": "No data found for the provided unique_id"}, status=404)
        return JsonResponse(data)

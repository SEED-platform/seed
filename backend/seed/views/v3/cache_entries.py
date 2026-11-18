"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.lib.superperms.orgs.permissions import get_org_id
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper, EmptySerializer
from seed.utils.cache import get_task_result, is_task_result_id


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
        org_id = int(get_org_id(request))
        not_found = JsonResponse({"error": "No data found for the provided unique_id"}, status=404)
        # Only the authorized organization's task results (see `new_task_result_id`, used by `start_export` and
        # `mapping_results`) can be retrieved, since other cache entries may hold other organizations' data or credentials
        if not is_task_result_id(unique_id, org_id):
            return not_found
        data, result_ali_id = get_task_result(unique_id)
        if not data:
            return not_found

        # A task's result is limited to the inventory of the access level instance of the user who started it, so only
        # users of that access level instance or one of its ancestors can retrieve it. Results without an access level
        # instance are denied.
        result_ali = AccessLevelInstance.objects.filter(pk=result_ali_id, organization_id=org_id).first() if result_ali_id else None
        user_ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        if result_ali is None or not (user_ali == result_ali or result_ali.is_descendant_of(user_ali)):
            return not_found
        return JsonResponse(data)

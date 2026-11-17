"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
import re

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from seed.decorators import SEED_CACHE_PREFIX, ajax_request
from seed.lib.superperms.orgs.decorators import ALLOW_SUPER_USER_PERMS, requires_owner
from seed.lib.superperms.orgs.models import AccessLevelInstance, OrganizationUser
from seed.utils.api import api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.cache import get_cache, get_cache_raw, make_key

_log = logging.getLogger(__name__)

# The only fields returned for progress data without an organization (e.g., cached before progress data was tagged with
# one), since its other fields (e.g., messages, summaries, and stack traces) can describe the organization's data
UNTAGGED_PROGRESS_FIELDS = ("progress_key", "progress", "status", "func_name", "total")

# The org-wide tasks whose endpoints only require an owner (`requires_owner`), which includes owners of a parent
# organization with any membership in the organization: deleting the organization or a cycle, and importing its access
# levels (see `_can_read_progress`)
OWNER_TASK_FUNC_NAMES = {"delete_organization_and_inventory", "delete_organization_cycle", "save_raw_access_level_instances_data"}


def _is_progress_key(key):
    """Whether `key` was made by `get_prog_key`, i.e., is like '<cache key prefix>SEED:<func_name>:PROG:<unique_id>'"""
    return re.fullmatch(re.escape(make_key(SEED_CACHE_PREFIX.format(""))) + r"[^:]+:PROG:.+", key) is not None


def _can_read_progress(user, data):
    """
    Whether the user can read tagged progress data (see `ProgressData`): superusers (as in `has_perm`), and users of the
    task's organization whose access level instance is the task's or one of its ancestors (or any of its users, if the
    task is not limited to an access level instance)
    """
    if user.is_superuser and ALLOW_SUPER_USER_PERMS:
        return True

    org_id = data["organization_id"]
    # Ignore memberships whose access level instance belongs to another organization (as in `has_perm`)
    org_user = (
        OrganizationUser.objects.filter(user=user, organization_id=org_id, access_level_instance__organization_id=org_id)
        .select_related("access_level_instance")
        .first()
    )
    if org_user is None:
        return False

    task_ali_id = data.get("access_level_instance_id")
    if task_ali_id is None:
        return True
    # nested-set bounds overlap between organizations, so the task's access level instance must be in the organization
    task_ali = AccessLevelInstance.objects.filter(pk=task_ali_id, organization_id=org_id).first()
    if task_ali is None:
        return False
    user_ali = org_user.access_level_instance
    if task_ali == user_ali or task_ali.is_descendant_of(user_ali):
        return True
    # Owners of a parent organization can start these org-wide tasks from any of a sub-organization's access level
    # instances (see `requires_owner`), so they can read their progress, but not that of its root's other tasks (e.g.,
    # imports and analyses)
    return task_ali.is_root() and data.get("func_name") in OWNER_TASK_FUNC_NAMES and requires_owner(org_user)


class ProgressViewSet(viewsets.ViewSet):
    raise_exception = True

    @extend_schema(
        parameters=[AutoSchemaHelper.path_string_field("id", "The progress key of the task")],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "status_message": "string",
                    "progress": "number",
                    "progress_key": "string",
                    "func_name": "string",
                    "message": "string",
                    "stacktrace": "string",
                    "summary": "object",
                    "total": "integer",
                    "organization_id": "integer",
                    "access_level_instance_id": "integer",
                },
                description="The task's progress data (which also includes its `unique_id`), with the organization and "
                "access level instance of the data that the task handles. Only superusers, and users of that "
                "organization whose access level instance is the task's or one of its ancestors, can read it. Unknown "
                'progress keys, and those of tasks that the user cannot read, return a "waiting" status with 0 '
                "progress. Progress data cached without an organization only includes `progress_key`, `progress`, "
                "`status`, `func_name`, and `total`.",
            )
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
        ]
    )
    def retrieve(self, request, pk):
        """
        Get the progress (percent complete) for a task.

        Returns::
            {
                'progress_key': The same progress key,
                'progress': Percent completion
            }
        """
        progress_key = pk
        # Unknown and unreadable keys get the same response so that it does not reveal which tasks exist
        waiting = JsonResponse({"progress_key": progress_key, "progress": 0, "status": "waiting"})

        # Other cache entries (e.g., mapping results) can hold organization data and must not be readable here
        if not _is_progress_key(progress_key):
            return waiting

        # Read it without refreshing its timeout (as `get_cache` does), so that users who cannot read it cannot keep it
        # cached
        data = get_cache_raw(progress_key)
        if not isinstance(data, dict):
            return waiting

        if data.get("organization_id") is None:
            # e.g., a task started before progress data was tagged; polling still keeps it cached while it runs
            data = get_cache(progress_key)
            return JsonResponse({field: data[field] for field in UNTAGGED_PROGRESS_FIELDS if field in data})

        if not _can_read_progress(request.user, data):
            return waiting

        return JsonResponse(get_cache(progress_key))

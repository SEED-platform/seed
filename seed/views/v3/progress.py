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
from seed.utils.api import api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.cache import get_cache, make_key

_log = logging.getLogger(__name__)


def _is_progress_key(key):
    """Whether `key` was made by `get_prog_key`, i.e., is like '<cache key prefix>SEED:<func_name>:PROG:<unique_id>'"""
    return re.fullmatch(re.escape(make_key(SEED_CACHE_PREFIX.format(""))) + r"[^:]+:PROG:.+", key) is not None


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
                },
                description="The task's progress data (which also includes its `unique_id`). "
                'Unknown progress keys return a "waiting" status with 0 progress',
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
        # Other cache entries (e.g., mapping results) can hold organization data and must not be readable here
        if _is_progress_key(progress_key) and get_cache(progress_key):
            return JsonResponse(get_cache(progress_key))
        else:
            return JsonResponse({"progress_key": progress_key, "progress": 0, "status": "waiting"})

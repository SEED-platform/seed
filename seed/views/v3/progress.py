from django.http import JsonResponse
from rest_framework import viewsets

from seed.decorators import ajax_request_class
from seed.utils.api import api_endpoint_class
from seed.utils.cache import get_cache

import logging
_log = logging.getLogger(__name__)


class ProgressViewSet(viewsets.ViewSet):
    raise_exception = True

    @api_endpoint_class
    @ajax_request_class
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
        if get_cache(progress_key):
            return JsonResponse(get_cache(progress_key))
        else:
            return JsonResponse({
                'progress_key': progress_key,
                'progress': 0,
                'status': 'waiting'
            })

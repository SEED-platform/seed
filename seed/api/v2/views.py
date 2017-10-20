from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication

from seed.authentication import SEEDAuthentication
from seed.decorators import ajax_request_class
from seed.utils.api import api_endpoint_class
from seed.utils.cache import get_cache


class ProgressViewSetV2(viewsets.ViewSet):
    raise_exception = True
    authentication_classes = (SessionAuthentication, SEEDAuthentication)

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
        # progress_key = request.data.get('progress_key')

        progress_key = pk
        if get_cache(progress_key):
            return JsonResponse(get_cache(progress_key))
        else:
            return JsonResponse({
                'progress_key': progress_key,
                'progress': 0,
                'status': 'waiting'
            })

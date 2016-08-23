

from rest_framework.reverse import reverse
from django.http import HttpResponse
from rest_framework import viewsets
import json


class TestReverseViewSet(viewsets.ViewSet):
    raise_exception = True

    def list(self, request):
        """
        Test a reverse call easily
        ---
        parameters:
            - name: reverse_string
              description: The string to test a reverse on
              type: string
              required: true
              paramType: query
        """
        reverse_string = request.query_params.get('reverse_string', None)
        reversed_url = reverse(reverse_string)
        return HttpResponse(json.dumps({reverse_string: reversed_url}))

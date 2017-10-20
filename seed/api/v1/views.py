from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication

from seed.authentication import SEEDAuthentication
from seed.decorators import ajax_request_class, require_organization_id_class
from seed.utils.api import api_endpoint_class
from seed.utils.buildings import (
    get_columns as utils_get_columns,
)


class ColumnViewSetV1(viewsets.ViewSet):
    raise_exception = True
    authentication_classes = (SessionAuthentication, SEEDAuthentication)

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    def list(self, request):
        """
        Returns a JSON list of columns a user can select as his/her default

        Requires the organization_id as a query parameter.

        This was formally /get_columns
        """
        all_fields = request.query_params.get('all_fields', '')
        all_fields = True if all_fields.lower() == 'true' else False
        return JsonResponse(utils_get_columns(request.query_params['organization_id'], all_fields))

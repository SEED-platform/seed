# !/usr/bin/env python
# encoding: utf-8
#
# :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
# :author

from rest_framework.reverse import reverse
from django.http import HttpResponse
from rest_framework import viewsets
import json

from seed.decorators import ajax_request
from rest_framework.decorators import action


class TestReverseViewSet(viewsets.ViewSet):
    raise_exception = True

    @action(detail=False, methods=['GET'])
    def no_arg_reverse(self, request):
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

    @action(detail=False, methods=['GET'])
    def try_coded_reverse(self, request):
        """
        Tries to reverse a string that is hardcoded in this view
        """
        i = dict()

        # try one from the main SEED app, which appears in the url as "/app/whatever", but it is namespaced to "seed"
        # i['seed:get_column_mapping_suggestions'] = reverse('seed:get_column_mapping_suggestions')

        # now try the same column mapping thing from API v2
        i['apiv2:data_files-mapping-suggestions'] = reverse('api:v2:data_files-mapping-suggestions', args=[1])

        # try one from the original /api url path, which is pretty much just get_api_schema
        i['api:get_api_schema'] = reverse('api:get_api_schema')

        # try the test one that includes a path argument
        i['apiv2:testviewarg'] = reverse('api:v2:testviewarg', args=[1])

        # try a class-based, router-generated view
        i['apiv2:datasets-list'] = reverse('api:v2:datasets-list')

        # report it out prettified
        return HttpResponse(json.dumps(i, indent=4, sort_keys=True))

    @action(detail=False, methods=['GET'])
    def one_arg_reverse(self, request):
        """
        Test a one arg reverse call easily
        ---
        parameters:
            - name: reverse_string
              description: The string to test a reverse on
              type: string
              required: true
              paramType: query
            - name: argument
              description: the single argument to pass in to try to reverse on
              type: string
              required: true
              paramType: query
        """
        reverse_string = request.query_params.get('reverse_string', None)
        argument = request.query_params.get('argument', None)
        reversed_url = reverse(reverse_string, args=[argument])
        return HttpResponse(json.dumps({reverse_string: reversed_url}))

    @action(detail=False, methods=['GET'])
    def show_file_type(self, request):
        """
        Show how to use a multipart file variable type
        ---
        parameters:
            - name: file
              type: file
        consumes:
            - application/json
            - multipart/form-data
        """
        return HttpResponse("Hello, world")


@ajax_request
def test_view_with_arg(request, pk=None):
    return {'value of pk': pk}


# !/usr/bin/env python
# encoding: utf-8
"""

:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""
from collections import OrderedDict
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ResultsListPagination(PageNumberPagination):
    page_size_query_param = 'per_page'

    def get_paginated_response(self, data):
        page_num = self.page.number

        return Response(OrderedDict([
            ('page', page_num),
            ('start', self.page.start_index()),
            ('end', self.page.end_index()),
            ('num_pages', self.page.paginator.num_pages),
            ('has_next', self.page.has_next()),
            ('has_previous', self.page.has_previous()),
            ('total', self.page.paginator.count),
            ('results', data)
        ]))

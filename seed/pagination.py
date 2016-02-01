# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import pagination
from rest_framework import response


class FakePaginiation(pagination.PageNumberPagination):
    """
    DRF Paginator class that presents results in the same format as
    `PageNumberPagination` but always includes all results on the first page.
    """
    def get_paginated_response(self, data):
        return response.Response({
            "next": None,
            "previous": None,
            "count": len(data),
            "results": data,
        })

    def paginate_queryset(self, queryset, request, view=None):
        return queryset

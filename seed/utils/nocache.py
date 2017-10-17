# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.utils.cache import add_never_cache_headers


class DisableClientSideCachingMiddleware(object):
    def process_response(self, request, response):
        add_never_cache_headers(response)
        return response

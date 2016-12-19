# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Paul Munday <paul@paulmunday.net>

This provides a custom JSON rendering class for SEED.

Currently SEED API endpoints return json in the format:
{'status': 'success', 'thing': {'attr': 'value'}}

which means ViewSet etc methods have to be overridden to provide the correct
format.

Use of the custom class(es) will generate the correct format, setting 'status'
based on the HTTP status code from the response, obviating the need to
override View(Set) methods unnecessarily, if e.g. ModelViewSet is used.
"""
from rest_framework import status
from rest_framework.renderers import JSONRenderer


class SEEDJSONRenderer(JSONRenderer):
    """
    Custom JSON Renderer.

    returns results in the format {'status': 'success', 'data': data}

    if self.data_name is set on the view its will be used in place of data
    as a key.
    """
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render 'data' into JSON in SEED Format.
        """
        data_name = 'data'
        view = renderer_context.get('view')
        data_name = getattr(view, 'data_name', data_name)
        response = renderer_context.get('response')
        status_type = 'error'
        if status.is_success(response.status_code):
            status_type = 'success'
        data = {'status': status_type, data_name: data}
        return super(SEEDJSONRenderer, self).render(
            data,
            accepted_media_type=accepted_media_type,
            renderer_context=renderer_context
        )

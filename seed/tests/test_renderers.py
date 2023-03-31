#!/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author Fable Turas <fable@raintechpdx.com>
"""
import json

# Imports from Third Party Modules
import mock
# Imports from Django
from django.test import TestCase
from django.views.generic import View

# Local Imports
from seed.renderers import SEEDJSONRenderer

# Constants

# Data Structure Definitions

# Private Functions

# Public Classes and Functions


class TestSEEDJSONRenderer(TestCase):

    def setUp(self):
        self.fake_renderer = SEEDJSONRenderer()
        self.fake_response = mock.MagicMock()
        self.fake_view = View()
        self.fake_context = {
            'view': self.fake_view,
            'response': self.fake_response
        }

    def test_render(self):
        """Test SEEDJSONRender render method"""
        # success
        fake_data = {'fake': 'data'}
        self.fake_response.status_code = 200
        result = json.loads(self.fake_renderer.render(
            fake_data, renderer_context=self.fake_context
        ))
        self.assertIn('status', result.keys())
        self.assertIn('data', result.keys())
        self.assertEqual(result['status'], 'success')

        # success with data_name in view
        data_name = 'cycles'
        self.fake_view.data_name = data_name
        result = json.loads(self.fake_renderer.render(
            fake_data, renderer_context=self.fake_context
        ))
        self.assertNotIn('data', result.keys())
        self.assertIn(data_name, result.keys())

        # success with pagination
        fake_data_paginated = {
            "next": None,
            "previous": None,
            "results": fake_data,
        }
        result = json.loads(self.fake_renderer.render(
            fake_data_paginated, renderer_context=self.fake_context
        ))
        self.assertIn('pagination', result.keys())

        # error
        self.fake_response.status_code = 400
        result = json.loads(self.fake_renderer.render(
            fake_data, renderer_context=self.fake_context
        ))
        self.assertIn('status', result.keys())
        self.assertIn('message', result.keys())
        self.assertEqual(result['status'], 'error')

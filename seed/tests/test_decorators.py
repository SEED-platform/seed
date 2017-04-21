# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.http import HttpResponse
from django.test import TestCase, RequestFactory
from rest_framework.test import APIRequestFactory

from seed import decorators
from seed.utils.cache import make_key, get_cache, get_lock, increment_cache, \
    clear_cache


class TestException(Exception):
    pass


class TestDecorators(TestCase):
    """Tests for locking tasks and reporting progress."""

    locked = 1
    unlocked = 0
    pk = 34  # Arbitrary PK value to test with.

    def setUp(self):
        clear_cache()

    # Tests for decorators utility functions

    def test_get_prog_key(self):
        """We format our cache key properly."""
        expected = make_key('SEED:fun_func:PROG:' + str(self.pk))
        self.assertEqual(decorators.get_prog_key('fun_func', self.pk),
                         expected)

    def test_increment_cache(self):
        """Sum our progress by increments properly."""
        expected = 25.0
        test_key = make_key('increment_test')
        increment = 25.0
        # Fresh increment, this initializes the value.
        increment_cache(test_key, increment)
        self.assertEqual(float(get_cache(test_key)['progress']), expected)

        # Increment an existing key
        increment_cache(test_key, increment)
        expected = 50.0
        self.assertEqual(float(get_cache(test_key)['progress']), expected)

        # This should put us well over 100.0 in incrementation w/o bounds check.
        for i in range(10):
            increment_cache(test_key, increment)

        expected = 100.0
        self.assertEqual(float(get_cache(test_key)['progress']), expected)

    # Tests for decorators themselves.

    def test_locking(self):
        """Make sure we indicate we're locked if and only if we're inside the function."""
        key = decorators._get_lock_key('fake_func', self.pk)
        self.assertEqual(int(get_lock(key)), self.unlocked)

        @decorators.lock_and_track
        def fake_func(import_file_pk):
            self.assertEqual(int(get_lock(key)), self.locked)

        fake_func(self.pk)

        self.assertEqual(int(get_lock(key)), self.unlocked)

    def test_locking_w_exception(self):
        """Make sure we release our lock if we've had an exception."""
        key = decorators._get_lock_key('fake_func', self.pk)

        @decorators.lock_and_track
        def fake_func(import_file_pk):
            self.assertEqual(int(get_lock(key)), self.locked)
            raise TestException('Test exception!')

        self.assertRaises(TestException, fake_func, self.pk)
        # Even though execution failed part way through a call, we unlock.
        self.assertEqual(int(get_lock(key)), self.unlocked)

    def test_progress(self):
        """When a task finishes, it increments the progress counter properly."""
        increment = expected = 25.0
        key = decorators.get_prog_key('fake_func', self.pk)
        self.assertEqual(float(get_cache(key, 0.0)['progress']), 0.0)

        @decorators.lock_and_track
        def fake_func(import_file_pk):
            increment_cache(key, increment)

        fake_func(self.pk)

        self.assertEqual(float(get_cache(key, 0.0)['progress']), expected)


class RequireOrganizationIDTests(TestCase):

    def setUp(self):
        @decorators.require_organization_id
        def test_view(request):
            return HttpResponse()

        self.test_view = test_view

    def test_require_organization_id_success_string(self):
        request = RequestFactory().get('', {'organization_id': '1'})
        response = self.test_view(request)
        self.assertEqual(200, response.status_code)

    def test_require_organization_id_success_integer(self):
        request = RequestFactory().get('', {'organization_id': '1'})
        response = self.test_view(request)
        self.assertEqual(200, response.status_code)

    def test_require_organization_id_fail_no_key(self):
        request = RequestFactory().get('')
        response = self.test_view(request)
        self.assertEqual(400, response.status_code)
        j = json.loads(response.content)
        self.assertEqual(j['status'], 'error')
        self.assertEqual(j['message'],
                         'Invalid organization_id: either blank or not an integer')

    def test_require_organization_id_fail_not_numeric(self):
        request = RequestFactory().get('', {'organization_id': 'invalid'})
        response = self.test_view(request)
        self.assertEqual(400, response.status_code)
        j = json.loads(response.content)
        self.assertEqual(j['status'], 'error')
        self.assertEqual(j['message'],
                         'Invalid organization_id: either blank or not an integer')


class ClassDecoratorTests(TestCase):

    def test_ajax_request_class_dict(self):
        request = RequestFactory().get('')

        @decorators.ajax_request_class
        def func(mock_self, request):
            return {'success': True, 'key': 'val'}

        result = func(True, request)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result['content-type'], 'application/json')
        self.assertEqual(
            json.loads(result.content), {"success": True, "key": "val"}
        )

    def test_ajax_request_class_dict_status_error(self):
        request = RequestFactory().get('')

        @decorators.ajax_request_class
        def func(mock_self, request):
            return {'status': 'error', 'error': 'error'}

        result = func(True, request)
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result['content-type'], 'application/json')
        self.assertEqual(
            json.loads(result.content), {"status": "error", "error": "error"}
        )

    def test_ajax_request_class_dict_status_false(self):
        request = RequestFactory().get('')

        @decorators.ajax_request_class
        def func(mock_self, request):
            return {'success': False, 'error': 'error'}

        result = func(True, request)
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result['content-type'], 'application/json')
        self.assertEqual(
            json.loads(result.content), {"success": False, "error": "error"}
        )

    def test_require_organization_id_class_org_id(self):
        request = APIRequestFactory().get('', data={'organization_id': 1})
        request.query_params = request.GET

        @decorators.require_organization_id_class
        def func(mock_self, request):
            return HttpResponse()

        result = func(True, request)
        self.assertEqual(result.status_code, 200)

    def test_require_organization_id_class_no_org_id(self):
        request = APIRequestFactory().get('', data={})
        request.query_params = request.GET

        @decorators.require_organization_id_class
        def func(mock_self, request):
            return HttpResponse()

        result = func(True, request)
        self.assertEqual(result.status_code, 400)
        self.assertEqual(
            result.content,
            'Valid organization_id is required in the query parameters.'
        )

    def test_require_organization_id_class_org_id_not_int(self):
        request = APIRequestFactory().get('', data={'organization_id': 'bad'})
        request.query_params = request.GET

        @decorators.require_organization_id_class
        def func(mock_self, request):
            return {'key': 'val'}

        result = func(True, request)
        self.assertEqual(result.status_code, 400)
        self.assertEqual(
            result.content,
            'Invalid organization_id in the query parameters, must be integer'
        )

    def test_ajax_request_class_format_type(self):
        request = RequestFactory().get('')
        request.META['HTTP_ACCEPT'] = 'text/json'

        @decorators.ajax_request_class
        def func(mock_self, request):
            return {'success': True, 'key': 'val'}

        result = func(True, request)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result['content-type'], 'text/json')
        self.assertEqual(
            json.loads(result.content), {"success": True, "key": "val"}
        )

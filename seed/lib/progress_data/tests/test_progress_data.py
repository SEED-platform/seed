# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from django.test import TestCase

from seed.lib.progress_data.progress_data import ProgressData

logger = logging.getLogger(__name__)


class TestProgressData(TestCase):
    """Tests that our logic for constructing cleaners works."""

    def setUp(self):
        pass

    def test_create_progress(self):
        pd = ProgressData(func_name='test_func', unique_id='abc123')

        self.assertEqual(pd.key, ':1:SEED:test_func:PROG:abc123')

        data_eql = {
            'status': 'not-started',
            'status_message': '',
            'summary': None,
            'stacktrace': None,
            'func_name': 'test_func',
            'progress_key': ':1:SEED:test_func:PROG:abc123',
            'progress': 0,
            'message': None,
            'total': None,
            'unique_id': 'abc123',
        }
        self.assertEqual(pd.data['status'], 'not-started')
        self.assertDictEqual(pd.data, data_eql)
        self.assertEqual(pd.total, None)

    def test_total_progress(self):
        pd = ProgressData(func_name='test_func_2', unique_id='def456')
        pd.total = 10
        self.assertEqual(pd.increment_value(), 10)

    def test_init_by_data(self):
        pd = ProgressData(func_name='test_func_3', unique_id='ghi789')
        pd.total = 100
        self.assertEqual(pd.key, ':1:SEED:test_func_3:PROG:ghi789')

        pd2 = ProgressData.from_key(pd.key)
        self.assertDictEqual(pd.data, pd2.data)

    def test_key_missing(self):
        with self.assertRaises(Exception) as exc:
            ProgressData.from_key('some_random_key')
        self.assertEqual(str(exc.exception), 'Could not find key some_random_key in cache')

    def test_delete_cache(self):
        pd = ProgressData(func_name='test_func_4', unique_id='1q2w3e')
        pd.total = 525600
        pd.data['status'] = 'doing-something'
        pd.save()

        self.assertEqual(pd.result()['total'], 525600)
        self.assertEqual(pd.data['status'], 'doing-something')
        self.assertEqual(pd.delete()['total'], None)

    def test_status_message(self):
        pd = ProgressData(func_name='test_func_5', unique_id='plokij')
        pd.total = 42
        pd.step('Stepping')

        self.assertEqual(pd.result()['total'], 42)
        self.assertEqual(pd.result()['status_message'], 'Stepping')

        # if we call step again, then the status message should not change
        pd.step()
        self.assertEqual(pd.result()['status_message'], 'Stepping')

        # Now passing in empty string will reset
        pd.step('')
        self.assertEqual(pd.result()['status_message'], '')

    def test_summary(self):
        pd = ProgressData(func_name='test_func_6', unique_id='pokemon')
        self.assertIsNone(pd.summary())

        new_summary = {"Values": ["As", "A", "List"]}
        pd.update_summary(new_summary)
        self.assertEqual(pd.summary(), new_summary)

        pd.step(new_summary=4815162342)
        self.assertEqual(pd.summary(), 4815162342)

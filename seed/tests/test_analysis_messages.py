# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
import logging

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.models import AnalysisMessage
from seed.test_helpers.fake import (
    FakeAnalysisFactory,
    FakeAnalysisPropertyViewFactory,
)
from seed.utils.organizations import create_organization


class TestAnalysisMessage(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Test',
            'last_name': 'User',
        }
        self.user = User.objects.create_user(**user_details)
        self.org, _, _ = create_organization(self.user)
        self.analysis = (
            FakeAnalysisFactory(organization=self.org, user=self.user)
            .get_analysis()
        )
        self.analysis_property_view = (
            FakeAnalysisPropertyViewFactory(organization=self.org, user=self.user)
            .get_analysis_property_view(analysis=self.analysis)
        )

    def test_log_and_create_logs_messages_and_creates_analysis_message(self):
        # Setup
        logger = logging.getLogger('test-logger')
        user_message = 'Message to the user'
        debug_message = 'This error was intentional'
        analysis_id = self.analysis.id
        analysis_property_view_id = self.analysis_property_view.id
        exception = Exception('My special exception')

        # Act
        with self.assertLogs(logger) as cm:
            AnalysisMessage.log_and_create(
                logger,
                AnalysisMessage.ERROR,
                user_message=user_message,
                debug_message=debug_message,
                analysis_id=analysis_id,
                analysis_property_view_id=analysis_property_view_id,
                exception=exception,
            )

        # Assert
        self.assertEqual(1, len(cm.output))

        level, logger_name, message = cm.output[0].split(':', 2)
        self.assertEqual('ERROR', level)
        self.assertEqual('test-logger', logger_name)

        parsed_message = json.loads(message)
        expected_message = {
            'analysis_id': analysis_id,
            'analysis_property_view': analysis_property_view_id,
            'user_message': user_message,
            'debug_message': debug_message,
            'exception': repr(exception),
        }
        self.assertDictEqual(expected_message, parsed_message)

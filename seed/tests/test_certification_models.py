# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Paul Munday <paul@paulmunday.net>
"""
# pylint:disable=no-name-in-module
import datetime

from django.core.exceptions import ValidationError

from seed.landing.models import SEEDUser as User
from seed.models import GreenAssessment
from seed.test_helpers.fake import (
    FakeGreenAssessmentFactory,
    FakeGreenAssessmentPropertyFactory,
    FakeGreenAssessmentURLFactory,
)
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization


class GreenAssessmentTests(DeleteModelsTestCase):
    """Tests for certification/Green Assessment models and methods"""

    # pylint: disable=too-many-instance-attributes

    def setUp(self):
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details)
        self.org, _, _ = create_organization(self.user)
        self.assessment_factory = FakeGreenAssessmentFactory(
            organization=self.org
        )
        self.green_assessment = self.assessment_factory.get_green_assessment(
            name="Green Test Score", award_body="Green TS Inc",
            recognition_type=GreenAssessment.SCORE,
            validity_duration=(365 * 5)
        )
        self.url_factory = FakeGreenAssessmentURLFactory()
        self.gap_factory = FakeGreenAssessmentPropertyFactory(
            organization=self.org, user=self.user
        )
        self.start_date = datetime.date.today() - datetime.timedelta(2 * 365)
        self.status_date = datetime.date.today() - datetime.timedelta(7)
        self.target_date = datetime.date.today() - datetime.timedelta(7)
        self.gap = self.gap_factory.get_green_assessment_property(
            assessment=self.green_assessment,
            organization=self.org, user=self.user, with_url=3,
            metric=5, date=self.start_date, status='Pending',
            source='Assessor', status_date=self.status_date,
            version='1', eligibility=True
        )
        self.urls = [url.url for url in self.gap.urls.all()]

    def test_unicode_magic_methods(self):
        """Test unicode repr methods"""
        expected = 'Green TS Inc, Green Test Score, Score'
        self.assertEqual(expected, str(self.green_assessment))

        expected = 'Green TS Inc, Green Test Score: 5'
        self.assertEqual(expected, str(self.gap))

    def test_gap_properties(self):
        """Test properties on GreenAssessmentProperty."""
        self.assertEqual('Green Test Score', self.gap.name)
        self.assertEqual('Green TS Inc', self.gap.body)
        self.assertEqual('SCR', self.gap.recognition_type)
        self.assertEqual('Score', self.gap.recognition_description)
        self.assertEqual(self.start_date.year, self.gap.year)
        self.assertEqual(
            self.green_assessment.organization, self.gap.organization
        )

    def test_url_properties(self):
        """Test properties on GreenAssessmentURL."""
        url = self.url_factory.get_url(property_assessment=self.gap)
        expected = self.gap.organization
        organization = url.organization
        self.assertEqual(expected, organization)

    def test_score(self):
        """Test score/rating/metric properties"""
        # test score/metric
        self.assertEqual(5, self.gap.score)
        self.assertEqual(5, self.gap.metric)
        self.assertIsInstance(self.gap.metric, int)
        self.assertIsInstance(self.gap.score, int)
        self.green_assessment.is_integer_score = False
        self.assertIsInstance(self.gap.metric, float)
        self.assertIsInstance(self.gap.score, float)
        self.gap.score = 4
        self.assertEqual(4.0, self.gap.score)
        with self.assertRaises(ValidationError) as conm:
            self.gap.rating = '5 stars'
        exception = conm.exception
        self.assertEqual(
            "['Green Test Score uses a metric (numeric score)']",
            str(exception)
        )
        self.gap.assessment.is_numeric_score = False
        self.gap.rating = '5 stars'
        self.assertEqual('5 stars', self.gap.rating)
        # must now return rating
        self.assertEqual('5 stars', self.gap.score)
        with self.assertRaises(ValidationError) as conm:
            self.gap.metric = 5
        exception = conm.exception
        self.assertEqual(
            "['Green Test Score uses a rating (non numeric score)']",
            str(exception)
        )

    def test_expiration(self):
        """Test expiration_date and is_valid properties"""
        expected_date = self.start_date + datetime.timedelta(365 * 5)
        self.assertEqual(expected_date, self.gap.expiration_date)
        self.assertTrue(self.gap.is_valid)

        # test setting/retrieving _expiration_date
        new_expiration = datetime.date.today() + datetime.timedelta(5 * 365)
        self.gap.expiration_date = new_expiration
        self.assertEqual(new_expiration, self.gap.expiration_date)
        self.assertTrue(self.gap.is_valid)

        # test past expiration date
        new_expiration = datetime.date.today() - datetime.timedelta(365)
        self.gap.expiration_date = new_expiration
        self.assertFalse(self.gap.is_valid)

    def test_to_bedes(self):
        """Test to_bedes_dict method."""
        expected = {
            'Assessment Program': 'Green Test Score',
            'Assessment Program Organization': 'Green TS Inc',
            'Assessment Recognition Type': 'Score',
            'Assessment Recognition Status': 'Pending',
            'Assessment Recognition Status Date': self.status_date,
            'Assessment Recognition Target Date': None,
            'Assessment Value': 5,
            'Assessment Version': '1',
            'Assessment Year': self.start_date.year,
            'Assessment Eligibility': True,
            'Assessment Level': None,
            'Assessment Program URL': self.urls,
        }
        self.assertDictEqual(expected, self.gap.to_bedes_dict())

    def test_to_reso(self):
        """Test to_reso_dict method."""
        expected = {
            'GreenBuildingVerificationType': 'Green Test Score',
            'GreenVerificationBody': 'Green TS Inc',
            'GreenVerificationDate': self.start_date,
            'GreenVerificationSource': 'Assessor',
            'GreenVerificationStatus': 'Pending',
            'GreenVerificationMetric': 5,
            'GreenVerificationRating': None,
            'GreenVerificationVersion': '1',
            'GreenVerificationYear': self.start_date.year,
            'GreenVerificationURL': self.urls,
        }
        self.assertDictEqual(expected, self.gap.to_reso_dict())

    def test_to_reso_sub_name(self):
        """Test to_reso_dict method with substitution."""
        expected = {
            'GreenBuildingVerificationType': 'Green Test Score',
            'GreenVerificationGreenTestScoreBody': 'Green TS Inc',
            'GreenVerificationGreenTestScoreDate': self.start_date,
            'GreenVerificationGreenTestScoreSource': 'Assessor',
            'GreenVerificationGreenTestScoreStatus': 'Pending',
            'GreenVerificationGreenTestScoreMetric': 5,
            'GreenVerificationGreenTestScoreRating': None,
            'GreenVerificationGreenTestScoreVersion': '1',
            'GreenVerificationGreenTestScoreYear': self.start_date.year,
            'GreenVerificationGreenTestScoreURL': self.urls,
        }
        self.assertDictEqual(expected, self.gap.to_reso_dict(sub_name=True))

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Paul Munday <paul@paulmunday.net>
"""
# pylint:disable=no-name-in-module
import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import (
    Organization,
    OrganizationUser,
)

from seed.models import (
    Cycle,
    GreenAssessment,
    GreenAssessmentProperty,
    GreenAssessmentURL,
    Property,
    PropertyState,
    PropertyView,
)

from seed.test_helpers.fake import (
    FakeGreenAssessmentFactory,
    FakeGreenAssessmentPropertyFactory, FakeGreenAssessmentURLFactory,
)


class GreenAssessmentTests(TestCase):
    """Tests for certification/Green Assesment models and methods"""
    # pylint: disable=too-many-instance-attributes

    def setUp(self):
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details)
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

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

    def tearDown(self):
        PropertyView.objects.all().delete()
        Cycle.objects.all().delete()
        Property.objects.all().delete()
        PropertyState.objects.all().delete()
        GreenAssessmentURL.objects.all().delete()
        GreenAssessmentProperty.objects.all().delete()
        GreenAssessment.objects.all().delete()
        self.user.delete()
        self.org.delete()

    def test_unicode_magic_methods(self):
        """Test unicode repr methods"""
        expected = u'Green TS Inc, Green Test Score, Score'
        self.assertEqual(expected, unicode(self.green_assessment))

        expected = u'Green TS Inc, Green Test Score: 5'
        self.assertEqual(expected, unicode(self.gap))

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
            "[u'Green Test Score uses a metric (numeric score)']",
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
            "[u'Green Test Score uses a rating (non numeric score)']",
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
            u'Assessment Program': 'Green Test Score',
            u'Assessment Program Organization': 'Green TS Inc',
            u'Assessment Recognition Type': u'Score',
            u'Assessment Recognition Status': 'Pending',
            u'Assessment Recognition Status Date': self.status_date,
            u'Assessment Recognition Target Date': None,
            u'Assessment Value': 5,
            u'Assessment Version': '1',
            u'Assessment Year': self.start_date.year,
            u'Assessment Eligibility': True,
            u'Assessment Level': None,
            u'Assessment Program URL': self.urls,
        }
        self.assertDictEqual(expected, self.gap.to_bedes_dict())

    def test_to_reso(self):
        """Test to_reso_dict method."""
        expected = {
            u'GreenBuildingVerificationType': 'Green Test Score',
            u'GreenVerificationBody': 'Green TS Inc',
            u'GreenVerificationSource': 'Assessor',
            u'GreenVerificationStatus': 'Pending',
            u'GreenVerificationMetric': 5,
            u'GreenVerificationRating': None,
            u'GreenVerificationVersion': '1',
            u'GreenVerificationYear': self.start_date.year,
            u'GreenVerificationURL': self.urls,
        }
        self.assertDictEqual(expected, self.gap.to_reso_dict())

    def test_to_reso_sub_name(self):
        """Test to_reso_dict method with substitution."""
        expected = {
            u'GreenBuildingVerificationType': 'Green Test Score',
            u'GreenVerificationGreenTestScoreBody': 'Green TS Inc',
            u'GreenVerificationGreenTestScoreSource': 'Assessor',
            u'GreenVerificationGreenTestScoreStatus': 'Pending',
            u'GreenVerificationGreenTestScoreMetric': 5,
            u'GreenVerificationGreenTestScoreRating': None,
            u'GreenVerificationGreenTestScoreVersion': '1',
            u'GreenVerificationGreenTestScoreYear': self.start_date.year,
            u'GreenVerificationGreenTestScoreURL': self.urls,
        }
        self.assertDictEqual(expected, self.gap.to_reso_dict(sub_name=True))

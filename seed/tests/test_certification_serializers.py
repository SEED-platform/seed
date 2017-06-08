#!/usr/bin/env python
# encoding: utf-8
"""
copyright (c) 2014 -2017 The Regents of the University of California,
through Lawrence Berkeley National Laboratory(subject to receipt of any
required approvals from the US. Department of Energy) and contributors.
All rights reserved
:author Paul Munday <paul@paulmunday.net>

Tests for serializers used by GreenAssessments/Energy Certifications
"""
import datetime
from collections import OrderedDict
import mock

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


from seed.serializers.certification import (
    GreenAssessmentURLField,
    PropertyViewField,
    ValidityDurationField,
    GreenAssessmentSerializer,
    GreenAssessmentPropertySerializer
)

from seed.test_helpers.fake import (
    FakePropertyViewFactory,
    FakeGreenAssessmentFactory,
    FakeGreenAssessmentPropertyFactory
)


class TestFields(TestCase):

    def get_date_string(self, dtobj):
        """Get YY-MM-DD string"""
        return "{}-{}-{}".format(dtobj.year, dtobj.month, dtobj.day)

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
        self.property_view_factory = FakePropertyViewFactory(
            organization=self.org, user=self.user
        )

    def tearDown(self):
        Property.objects.all().delete()
        PropertyState.objects.all().delete()
        PropertyView.objects.all().delete()
        GreenAssessment.objects.all().delete()
        Cycle.objects.all().delete()
        self.user.delete()
        self.org.delete()

    def test_url_field(self):
        """Test GreenAssessmentURLField"""
        field = GreenAssessmentURLField()
        url1 = mock.MagicMock()
        url1.url = 'http://example.com'
        url1.description = 'example.com'
        url2 = mock.MagicMock()
        url2.url = 'http://example.org'
        url2.description = 'example.org'
        mock_obj = mock.MagicMock()
        mock_obj.all.return_value = [url1, url2]
        expected = [
            ('http://example.com', 'example.com'),
            ('http://example.org', 'example.org')
        ]
        result = field.to_representation(mock_obj)
        self.assertEqual(expected, result)

    def test_property_view_field(self):
        """Test PropertyViewField"""
        property_view = self.property_view_factory.get_property_view()
        state = property_view.state
        cycle = OrderedDict((
            ('id', property_view.cycle.id),
            ('start', self.get_date_string(property_view.cycle.start)),
            ('end', self.get_date_string(property_view.cycle.end))
        ))
        expected = OrderedDict((
            ('id', property_view.pk),
            ('address_line_1', state.normalized_address.title()),
            ('address_line_2', state.address_line_2),
            ('city', state.city),
            ('state', state.state),
            ('postal_code', state.postal_code),
            ('property', property_view.property.id),
            ('cycle', cycle)
        ))

        field = PropertyViewField(read_only=True)
        result = field.to_representation(property_view)
        self.assertEqual(expected, result)

    def test_validity_duration_field_to_representation(self):
        """Test ValidityDurationField.to_representation()"""
        ga_factory = FakeGreenAssessmentFactory(organization=self.org)
        green_assessment = ga_factory.get_green_assessment(
            validity_duration=365
        )
        field = ValidityDurationField()
        result = field.to_representation(green_assessment.validity_duration)
        self.assertEqual(result, 365)

    def test_validity_duration_field_to_internal_value(self):
        """Test ValidityDurationField.to_internal_value()"""
        field = ValidityDurationField()
        result = field.to_internal_value(365)
        expected = datetime.timedelta(365)
        self.assertEqual(result, expected)
        result = field.to_internal_value('365')
        self.assertEqual(result, expected)
        result = field.to_internal_value(None)
        expected = None
        self.assertEqual(result, expected)
        self.assertRaises(ValidationError, field.to_internal_value, 1.54)
        self.assertRaises(ValidationError, field.to_internal_value, 'ten')
        self.assertRaises(ValidationError, field.to_internal_value, 0)
        self.assertRaises(ValidationError, field.to_internal_value, -10)


class TestGreenAssessmentPropertySerializer(TestCase):

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
        self.property_view_factory = FakePropertyViewFactory(
            organization=self.org, user=self.user
        )
        self.ga_factory = FakeGreenAssessmentFactory(organization=self.org)
        self.gap_factory = FakeGreenAssessmentPropertyFactory(
            organization=self.org, user=self.user
        )
        self.assessment = self.ga_factory.get_green_assessment()
        self.property_view = self.property_view_factory.get_property_view()
        self.data = {
            'source': 'test',
            'status': 'complete',
            'status_date': '2017-01-01',
            'metric': 5,
            'version': '0.1',
            'date': '2016-01-01',
            'eligibility': True,
            'assessment': self.assessment,
            'view': self.property_view,
        }
        self.urls = [
            ('http://example.com', 'example.com'),
            ('http://example.org', 'example.org')
        ]

    def tearDown(self):
        Property.objects.all().delete()
        PropertyState.objects.all().delete()
        PropertyView.objects.all().delete()
        GreenAssessmentURL.objects.all().delete()
        GreenAssessmentProperty.objects.all().delete()
        GreenAssessment.objects.all().delete()
        Cycle.objects.all().delete()
        self.user.delete()
        self.org.delete()

    @mock.patch('seed.serializers.certification.GreenAssessmentURL')
    def test_create(self, mock_url_model):
        """Test (overridden) create method."""
        serializer = GreenAssessmentPropertySerializer()
        data = self.data.copy()
        data['urls'] = self.urls
        instance = serializer.create(data)
        mock_url_model.objects.bulk_create.assert_called_with(
            [
                mock_url_model(
                    property_assessment=instance, url=url[0],
                    description=url[1]
                )
                for url in self.urls
            ]
        )

    @mock.patch('seed.serializers.certification.GreenAssessmentURL')
    def test_update(self, mock_url_model):
        """Test (overridden) update method."""
        data = self.data.copy()
        data['urls'] = self.urls[:1]
        gap = self.gap_factory.get_green_assessment_property(**data)
        serializer = GreenAssessmentPropertySerializer()
        data['urls'] = self.urls[1:]
        instance = serializer.update(gap, data)
        mock_url_model.objects.filter.assert_called_with(
            property_assessment=instance
        )
        mock_url_model.assert_called_with(
            url='http://example.org', property_assessment=gap,
            description='example.org'
        )

    def test_validate(self):
        """Test (overriden) validate method"""
        serializer = GreenAssessmentPropertySerializer()
        # add context
        mock_request = mock.MagicMock()
        mock_request.user = self.user
        serializer.context = {'request': mock_request}

        # assert raises error if rating and metric supplied
        data = self.data.copy()
        data['rating'] = 'Gold Star'
        with self.assertRaises(ValidationError) as conm:
            serializer.validate(data)
        exception = conm.exception
        expected = "[u'Only one of metric or rating can be supplied.']"
        self.assertEqual(expected, str(exception))

        # assert raises error if metric is expected
        del data['metric']
        data['rating'] = '5'
        with self.assertRaises(ValidationError) as conm:
            serializer.validate(data)
        exception = conm.exception
        expected = "[u'{} uses a metric (numeric score).']".format(
            self.assessment.name
        )
        self.assertEqual(expected, str(exception))

        # assert raises error if metric is of wrong type
        del data['rating']
        data['metric'] = '5 stars'
        with self.assertRaises(ValidationError) as conm:
            serializer.validate(data)
        exception = conm.exception
        expected = "[u'Metric must be a number.']"
        self.assertEqual(expected, str(exception))

        # assert raises error if rating expected
        self.assessment.is_numeric_score = False
        data['metric'] = 5
        with self.assertRaises(ValidationError) as conm:
            serializer.validate(data)
        exception = conm.exception
        expected = "[u'{} uses a rating (non-numeric score).']".format(
            self.assessment.name
        )

        # assert raises error if rating is of wrong type
        del data['metric']
        data['rating'] = 5
        with self.assertRaises(ValidationError) as conm:
            serializer.validate(data)
        exception = conm.exception
        expected = "[u'Rating must be a string.']"
        self.assertEqual(expected, str(exception))

        # assert converts ints to floats
        self.assessment.is_numeric_score = True
        del data['rating']
        data['metric'] = 5
        result = serializer.validate(data)
        self.assertEqual(result, data)

        # assert raises error if integer expected
        data['metric'] = 3.5
        with self.assertRaises(ValidationError) as conm:
            serializer.validate(data)
        exception = conm.exception
        expected = "[u'Metric must be an integer.']"
        self.assertEqual(expected, str(exception))

        # assert raises error if assessment missing
        del data['assessment']
        with self.assertRaises(ValidationError) as conm:
            serializer.validate(data)
        exception = conm.exception
        expected = "[u'Could not find assessment.']"
        self.assertEqual(expected, str(exception))


class TestGreenAssessmentSerializer(TestCase):

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
        self.ga_factory = FakeGreenAssessmentFactory(organization=self.org)
        assessment_data = {
            'name': 'Test',
            'award_body': 'Test Inc',
            'recognition_type': 'AWD',
            'description': 'Test Award',
            'is_numeric_score': True,
            'is_integer_score': True,
            'validity_duration': 365
        }
        self.assessment = self.ga_factory.get_green_assessment(
            **assessment_data
        )

    def tearDown(self):
        GreenAssessment.objects.all().delete()
        self.user.delete()
        self.org.delete()

    def test_serialization(self):
        """Test object serialization."""
        expected = {
            'id': self.assessment.id,
            'name': u'Test',
            'award_body': u'Test Inc',
            'recognition_type': u'AWD',
            'recognition_description': u'Award',
            'description': u'Test Award',
            'is_numeric_score': True,
            'is_integer_score': True,
            'validity_duration': 365
        }
        result = GreenAssessmentSerializer(self.assessment).data
        self.assertEqual(expected, result)

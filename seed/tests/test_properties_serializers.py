#!/usr/bin/env python
# encoding: utf-8
"""
copyright (c) 2014 -2016 The Regents of the University of California,
through Lawrence Berkeley National Laboratory(subject to receipt of any
required approvals from the US. Department of Energy) and contributors.
All rights reserved
:author Paul Munday <paul@paulmunday.net>

Tests for serializers used by GreenAssessments/Energy Certifications
"""
from collections import OrderedDict
import datetime
import json
import mock

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
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    StatusLabel,
    TaxLot,
    TaxLotProperty,
    TaxLotState,
    TaxLotView
)

from seed.models.auditlog import AUDIT_USER_EDIT

from seed.serializers.certification import (
    GreenAssessmentPropertyReadOnlySerializer
)

from seed.serializers.properties import (
    PropertyAuditLogReadOnlySerializer,
    PropertyListSerializer,
    PropertyMinimalSerializer,
    PropertyViewSerializer,
    PropertyViewListSerializer,
    PropertyViewAsStateSerializer,
    unflatten_values,
)

from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakeGreenAssessmentFactory,
    FakeGreenAssessmentPropertyFactory,
    FakePropertyAuditLogFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeStatusLabelFactory,
    FakeTaxLotPropertyFactory,
    FakeTaxLotStateFactory,
    FakeTaxLotViewFactory
)


class TestPropertySerializers(TestCase):

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
        self.audit_log_factory = FakePropertyAuditLogFactory(
            organization=self.org, user=self.user
        )
        self.property_factory = FakePropertyFactory(
            organization=self.org
        )
        self.property_state_factory = FakePropertyStateFactory(
            organization=self.org
        )
        self.property_view_factory = FakePropertyViewFactory(
            organization=self.org, user=self.user
        )
        self.ga_factory = FakeGreenAssessmentFactory(organization=self.org)
        self.gap_factory = FakeGreenAssessmentPropertyFactory(
            organization=self.org, user=self.user
        )
        self.label_factory = FakeStatusLabelFactory(
            organization=self.org
        )
        self.assessment = self.ga_factory.get_green_assessment()
        self.property_view = self.property_view_factory.get_property_view()
        self.gap_data = {
            'source': 'test',
            'status': 'complete',
            'status_date': datetime.date(2017, 0o1, 0o1),
            'metric': 5,
            'version': '0.1',
            'date': datetime.date(2016, 0o1, 0o1),
            'eligibility': True,
            'assessment': self.assessment,
            'view': self.property_view,
        }
        self.urls = ['http://example.com', 'http://example.org']

    def tearDown(self):
        Property.objects.all().delete()
        PropertyState.objects.all().delete()
        PropertyView.objects.all().delete()
        PropertyAuditLog.objects.all().delete()
        GreenAssessmentURL.objects.all().delete()
        GreenAssessmentProperty.objects.all().delete()
        GreenAssessment.objects.all().delete()
        StatusLabel.objects.all().delete()
        Cycle.objects.all().delete()
        self.user.delete()
        self.org.delete()

    def test_audit_log_serializer(self):
        """Test to_representation method."""

        # test with AUDIT_USER_CREATE
        audit_log = self.audit_log_factory.get_property_audit_log()
        result = PropertyAuditLogReadOnlySerializer(audit_log).data
        self.assertEqual(result['description'], 'test audit log')
        self.assertEqual(result['date_edited'], audit_log.created.ctime())
        self.assertEqual(result['source'], 'UserCreate')
        self.assertIsNone(result['changed_fields'])
        self.assertEqual(result['state']['city'], 'Boring')

        # test with AUDIT_USER_EDIT
        changed_fields = ['a', 'b', 'c']
        audit_log = self.audit_log_factory.get_property_audit_log(
            record_type=AUDIT_USER_EDIT, description=json.dumps(changed_fields)
        )
        result = PropertyAuditLogReadOnlySerializer(audit_log).data
        self.assertEqual(result['description'], 'User edit')
        self.assertEqual(result['source'], 'UserEdit')
        self.assertEqual(result['changed_fields'], changed_fields)

    def test_property_view_list_serializer(self):
        """Test to_representation method."""
        property_view_1 = self.property_view_factory.get_property_view()
        property_view_2 = self.property_view_factory.get_property_view()
        gap1_data = self.gap_data.copy()
        gap2_data = self.gap_data.copy()
        gap1_data['view'] = property_view_1
        gap2_data['view'] = property_view_2
        gap2_data['metric'] = 4
        self.gap_factory.get_green_assessment_property(**gap1_data)
        self.gap_factory.get_green_assessment_property(**gap2_data)
        serializer = PropertyViewListSerializer(
            child=PropertyViewSerializer()
        )
        result = serializer.to_representation(
            [property_view_1, property_view_2]
        )
        self.assertEqual(result[0]['cycle']['id'], property_view_1.cycle_id)
        self.assertEqual(result[1]['cycle']['id'], property_view_2.cycle_id)
        self.assertEqual(result[0]['state']['id'], property_view_1.state_id)
        self.assertEqual(result[1]['state']['id'], property_view_2.state_id)
        self.assertEqual(result[0]['certifications'][0]['score'], 5)
        self.assertEqual(result[1]['certifications'][0]['score'], 4)
        self.assertEqual(
            result[0]['certifications'][0]['assessment']['name'],
            self.assessment.name
        )
        self.assertEqual(
            result[1]['certifications'][0]['assessment']['name'],
            self.assessment.name
        )

        # with queryset
        serializer = PropertyViewListSerializer(
            child=PropertyViewSerializer()
        )
        queryset = PropertyView.objects.filter(
            id__in=[property_view_1.id, property_view_2.id]
        )
        result = serializer.to_representation(queryset)
        self.assertEqual(result[0]['cycle']['id'], property_view_1.cycle_id)
        self.assertEqual(result[1]['cycle']['id'], property_view_2.cycle_id)
        self.assertEqual(result[0]['state']['id'], property_view_1.state_id)
        self.assertEqual(result[1]['state']['id'], property_view_2.state_id)
        self.assertEqual(result[0]['certifications'][0]['score'], 5)
        self.assertEqual(result[1]['certifications'][0]['score'], 4)
        self.assertEqual(
            result[0]['certifications'][0]['assessment']['name'],
            self.assessment.name
        )
        self.assertEqual(
            result[1]['certifications'][0]['assessment']['name'],
            self.assessment.name
        )

    def test_property_list_serializer(self):
        """Test PropertyListSerializer.to_representation"""
        # TODO test to representation
        property1 = self.property_factory.get_property()
        property2 = self.property_factory.get_property()
        label1 = self.label_factory.get_statuslabel()
        label2 = self.label_factory.get_statuslabel()
        property1.labels.add(label1)
        property1.labels.add(label2)
        property2.labels.add(label2)

        expected = [
            OrderedDict([
                ('id', property1.id),
                ('campus', False),
                ('parent_property', None),
                ('labels', [label1.id, label2.id])
            ]),
            OrderedDict([
                ('id', property2.id),
                ('campus', False),
                ('parent_property', None),
                ('labels', [label2.id])
            ]),
        ]

        serializer = PropertyListSerializer(
            child=PropertyMinimalSerializer()
        )
        result = serializer.to_representation(
            [property1, property2]
        )
        self.assertEqual(expected, result)


class TestPropertyViewAsStateSerializers(TestCase):

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
        self.audit_log_factory = FakePropertyAuditLogFactory(
            organization=self.org, user=self.user
        )
        self.cycle_factory = FakeCycleFactory(
            organization=self.org, user=self.user
        )
        self.property_state_factory = FakePropertyStateFactory(
            organization=self.org
        )
        self.property_view_factory = FakePropertyViewFactory(
            organization=self.org, user=self.user
        )
        self.ga_factory = FakeGreenAssessmentFactory(organization=self.org)
        self.gap_factory = FakeGreenAssessmentPropertyFactory(
            organization=self.org, user=self.user
        )
        self.taxlot_property_factory = FakeTaxLotPropertyFactory(
            organization=self.org, user=self.user
        )
        self.taxlot_state_factory = FakeTaxLotStateFactory(
            organization=self.org
        )
        self.taxlot_view_factory = FakeTaxLotViewFactory(
            organization=self.org, user=self.user
        )
        self.assessment = self.ga_factory.get_green_assessment()
        self.cycle = self.cycle_factory.get_cycle()
        self.property_state = self.property_state_factory.get_property_state(self.org)
        self.property_view = self.property_view_factory.get_property_view(
            state=self.property_state, cycle=self.cycle
        )
        self.taxlot_state = self.taxlot_state_factory.get_taxlot_state()
        self.taxlot_view = self.taxlot_view_factory.get_taxlot_view(
            state=self.taxlot_state, cycle=self.cycle
        )
        self.audit_log = self.audit_log_factory.get_property_audit_log(
            state=self.property_state, view=self.property_view,
            record_type=AUDIT_USER_EDIT, description=json.dumps(['a', 'b'])
        )
        self.audit_log2 = self.audit_log_factory.get_property_audit_log(
            view=self.property_view
        )
        self.gap_data = {
            'source': 'test',
            'status': 'complete',
            'status_date': datetime.date(2017, 0o1, 0o1),
            'metric': 5,
            'version': '0.1',
            'date': datetime.date(2016, 0o1, 0o1),
            'eligibility': True,
            'assessment': self.assessment,
            'view': self.property_view,
        }
        self.urls = ['http://example.com', 'http://example.org']
        self.gap = self.gap_factory.get_green_assessment_property(
            **self.gap_data
        )
        self.serializer = PropertyViewAsStateSerializer(
            instance=self.property_view
        )

    def tearDown(self):
        TaxLot.objects.all().delete()
        TaxLotState.objects.all().delete()
        TaxLotView.objects.all().delete()
        TaxLotProperty.objects.all().delete()
        Property.objects.all().delete()
        PropertyState.objects.all().delete()
        PropertyView.objects.all().delete()
        PropertyAuditLog.objects.all().delete()
        GreenAssessmentURL.objects.all().delete()
        GreenAssessmentProperty.objects.all().delete()
        GreenAssessment.objects.all().delete()
        Cycle.objects.all().delete()
        self.user.delete()
        self.org.delete()

    def test_init(self):
        """Test __init__."""
        expected = PropertyAuditLogReadOnlySerializer(self.audit_log).data
        self.assertEqual(self.serializer.current, expected)

    def test_get_certifications(self):
        """Test get_certifications"""
        expected = [GreenAssessmentPropertyReadOnlySerializer(self.gap).data]
        self.assertEqual(
            self.serializer.get_certifications(self.property_view), expected
        )

    def test_get_changed_fields(self):
        """Test get_changed_fields"""
        expected = [u'a', u'b']
        self.assertEqual(
            self.serializer.get_changed_fields(None), expected
        )

    def test_get_date_edited(self):
        """Test get_date_edited"""
        expected = self.audit_log.created.ctime()
        self.assertEqual(
            self.serializer.get_date_edited(None), expected
        )

    def test_get_filename(self):
        """Test get_filename"""
        expected = self.audit_log.import_filename
        self.assertEqual(
            self.serializer.get_filename(None), expected
        )

    def test_get_history(self):
        """Test get_history"""
        obj = mock.MagicMock()
        obj.state = self.property_state
        expected = [PropertyAuditLogReadOnlySerializer(self.audit_log2).data]
        self.assertEqual(
            self.serializer.get_history(obj), expected
        )

    def test_get_source(self):
        """Test get_source"""
        expected = self.audit_log.get_record_type_display()
        self.assertEqual(
            self.serializer.get_source(None), expected
        )

    def test_get_taxlots(self):
        """Test get_taxlots"""
        self.taxlot_property_factory.get_taxlot_property(
            cycle=self.cycle, property_view=self.property_view,
            taxlot_view=self.taxlot_view
        )
        result = self.serializer.get_taxlots(self.property_view)
        self.assertEqual(result[0]['state']['id'], self.taxlot_state.id)

    @mock.patch('seed.serializers.properties.PropertyView')
    @mock.patch('seed.serializers.properties.PropertyStateWritableSerializer')
    def test_create(self, mock_serializer, mock_pview):
        """Test create"""
        mock_serializer.return_value.is_valid.return_value = True
        mock_serializer.return_value.save.return_value = 'mock_state'
        mock_property_view = mock.MagicMock()
        mock_pview.objects.create.return_value = mock_property_view
        data = {
            'org_id': 1,
            'cycle': 2,
            'state': {'test': 3},
            'property': 4
        }

        serializer = PropertyViewAsStateSerializer()
        serializer.create(data)
        mock_serializer.assert_called_with(
            data={'test': 3}
        )
        self.assertTrue(mock_serializer.return_value.save.called)
        mock_pview.objects.create.assert_called_with(
            state='mock_state', cycle_id=2, property_id=4, org_id=1
        )

    @mock.patch('seed.serializers.properties.PropertyStateWritableSerializer')
    def test_update_put(self, mock_serializer):
        """Test update with PUT"""
        mock_serializer.return_value.is_valid.return_value = True
        mock_serializer.return_value.save.return_value = 'mock_state'
        mock_property_view = mock.MagicMock()
        mock_request = mock.MagicMock()
        data = {
            'org_id': 1,
            'cycle': 2,
            'state': {'test': 3},
            'property': 4
        }

        serializer = PropertyViewAsStateSerializer()
        mock_request.METHOD = 'PUT'
        serializer.context = {'request': mock_request}
        serializer.update(mock_property_view, data)
        mock_serializer.assert_called_with(
            data={'test': 3}
        )
        self.assertTrue(mock_serializer.return_value.save.called)

    @mock.patch('seed.serializers.properties.PropertyStateWritableSerializer')
    def test_update_patch(self, mock_serializer):
        """Test update with PATCH"""
        mock_serializer.return_value.is_valid.return_value = True
        mock_serializer.return_value.save.return_value = 'mock_state'
        mock_property_view = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_request.method = 'PATCH'
        data = {
            'org_id': 1,
            'cycle': 2,
            'state': {'test': 3},
            'property': 4
        }
        serializer = PropertyViewAsStateSerializer()
        mock_property_view.state = 'pv_state'
        serializer.context = {'request': mock_request}
        serializer.update(mock_property_view, data)
        mock_serializer.assert_called_with(
            'pv_state',
            data={'test': 3}
        )
        self.assertTrue(mock_serializer.return_value.save.called)


class TestMisc(TestCase):
    """Miscellaneous tests."""

    def test_unflatten_values(self):
        """Test unflatten_values fucntion."""
        test_dict = {
            'a': 1, 'b': 2, 'sub_a': 3,
            'sub__a': 4, 'sub__b': 5,
            'bus__a': 6, 'bus__b': 7, 'bus__c': 9
        }
        expected = {
            'a': 1, 'b': 2, 'sub_a': 3,
            'sub': {'a': 4, 'b': 5},
            'bus': {'a': 6, 'b': 7, 'c': 9},
        }
        test_keys = ['bus', 'sub']
        result = unflatten_values(test_dict, test_keys)
        self.assertEqual(len(test_dict.keys()) - 3, len(result.keys()))
        self.assertEqual(len(expected.keys()), len(result.keys()))
        self.assertEqual(expected, result)
        self.assertRaises(AssertionError, unflatten_values, test_dict, ['a'])
        self.assertRaises(
            AssertionError, unflatten_values, test_dict, test_dict.keys()
        )
        self.assertRaises(
            AssertionError, unflatten_values, test_dict, ['a', 'bus', 'sub']
        )
        self.assertRaises(
            AssertionError, unflatten_values, test_dict, ['a', 'sub', 'foo']
        )

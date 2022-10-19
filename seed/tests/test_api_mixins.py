# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.
:author Paul Munday <paul@paulmunday.net>
:author Nicholas Long <nicholas.long@nrel.gov>
"""
from datetime import datetime

# pylint:disable=no-name-in-module
import mock
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.models import Column, PropertyView
from seed.test_helpers.fake import (
    FakeColumnListProfileFactory,
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory
)
from seed.utils.api import (
    OrgCreateMixin,
    OrgMixin,
    OrgQuerySetMixin,
    OrgUpdateMixin,
    OrgValidateMixin,
    OrgValidator,
    ProfileIdMixin,
    get_org_id_from_validator,
    rgetattr
)
from seed.utils.organizations import create_organization


class TestOrgMixin(TestCase):
    """Test OrgMixin -- provides get_organization_id method"""

    def setUp(self):
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details)
        self.org, self.org_user, _ = create_organization(self.user)

        class OrgMixinClass(OrgMixin):
            pass

        self.mixin_class = OrgMixinClass()

    def tearDown(self):
        self.user.delete()
        self.org.delete()
        self.org_user.delete()

    @mock.patch('seed.utils.api.get_user_org')
    @mock.patch('seed.utils.api.get_org_id')
    def test_get_organization(self, mock_get_org_id, mock_get_user_org):
        """test get_organization method"""
        mock_request = mock.MagicMock()
        mock_request.user = self.user

        # assert raises exception if org_id does not match user
        mock_get_org_id.return_value = self.org.id * 100
        self.assertRaises(
            PermissionDenied,
            self.mixin_class.get_organization,
            mock_request, True
        )

        # test first org id returned if not defined on request
        mock_get_org_id.return_value = None
        mock_get_user_org.return_value = self.org
        expected = self.org.id
        self.mixin_class._organization = None
        result = self.mixin_class.get_organization(mock_request)
        self.assertEqual(expected, result)

        # test org id returned if defined on request, and matches
        mock_get_org_id.return_value = self.org.id
        self.mixin_class._organization = None
        result = self.mixin_class.get_organization(mock_request)
        self.assertEqual(expected, result)

        # test org returned if return_obj = True
        mock_get_org_id.return_value = self.org.id
        self.mixin_class._organization = None
        result = self.mixin_class.get_organization(
            mock_request, return_obj=True
        )
        self.assertIsInstance(result, Organization)


class TestOrgCreateMixin(TestCase):
    """Test OrgCreateMixin -- provides perform_create  method"""

    def setUp(self):
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        mock_request = mock.MagicMock()
        mock_request.user = self.user

        class OrgCreateMixinClass(OrgCreateMixin):
            request = mock_request

        self.mixin_class = OrgCreateMixinClass()

    def tearDown(self):
        self.user.delete()
        self.org.delete()
        self.org_user.delete()

    @mock.patch('seed.utils.api.get_org_id')
    def test_get_perform_create(self, mock_get_org_id):
        """test perform_create method"""
        mock_serializer = mock.MagicMock()
        mock_get_org_id.return_value = self.org.id

        self.mixin_class.perform_create(mock_serializer)
        mock_serializer.save.assert_called_with(organization_id=self.org.id)


class TestOrgUpdateMixin(TestCase):
    """Test OrgUpdateMixin -- provides perform_update  method"""

    def setUp(self):
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        mock_request = mock.MagicMock()
        mock_request.user = self.user

        class OrgUpdateMixinClass(OrgUpdateMixin):
            request = mock_request

        self.mixin_class = OrgUpdateMixinClass()

    def tearDown(self):
        self.user.delete()
        self.org.delete()
        self.org_user.delete()

    @mock.patch('seed.utils.api.get_org_id')
    def test_get_perform_update(self, mock_get_org_id):
        """test perform_update method"""
        mock_serializer = mock.MagicMock()
        mock_get_org_id.return_value = self.org.id

        self.mixin_class.perform_update(mock_serializer)
        mock_serializer.save.assert_called_with(organization_id=self.org.id)


class TestOrgValidateMixin(TestCase):
    """Test OrgValidateMixin -- provides validate method for serializers"""

    def setUp(self):
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        self.org, self.org_user, _ = create_organization(self.user)
        mock_request = mock.MagicMock()
        mock_request.user = self.user
        self.org_validator = OrgValidator(
            key='foreign_key', field='organization_id'
        )

        class OrgValidateMixinClass(OrgValidateMixin):
            context = {'request': mock_request}
            org_validators = [self.org_validator]

        self.mixin_class = OrgValidateMixinClass()

    def tearDown(self):
        self.user.delete()
        self.org.delete()
        self.org_user.delete()

    def test_validate_org(self):
        """Test validate_org method."""
        # assert raises exception if organization_id is None
        mock_instance = mock.MagicMock()
        mock_instance.organization_id = None
        self.assertRaises(
            PermissionDenied,
            self.mixin_class.validate_org,
            mock_instance,
            self.user,
            self.org_validator
        )

        # assert raises exception if organization_id does not match
        mock_instance = mock.MagicMock()
        mock_instance.organization_id = self.org.id * 100
        self.assertRaises(
            PermissionDenied,
            self.mixin_class.validate_org,
            mock_instance,
            self.user,
            self.org_validator
        )

        # assert does raises exception if organization_id matches
        did_not_raise_exception = False
        mock_instance = mock.MagicMock()
        mock_instance.organization_id = self.org.id
        self.mixin_class.validate_org(
            mock_instance, self.user, self.org_validator
        )
        # only reached if above does not raise exception
        did_not_raise_exception = True
        self.assertTrue(did_not_raise_exception)

    def test_validate_raises_exception(self):
        """
        Test to ensure validate fails if org_validators is not set
        on the class usind this mixin.
        """

        class OrgValidateClass(OrgValidateMixin):
            pass

        my_class = OrgValidateClass()
        self.assertRaises(ValidationError, my_class.validate, {})

    def test_validate(self):
        """Test validate method"""
        # assert raises exception if organization_id is None
        mock_instance = mock.MagicMock()
        mock_instance.organization_id = None
        data = {'foreign_key': mock_instance}
        self.assertRaises(PermissionDenied, self.mixin_class.validate, data)

        # assert raises exception if organization_id does not match
        mock_instance = mock.MagicMock()
        mock_instance.organization_id = self.org.id * 100
        data = {'foreign_key': mock_instance}
        self.assertRaises(PermissionDenied, self.mixin_class.validate, data)

        # assert does not raises exception if organization_id matches
        did_not_raise_exception = False
        mock_instance = mock.MagicMock()
        mock_instance.organization_id = self.org.id
        data = {'foreign_key': mock_instance}
        self.mixin_class.validate(data)
        # only reached if above does not raise exception
        did_not_raise_exception = True
        self.assertTrue(did_not_raise_exception)


class TestOrgQuerySetMixin(TestCase):
    """Test OrgQuerySetMixin -- provides get_queryset method for viewsets"""

    def setUp(self):
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(email='test_user@demo.com', **user_details)
        self.org, self.org_user, _ = create_organization(self.user)

    def tearDown(self):
        self.user.delete()
        self.org.delete()
        self.org_user.delete()

    def test_get_queryset_exception(self):
        """Test get_queryset method raise exception is self.model not set"""
        # mock_model = mock.MagicMock()
        # mock_objects = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_request.user = self.user

        class OrgQuerySetMixinClass(OrgQuerySetMixin):
            request = mock_request

        mixin_class = OrgQuerySetMixinClass()
        self.assertRaises(AttributeError, mixin_class.get_queryset)

    @mock.patch('seed.utils.api.get_org_id')
    def test_get_queryset(self, mock_get_org_id):
        """Test get_queryset method"""
        mock_model = mock.MagicMock()

        mock_request = mock.MagicMock()
        mock_request.user = self.user
        mock_get_org_id.return_value = self.org.id

        class OrgQuerySetMixinClass(OrgQuerySetMixin):
            request = mock_request
            model = mock_model

        mixin_class = OrgQuerySetMixinClass()
        mixin_class.get_queryset()
        mock_model.objects.filter.assert_called_with(organization_id=self.org.id)


class TestProfileIdMixin(TestCase):
    """Test OrgMixin -- provides get_organization_id method"""

    def setUp(self):
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.column_list_factory = FakeColumnListProfileFactory(organization=self.org)
        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=timezone.get_current_timezone())
        )

        class ProfileIdMixInclass(ProfileIdMixin):
            pass

        self.mixin_class = ProfileIdMixInclass()

    def tearDown(self):
        PropertyView.objects.all().delete()
        self.user.delete()
        self.org.delete()
        self.org_user.delete()

    def test_get_profile_id(self):
        """test get_organization method"""
        state = self.property_state_factory.get_property_state(extra_data={"field_1": "value_1"})
        prprty = self.property_factory.get_property()
        PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )

        # save all the columns in the state to the database so we can setup column list settings
        Column.save_column_names(state)

        columns = self.mixin_class.get_show_columns(self.org.id, None)
        self.assertGreater(len(columns['fields']), 10)
        self.assertListEqual(columns['extra_data'], ['field_1'])

        columns = self.mixin_class.get_show_columns(self.org.id, -1)
        self.assertGreater(len(columns['fields']), 10)
        self.assertListEqual(columns['extra_data'], ['field_1'])

        columns = self.mixin_class.get_show_columns(self.org.id, 1000000)
        self.assertGreater(len(columns['fields']), 10)
        self.assertListEqual(columns['extra_data'], ['field_1'])

        # no extra data
        columnlistprofile = self.column_list_factory.get_columnlistprofile(
            columns=['address_line_1', 'site_eui']
        )
        columns = self.mixin_class.get_show_columns(self.org.id, columnlistprofile.id)
        self.assertListEqual(columns['fields'], ['extra_data', 'id', 'address_line_1', 'site_eui'])
        self.assertListEqual(columns['extra_data'], [])

        # with extra data
        columnlistprofile = self.column_list_factory.get_columnlistprofile(
            columns=['address_line_1', 'site_eui', 'field_1']
        )
        columns = self.mixin_class.get_show_columns(self.org.id, columnlistprofile.id)
        self.assertListEqual(columns['fields'], ['extra_data', 'id', 'address_line_1', 'site_eui'])
        self.assertListEqual(columns['extra_data'], ['field_1'])


class TestHelpers(TestCase):
    """Test misc helper funcs"""

    def test_rgetattr(self):
        """Test recursive getattr like thing"""
        # assert acts like get attr (minus being able to set a default)
        obj = type('X', (object,), dict(a=1))
        result = rgetattr(obj, ['a'])
        self.assertEqual(result, 1)

        # assert returns None if attr not set
        result = rgetattr(obj, ['b'])

        # test recursive get
        child = type('X', (object,), dict(a=7, b=2))
        obj = type('X', (object,), dict(a=child, b=3))
        result = rgetattr(obj, ['a', 'b'])
        self.assertEqual(result, 2)

        result = rgetattr(obj, ['a', 'a'])
        self.assertEqual(result, 7)

        result = rgetattr(obj, ['a', 'c'])
        self.assertEqual(result, None)

    def test_get_org_id_from_validator(self):
        """test get_org_id_from_validator"""
        child = type('X', (object,), dict(a=7, b=2))
        obj = type('X', (object,), dict(a=child, b=3))
        result = get_org_id_from_validator(obj, 'a__b')
        self.assertEqual(result, 2)

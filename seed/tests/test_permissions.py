# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Paul Munday <paul@paulmunday.net>
"""
# pylint:disable=no-name-in-module
import mock

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import (
    Organization,
    OrganizationUser,
    ROLE_OWNER,
    ROLE_MEMBER,
    ROLE_VIEWER,
)

from seed.lib.superperms.orgs.permissions import (
    get_org_or_id,
    get_org_id,
    get_user_org,
    SEEDOrgPermissions,
    SEEDPublicPermissions
)


class PermissionsFunctionsTests(TestCase):
    """Tests for Custom DRF Permissions util functions"""
    # pylint: disable=too-many-instance-attributes
    def setUp(self):
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        user2_details = {
            'username': 'test_user2@demo.com',
            'password': 'test_pass'
        }
        user3_details = {
            'username': 'test_user3@demo.com',
            'password': 'test_pass'
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details)
        self.user2 = User.objects.create_user(
            email='test_user2@demo.com', **user2_details)
        self.user3 = User.objects.create_user(
            email='test_user3@demo.com', **user3_details)

        self.org = Organization.objects.create()
        self.sub_org = Organization.objects.create(parent_org=self.org)
        self.sub_org2 = Organization.objects.create(parent_org=self.org)

        # user with more than one org, default_organization set
        self.org_user = OrganizationUser.objects.create(
            user=self.user, organization=self.org)
        self.sub_org_user = OrganizationUser.objects.create(
            user=self.user, organization=self.sub_org)
        self.user.default_organization = self.sub_org

        # user with no default, one parent, one sub org
        self.org_user2 = OrganizationUser.objects.create(
            user=self.user2, organization=self.org)
        self.sub_org_user2 = OrganizationUser.objects.create(
            user=self.user2, organization=self.sub_org)

        # user with all orgs of equal rank
        self.org_user3 = OrganizationUser.objects.create(
            user=self.user3, organization=self.sub_org)
        self.sub_org_user3 = OrganizationUser.objects.create(
            user=self.user3, organization=self.sub_org2)

    def tearDown(self):
        self.user.delete()
        self.user2.delete()
        self.user3.delete()
        self.org.delete()
        self.sub_org.delete()
        self.sub_org2.delete()
        self.org_user.delete()
        self.org_user2.delete()
        self.org_user3.delete()
        self.sub_org_user.delete()
        self.sub_org_user2.delete()
        self.sub_org_user3.delete()

    def test_org_or_id(self):
        """Test getting org or org id"""
        test_dict = {'organization': 1, 'organization_id': 2}
        result = get_org_or_id(test_dict)
        self.assertEqual(1, result)

        test_dict = {'organization_id': 2}
        result = get_org_or_id(test_dict)
        self.assertEqual(2, result)

    def test_get_org_id(self):
        """Test getting org id from request."""
        mock_request = mock.MagicMock()
        mock_request.query_params = {'organization': 1}
        result = get_org_id(mock_request)
        self.assertEqual(1, result)

        mock_request = mock.MagicMock()
        mock_request.query_params = {'organization': None}
        mock_request.data = {'organization': 2}
        result = get_org_id(mock_request)
        self.assertEqual(2, result)

        mock_request = mock.MagicMock()
        mock_request.query_params = {'organization': None}
        mock_value_error = mock.PropertyMock(side_effect=ValueError)
        type(mock_request).data = mock_value_error
        result = get_org_id(mock_request)
        self.assertEqual(None, result)

    def test_get_user_org(self):
        """test get_user_org method"""

        # test default organization is returned if defined in user profile.
        expected = self.sub_org
        result = get_user_org(self.user)
        self.assertEqual(expected, result)

        # test org returned will be a parent if user has parent org in orgs.
        # print(dir(self.user))
        expected = self.org
        result = get_user_org(self.user2)
        self.assertEqual(expected, result)

        # test first org id returned if all user orgs are equal rank
        expected = self.sub_org
        result = get_user_org(self.user3)
        self.assertEqual(expected, result)


class SEEDOrgPermissionsTests(TestCase):
    """Tests for Custom DRF Permissions"""
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
        self.org_user = OrganizationUser.objects.create(
            user=self.user, organization=self.org
        )

    def tearDown(self):
        self.user.delete()
        self.org.delete()
        self.org_user.delete()

    @mock.patch('seed.lib.superperms.orgs.permissions.get_org_id')
    def test_has_perm(self, mock_get_org_id):
        """Test has_perm method"""
        permissions = SEEDOrgPermissions()
        mock_request = mock.MagicMock()

        # assert False if org/org user does not exist
        mock_get_org_id.return_value = '1000000'
        mock_request.METHOD = 'GET'
        self.assertFalse(permissions.has_perm(mock_request))

        # check self.org_user has right permissions
        mock_get_org_id.return_value = self.org.id
        mock_request.user = self.user
        assert self.org_user.role_level >= ROLE_MEMBER
        for view_type in SEEDOrgPermissions.perm_map:
            mock_request.METHOD = view_type
            self.assertTrue(permissions.has_perm(mock_request))

        # test with lower role_level
        self.org_user.role_level = ROLE_VIEWER
        self.org_user.save()
        assert self.org_user.role_level < ROLE_MEMBER
        for view_type in ['GET', 'OPTIONS', 'HEAD']:
            mock_request.METHOD = view_type
            self.assertTrue(permissions.has_perm(mock_request))
        for view_type in ['POST', 'PATCH', 'PUT', 'DELETE']:
            mock_request.METHOD = view_type
            self.assertFalse(permissions.has_perm(mock_request))

        # test with higher role_level
        self.org_user.role_level = ROLE_OWNER
        self.org_user.save()
        assert self.org_user.role_level > ROLE_MEMBER
        for view_type in SEEDOrgPermissions.perm_map:
            mock_request.METHOD = view_type
            self.assertTrue(permissions.has_perm(mock_request))

    @mock.patch.object(SEEDOrgPermissions, 'has_perm')
    @mock.patch('seed.lib.superperms.orgs.permissions.is_authenticated')
    def test_has_permission(self, mock_is_authenticated, mock_has_perm):
        """Test has_permission method"""
        permissions = SEEDOrgPermissions()
        mock_request = mock.MagicMock()
        mock_request.user = self.user
        mock_view = mock.MagicMock()

        # assert raises error if no queryset
        mock_value_error = mock.PropertyMock(side_effect=ValueError)
        type(mock_view).get_queryset = mock_value_error
        mock_view.queryset = None
        self.assertRaises(
            AssertionError,
            permissions.has_permission,
            mock_request,
            mock_view
        )

        # queryset its not used, but needs to be checked as work around
        mock_view.queryset = True

        # assert false if not has_perm
        mock_has_perm.return_value = False
        mock_is_authenticated.return_value = True
        self.assertFalse(permissions.has_permission(mock_request, mock_view))

        # assert false if not  authenticated
        mock_has_perm.return_value = True
        mock_is_authenticated.return_value = False
        self.assertFalse(permissions.has_permission(mock_request, mock_view))

        # assert false if not has_perm and is not authenticated
        mock_has_perm.return_value = False
        mock_is_authenticated.return_value = False
        self.assertFalse(permissions.has_permission(mock_request, mock_view))

        # assert true if has_perm and is authenticated
        mock_has_perm.return_value = True
        mock_is_authenticated.return_value = True
        self.assertTrue(permissions.has_permission(mock_request, mock_view))

        # test get_queryset called
        # pylint: disable=redefined-variable-type
        mock_get_queryset = mock.MagicMock()
        type(mock_view).get_queryset = mock_get_queryset
        permissions.has_permission(mock_request, mock_view)
        self.assertTrue(mock_get_queryset.called)


class SEEDPublicPermissionsTests(TestCase):
    """Tests for Custom DRF Permissions"""
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
        self.org_user = OrganizationUser.objects.create(
            user=self.user, organization=self.org
        )

    def tearDown(self):
        self.user.delete()
        self.org.delete()
        self.org_user.delete()

    @mock.patch('seed.lib.superperms.orgs.permissions.is_authenticated')
    @mock.patch('seed.lib.superperms.orgs.permissions.get_org_id')
    def test_has_perm(self, mock_get_org_id, mock_is_authenticated):
        """Test has_perm method"""
        permissions = SEEDPublicPermissions()
        mock_request = mock.MagicMock()

        # assert can use safe methods if not autheticated
        mock_is_authenticated.return_value = False
        for view_type in ['GET', 'OPTIONS', 'HEAD']:
            mock_request.METHOD = view_type
            self.assertTrue(permissions.has_perm(mock_request))
        for view_type in ['POST', 'PATCH', 'PUT', 'DELETE']:
            mock_request.METHOD = view_type
            self.assertFalse(permissions.has_perm(mock_request))

        # check with authenticated user
        mock_is_authenticated.return_value = True

        # check self.org_user has right permissions
        mock_get_org_id.return_value = self.org.id
        mock_request.user = self.user
        assert self.org_user.role_level >= ROLE_MEMBER
        for view_type in SEEDOrgPermissions.perm_map:
            mock_request.METHOD = view_type
            self.assertTrue(permissions.has_perm(mock_request))

        # test with lower role_level
        self.org_user.role_level = ROLE_VIEWER
        self.org_user.save()
        assert self.org_user.role_level < ROLE_MEMBER
        for view_type in ['GET', 'OPTIONS', 'HEAD']:
            mock_request.METHOD = view_type
            self.assertTrue(permissions.has_perm(mock_request))
        for view_type in ['POST', 'PATCH', 'PUT', 'DELETE']:
            mock_request.METHOD = view_type
            self.assertFalse(permissions.has_perm(mock_request))

        # test with higher role_level
        self.org_user.role_level = ROLE_OWNER
        self.org_user.save()
        assert self.org_user.role_level > ROLE_MEMBER
        for view_type in SEEDOrgPermissions.perm_map:
            mock_request.METHOD = view_type
            self.assertTrue(permissions.has_perm(mock_request))

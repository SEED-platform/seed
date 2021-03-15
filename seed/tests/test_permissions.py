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
from seed.utils.organizations import create_organization


def mock_request_factory(view_authz_org_id_kwarg=None, parser_kwargs=None, path='/api/v3/no/org/here/', query_params=None, data=None):
    mock_request = mock.MagicMock()
    # parser context stores the parsed kwargs from the path
    mock_view_dict = {} if view_authz_org_id_kwarg is None else {'authz_org_id_kwarg': view_authz_org_id_kwarg}
    mock_request.parser_context = {
        'view': type('MockView', (object,), mock_view_dict),
        'kwargs': parser_kwargs if parser_kwargs is not None else {}
    }
    mock_request._request = type('MockRequest', (object,), {'path': path})
    mock_request.query_params = query_params if query_params is not None else {}
    mock_request.data = data if data is not None else {}

    return mock_request


class PermissionsFunctionsTests(TestCase):
    """Tests for Custom DRF Permissions util functions"""

    # pylint: disable=too-many-instance-attributes

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
        # Priority of id sources should be, in order:
        # - request parser context (ie view kwarg matches an organization id keyword)
        # - path (under `organizations` resource)
        # - query_params
        # - data

        # Should return None if not found in any of these sources
        mock_request = mock_request_factory(
            view_authz_org_id_kwarg=None,
            parser_kwargs={'not_org_id': 1},
            path='/api/v3/nope/2/',
            query_params={'not_org_id': 3},
            data={'not_org_id': 4}
        )
        result = get_org_id(mock_request)
        self.assertEqual(None, result)

        # get from request parser_context
        mock_request = mock_request_factory(
            view_authz_org_id_kwarg='custom_org_id_keyword',
            parser_kwargs={'custom_org_id_keyword': 1},
            # technically not possible to have different id in path since parser_kwargs
            # comes from path but useful in demonstrating source priorities
            path='/api/v3/organizations/2',
            query_params={'organization_id': 3},
            data={'organization_id': 4}
        )
        result = get_org_id(mock_request)
        self.assertEqual(1, result)

        # get from path
        mock_request = mock_request_factory(
            view_authz_org_id_kwarg=None,
            parser_kwargs={'not_org_id': 1},
            path='/api/v2/organizations/2',
            query_params={'organization_id': 3},
            data={'organization_id': 4}
        )
        result = get_org_id(mock_request)
        self.assertEqual(2, result)

        # get from query params
        mock_request = mock_request_factory(
            view_authz_org_id_kwarg=None,
            parser_kwargs={'not_org_id': 1},
            path='/api/v3/nope/2/',
            query_params={'organization_id': 3},
            data={'organization_id': 4}
        )
        result = get_org_id(mock_request)
        self.assertEqual(3, result)

        # get from data
        mock_request = mock_request_factory(
            view_authz_org_id_kwarg=None,
            parser_kwargs={'not_org_id': 1},
            path='/api/v3/nope/2/',
            query_params={'not_org_id': 3},
            data={'organization_id': 4}
        )
        result = get_org_id(mock_request)
        self.assertEqual(4, result)

        # get from nowhere, and has no data attr
        # not sure why request wouldn't have data, but this is an older test
        # so keeping it here.
        mock_request = mock_request_factory(
            view_authz_org_id_kwarg=None,
            parser_kwargs={'not_org_id': 1},
            path='/api/v3/nope/2/',
            query_params={'not_org_id': 3},
            data={}
        )
        mock_value_error = mock.PropertyMock(side_effect=ValueError)
        type(mock_request).data = mock_value_error
        result = get_org_id(mock_request)
        self.assertEqual(None, result)

    def test_get_user_org(self):
        """Test getting org from user"""
        fake_user = User.objects.create(username='test')
        fake_org_1 = Organization.objects.create()
        fake_org_2 = Organization.objects.create()
        fake_org_3 = Organization.objects.create()
        OrganizationUser.objects.create(
            user=fake_user, organization=fake_org_1
        )
        OrganizationUser.objects.create(
            user=fake_user, organization=fake_org_2
        )
        OrganizationUser.objects.create(
            user=fake_user, organization=fake_org_3
        )
        # no default_organization and no parent org
        result = get_user_org(fake_user)
        self.assertIn(result, fake_user.orgs.all())

        # parent org, no default_organization
        fake_org_1.parent_org = fake_org_2
        fake_org_1.save()
        expected = fake_org_2
        result = get_user_org(fake_user)
        self.assertEqual(result, expected)

        # user default_organization
        fake_user.default_organization = fake_org_3
        fake_user.save()
        expected = fake_org_3
        result = get_user_org(fake_user)
        self.assertEqual(result, expected)


class SEEDOrgPermissionsTests(TestCase):
    """Tests for Custom DRF Permissions"""

    # pylint: disable=too-many-instance-attributes

    def setUp(self):
        self.user = User.objects.create_user('test_user@demo.com', 'test_user@demo.com', 'test_pass')
        self.superuser = User.objects.create_superuser('test_superuser@demo.com', 'test_superuser@demo.com', 'test_pass')
        self.org, self.org_user, _ = create_organization(self.user)

    def tearDown(self):
        self.user.delete()
        self.org.delete()
        self.org_user.delete()

    @mock.patch('seed.lib.superperms.orgs.permissions.get_org_id')
    def test_has_perm(self, mock_get_org_id):
        """Test has_perm method"""
        permissions = SEEDOrgPermissions()
        mock_request = mock.MagicMock()
        mock_request.user = self.user

        # assert False if org/org user does not exist
        mock_get_org_id.return_value = '1000000'
        mock_request.method = 'GET'
        self.assertFalse(permissions.has_perm(mock_request))

        # check self.org_user has right permissions
        mock_get_org_id.return_value = self.org.id
        assert self.org_user.role_level >= ROLE_MEMBER
        for view_type in SEEDOrgPermissions.perm_map:
            mock_request.method = view_type
            self.assertTrue(permissions.has_perm(mock_request))

        # test with lower role_level
        self.org_user.role_level = ROLE_VIEWER
        self.org_user.save()
        assert self.org_user.role_level < ROLE_MEMBER
        for view_type in ['GET', 'OPTIONS', 'HEAD']:
            mock_request.method = view_type
            self.assertTrue(permissions.has_perm(mock_request))
        for view_type in ['POST', 'PATCH', 'PUT', 'DELETE']:
            mock_request.method = view_type
            self.assertFalse(permissions.has_perm(mock_request))

        # test with admin
        mock_request.user = self.superuser
        self.assertTrue(permissions.has_perm(mock_request))

    @mock.patch.object(SEEDOrgPermissions, 'has_perm')
    @mock.patch('seed.lib.superperms.orgs.permissions.is_authenticated')
    def test_has_permission(self, mock_is_authenticated, mock_has_perm):
        """Test has_permission method"""
        permissions = SEEDOrgPermissions()
        mock_request = mock.MagicMock()
        mock_request.user = self.user
        mock_view = mock.MagicMock()

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
        mock_view.queryset = None
        mock_get_queryset = mock.MagicMock()
        type(mock_view).get_queryset = mock_get_queryset
        permissions.has_permission(mock_request, mock_view)
        self.assertTrue(mock_get_queryset.called)

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


class SEEDPublicPermissionsTests(TestCase):
    """Tests for Custom DRF Permissions"""

    # pylint: disable=too-many-instance-attributes

    def setUp(self):
        self.user = User.objects.create_user('test_user@demo.com', 'test_user@demo.com', 'test_pass')
        self.org, self.org_user, _ = create_organization(self.user)

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
            mock_request.method = view_type
            self.assertTrue(permissions.has_perm(mock_request))
        for view_type in ['POST', 'PATCH', 'PUT', 'DELETE']:
            mock_request.method = view_type
            self.assertFalse(permissions.has_perm(mock_request))

        # check with authenticated user
        mock_is_authenticated.return_value = True

        # check self.org_user has right permissions
        mock_get_org_id.return_value = self.org.id
        mock_request.user = self.user
        assert self.org_user.role_level >= ROLE_MEMBER
        for view_type in SEEDOrgPermissions.perm_map:
            mock_request.method = view_type
            self.assertTrue(permissions.has_perm(mock_request))

        # test with lower role_level
        self.org_user.role_level = ROLE_VIEWER
        self.org_user.save()
        assert self.org_user.role_level < ROLE_MEMBER
        for view_type in ['GET', 'OPTIONS', 'HEAD']:
            mock_request.method = view_type
            self.assertTrue(permissions.has_perm(mock_request))
        for view_type in ['POST', 'PATCH', 'PUT', 'DELETE']:
            mock_request.method = view_type
            self.assertFalse(permissions.has_perm(mock_request))

        # test with higher role_level
        self.org_user.role_level = ROLE_OWNER
        self.org_user.save()
        assert self.org_user.role_level > ROLE_MEMBER
        for view_type in SEEDOrgPermissions.perm_map:
            mock_request.method = view_type
            self.assertTrue(permissions.has_perm(mock_request))

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.utils.unittest import TestCase
from django.http import HttpResponse, HttpResponseForbidden
from seed.lib.superperms.orgs.models import (
    ROLE_VIEWER,
    ROLE_MEMBER,
    ROLE_OWNER,
    Organization,
    OrganizationUser,
)
from seed.landing.models import SEEDUser as User


#
# Copied wholesale from django-brake's tests
# https://github.com/gmcquillan/django-brake/blob/master/brake/tests/tests.py
from seed.lib.superperms.orgs import decorators


class FakeRequest(object):
    """A simple request stub."""
    __name__ = 'FakeRequest'
    method = 'POST'
    META = {'REMOTE_ADDR': '127.0.0.1'}
    path = 'fake_login_path'
    body = None

    def __init__(self, headers=None):
        if headers:
            self.META.update(headers)


class FakeClient(object):
    """An extremely light-weight test client."""

    def _gen_req(self, view_func, data, headers, method='POST', **kwargs):
        request = FakeRequest(headers)
        if 'user' in kwargs:
            request.user = kwargs.get('user')
        if callable(view_func):
            # since we check for a GET first for organization_id, then the body
            setattr(request, 'GET', {})
            setattr(request, method, data)
            request.body = json.dumps(data)
            return view_func(request)

        return request

    def get(self, view_func, data, headers=None, **kwargs):
        return self._gen_req(view_func, data, headers, method='GET', **kwargs)

    def post(self, view_func, data, headers=None, **kwargs):
        return self._gen_req(view_func, data, headers, **kwargs)


# These are test functions wrapped in decorators.

@decorators.has_perm('derp')
def _fake_view_no_perm_name(request):
    return HttpResponse()


@decorators.has_perm('can_invite_member')
def _fake_invite_user(request):
    return HttpResponse()


class TestDecorators(TestCase):
    def setUp(self):
        super(TestDecorators, self).setUp()
        self.client = FakeClient()
        self.fake_org = Organization.objects.create(name='fake org')
        self.fake_member = User.objects.create(
            username='fake_member',
            email='fake_member@asdf.com'
        )
        self.fake_superuser = User.objects.create_superuser(
            username='fake_super_member',
            password='so fake, so real',
            email='fake_super_member@asdf.com'
        )
        self.fake_owner = User.objects.create(
            username='fake_owner',
            email='fake_owner@asdf.com'
        )
        self.fake_viewer = User.objects.create(
            username='fake_viewer',
            email='fake_viewer@asdf.com'
        )
        self.owner_org_user = OrganizationUser.objects.create(
            user=self.fake_owner,
            organization=self.fake_org,
            role_level=ROLE_OWNER
        )
        self.member_org_user = OrganizationUser.objects.create(
            user=self.fake_member,
            organization=self.fake_org,
            role_level=ROLE_MEMBER
        )
        self.viewer_org_user = OrganizationUser.objects.create(
            user=self.fake_viewer,
            organization=self.fake_org,
            role_level=ROLE_VIEWER
        )
        self.superuser_org_user = OrganizationUser.objects.create(
            user=self.fake_superuser,
            organization=self.fake_org,
            role_level=ROLE_VIEWER
        )

    def tearDown(self):
        """WTF DJANGO."""
        User.objects.all().delete()
        Organization.objects.all().delete()
        OrganizationUser.objects.all().delete()
        super(TestDecorators, self).tearDown()

    # Test has_perm in various permutations.

    def test_has_perm_w_no_org(self):
        """We should return BadRequest if there's no org."""
        self.client.user = User.objects.create(username='f', email='d@d.com')
        resp = self.client.post(
            _fake_view_no_perm_name,
            {'organization_id': 0},
            user=self.client.user
        )
        error_msg = {
            'status': 'error', 'message': 'Organization does not exist'
        }

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.__class__, HttpResponseForbidden)
        self.assertDictEqual(json.loads(resp.content), error_msg)

    def test_has_perm_user_not_in_org(self):
        """We should reject requests from a user not in this org."""
        self.client.user = User.objects.create(username='f', email='d@d.com')
        resp = self.client.post(
            _fake_view_no_perm_name,
            {'organization_id': self.fake_org.pk},
            user=self.client.user
        )

        error_msg = {
            'status': 'error', 'message': 'No relationship to organization'
        }

        self.assertEqual(resp.status_code, 403)
        self.assertDictEqual(json.loads(resp.content), error_msg)

    def test_has_perm_w_no_perm_name(self):
        """Default to false if an undefined perm is spec'ed"""
        self.client.user = self.fake_member
        resp = self.client.post(
            _fake_view_no_perm_name,
            {'organization_id': self.fake_org.pk},
            user=self.fake_member
        )

        self.assertEqual(resp.status_code, 403)

    def test_has_perm_w_super_user(self):
        """Make sure that a superuser is ignored if setting is True."""
        super_user = User.objects.create(username='databaser')

        resp = self.client.post(
            _fake_invite_user,
            {'organization_id': self.fake_org.pk},
            user=self.fake_member
        )

        error_msg = {
            'status': 'error', 'message': 'Permission denied'
        }

        self.assertEqual(resp.status_code, 403)
        self.assertDictEqual(json.loads(resp.content), error_msg)

        super_user.is_superuser = True
        super_user.save()

        # Note that our super_user isn't associated withn *any* Orgs.
        self.client.user = super_user
        resp = self.client.post(
            _fake_invite_user,
            {'organization_id': self.fake_org.pk},
            user=super_user
        )

        self.assertEqual(resp.__class__, HttpResponse)

    def test_has_perm_good_case(self):
        """Test that we actually allow people through."""
        self.client.user = self.fake_owner
        resp = self.client.post(
            _fake_invite_user,
            {'organization_id': self.fake_org.pk},
            user=self.fake_owner
        )

        self.assertEqual(resp.__class__, HttpResponse)

    # Test boolean functions for permission logic.

    def test_requires_parent_org_owner(self):
        """Correctly suss out parent org owners."""
        self.assertTrue(decorators.requires_parent_org_owner(
            self.owner_org_user
        ))
        self.assertFalse(decorators.requires_parent_org_owner(
            self.member_org_user
        ))

        baby_org = Organization.objects.create(name='baby')
        # Add Viewer from the parent org as the owner of the child org.
        baby_ou = OrganizationUser.objects.create(
            user=self.fake_viewer, organization=baby_org
        )
        baby_org.parent_org = self.fake_org
        baby_org.save()

        # Even though we're owner for this org, it's not a parent org.
        self.assertFalse(decorators.requires_parent_org_owner(baby_ou))

    def test_can_create_sub_org(self):
        """Only an owner can create sub orgs."""
        self.assertTrue(decorators.can_create_sub_org(self.owner_org_user))
        self.assertFalse(decorators.can_create_sub_org(self.member_org_user))
        self.assertFalse(decorators.can_create_sub_org(self.viewer_org_user))

    def test_can_remove_org(self):
        """Only an owner can create sub orgs."""
        self.assertTrue(decorators.can_remove_org(self.owner_org_user))
        self.assertFalse(decorators.can_remove_org(self.member_org_user))
        self.assertFalse(decorators.can_remove_org(self.viewer_org_user))

    def test_can_invite_member(self):
        """Only an owner can create sub orgs."""
        self.assertTrue(decorators.can_invite_member(self.owner_org_user))
        self.assertFalse(decorators.can_invite_member(self.member_org_user))
        self.assertFalse(decorators.can_invite_member(self.viewer_org_user))

    def test_can_remove_member(self):
        """Only an owner can create sub orgs."""
        self.assertTrue(decorators.can_remove_member(self.owner_org_user))
        self.assertFalse(decorators.can_remove_member(self.member_org_user))
        self.assertFalse(decorators.can_remove_member(self.viewer_org_user))

    def test_can_modify_query_thresh(self):
        """Only an parent owner can modify query thresholds."""
        self.assertTrue(
            decorators.can_modify_query_thresh(self.owner_org_user)
        )
        self.assertFalse(decorators.can_modify_query_thresh(
            self.member_org_user
        ))
        self.assertFalse(decorators.can_modify_query_thresh(
            self.viewer_org_user
        ))

    def test_can_view_sub_org_settings(self):
        """Only an parent owner can create sub orgs."""
        self.assertTrue(
            decorators.can_view_sub_org_settings(self.owner_org_user)
        )
        self.assertFalse(
            decorators.can_view_sub_org_settings(self.member_org_user)
        )
        self.assertFalse(
            decorators.can_view_sub_org_settings(self.viewer_org_user)
        )

    def test_can_view_sub_org_fields(self):
        """Only an parent owner can create sub orgs."""
        self.assertTrue(
            decorators.can_view_sub_org_fields(self.owner_org_user)
        )
        self.assertFalse(
            decorators.can_view_sub_org_fields(self.member_org_user)
        )
        self.assertFalse(
            decorators.can_view_sub_org_fields(self.viewer_org_user)
        )

    def test_requires_owner(self):
        """Test ownerness."""
        self.assertTrue(decorators.requires_owner(self.owner_org_user))
        self.assertFalse(decorators.requires_owner(self.member_org_user))
        self.assertFalse(decorators.requires_owner(self.viewer_org_user))

    def test_requires_owner_w_child_org_and_parent_owner(self):
        """Parent owners are as child owners."""
        baby_org = Organization.objects.create(name='baby')
        baby_org.parent_org = self.fake_org
        baby_org.save()

        self.assertTrue(decorators.requires_owner(self.owner_org_user))

    def test_requires_member(self):
        """Test membership."""
        self.assertTrue(decorators.requires_member(self.member_org_user))
        self.assertTrue(decorators.requires_member(self.member_org_user))
        self.assertFalse(decorators.requires_member(self.viewer_org_user))

    def test_requires_viewer(self):
        """Test viewership."""
        self.assertTrue(decorators.requires_viewer(self.owner_org_user))
        self.assertTrue(decorators.requires_viewer(self.member_org_user))
        self.assertTrue(decorators.requires_viewer(self.viewer_org_user))

    def test_requires_superuser(self):
        """Test superusership."""
        self.assertFalse(decorators.requires_superuser(self.owner_org_user))
        self.assertFalse(decorators.requires_superuser(self.member_org_user))
        self.assertFalse(decorators.requires_superuser(self.viewer_org_user))
        self.assertTrue(decorators.requires_superuser(self.superuser_org_user))

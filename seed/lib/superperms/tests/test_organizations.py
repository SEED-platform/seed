# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.utils.unittest import TestCase

from seed.lib.superperms.orgs.exceptions import TooManyNestedOrgs
from seed.lib.superperms.orgs.models import (
    ROLE_VIEWER,
    ROLE_MEMBER,
    ROLE_OWNER,
    STATUS_PENDING,
    ExportableField,
    Organization,
    OrganizationUser,
)

from seed.landing.models import SEEDUser as User


class TestOrganizationUser(TestCase):
    # TODO: I know I shouldn't need these. Need to figure out what's up with
    # Django's TestCase.
    def setUp(self, *args, **kwargs):
        self.user1 = User.objects.create(
            username='user1', email='asdf@asdf.com'
        )
        self.user2 = User.objects.create(
            username='user2', email='asdf2@asdf.com'
        )
        self.user3 = User.objects.create(
            username='user3', email='asdf3@asdf.com'
        )
        self.org = Organization.objects.create(name='OrgUser Tester')
        super(TestOrganizationUser, self).setUp(*args, **kwargs)

    def tearDown(self, *args, **kwargs):
        """WTF Django test case?"""
        User.objects.all().delete()
        OrganizationUser.objects.all().delete()
        Organization.objects.all().delete()
        ExportableField.objects.all().delete()
        super(TestOrganizationUser, self).tearDown(*args, **kwargs)

    def test_last_organization_user_is_owner(self):
        """Make sure last organization user is change to owner."""
        org_user1 = OrganizationUser.objects.create(
            user=self.user1, organization=self.org
        )
        OrganizationUser.objects.create(
            user=self.user2, organization=self.org, role_level=ROLE_VIEWER
        )
        org_user3 = OrganizationUser.objects.create(
            user=self.user3, organization=self.org, role_level=ROLE_MEMBER
        )

        self.assertEqual(OrganizationUser.objects.all().count(), 3)
        self.assertEqual(
            OrganizationUser.objects.filter(role_level=ROLE_OWNER).count(), 1
        )

        org_user1.delete()

        self.assertEqual(
            OrganizationUser.objects.filter(role_level=ROLE_OWNER).count(), 1
        )

        refreshed_org_user3 = OrganizationUser.objects.get(pk=org_user3.pk)

        self.assertEqual(refreshed_org_user3.role_level, ROLE_OWNER)


class TestOrganization(TestCase):
    # TODO: I know I shouldn't need these. Need to figure out what's up with
    # Django's TestCase.
    def setUp(self, *args, **kwargs):
        self.user = User.objects.create(email='asdf@asdf.com')
        super(TestOrganization, self).setUp(*args, **kwargs)

    def tearDown(self, *args, **kwargs):
        """WTF Django test case?"""
        User.objects.all().delete()
        OrganizationUser.objects.all().delete()
        Organization.objects.all().delete()
        ExportableField.objects.all().delete()
        super(TestOrganization, self).tearDown(*args, **kwargs)

    def test_add_user_to_org(self):
        """Test that a user is associated with an org using through table."""
        org = Organization.objects.create()

        # Ensure we don't have any users associated yet.
        self.assertEqual(org.users.all().count(), 0)

        # Just link a user and an org, leave defaults
        org_user = OrganizationUser.objects.create(
            user=self.user, organization=org
        )

        self.assertEqual(org_user.role_level, ROLE_OWNER)  # Default
        self.assertEqual(org_user.status, STATUS_PENDING)

        self.assertEqual(
            org.users.all()[0], self.user
        )

    def test_exportable_fields(self):
        """We can set a list of fields to be exportable for an org."""
        org = Organization.objects.create()
        exportable_fields = [
            ExportableField.objects.create(
                name='test-{0}'.format(x),
                organization=org,
                field_model='FakeModel'
            ) for x in range(10)
            ]

        self.assertListEqual(
            list(org.exportable_fields.all()), exportable_fields
        )

    def test_one_level_org_nesting(self):
        """Make sure we can save one level of organization."""
        parent_org = Organization.objects.create(name='Big Daddy')
        child_org = Organization.objects.create(name='Little Sister')

        child_org.parent_org = parent_org
        child_org.save()

        refreshed_parent = Organization.objects.get(pk=parent_org.pk)
        refreshed_child = Organization.objects.get(pk=child_org.pk)
        self.assertEqual(refreshed_parent.child_orgs.first(), refreshed_child)
        self.assertEqual(refreshed_child.parent_org, refreshed_parent)

    def test_multi_level_org_nesting(self):
        """Make sure we raise exception if a child tries to make a child."""
        parent_org = Organization.objects.create(name='Big Daddy')
        child_org = Organization.objects.create(name='Little Sister')
        baby_org = Organization.objects.create(name='Baby Sister')

        child_org.parent_org = parent_org  # Double nesting
        child_org.save()

        baby_org.parent_org = child_org

        self.assertRaises(TooManyNestedOrgs, baby_org.save)

    def test_get_parent_nested(self):
        """Test for get_parent() in a nested situation."""
        parent_org = Organization.objects.create(name='Big Daddy')
        child_org = Organization.objects.create(
            name='Little Sister', parent_org=parent_org
        )

        self.assertEqual(child_org.get_parent(), parent_org)
        self.assertEqual(parent_org.get_parent(), parent_org)

    def test_get_parent_not_nested(self):
        """Test for get_parent() in a solo org situation."""
        org = Organization.objects.create(name='Solo Org')
        self.assertEqual(org.get_parent(), org)

    def test_get_exportable_fields(self):
        """Make sure we use parent exportable_fields."""
        parent_org = Organization.objects.create(name='Parent')
        parent_fields = [
            ExportableField.objects.create(
                name='parent-{0}'.format(x),
                organization=parent_org,
                field_model='FakeModel'
            ) for x in range(10)
            ]

        child_org = Organization.objects.create(name='Child')
        child_fields = [
            ExportableField.objects.create(
                name='child-{0}'.format(x),
                organization=child_org,
                field_model='FakeModel'
            ) for x in range(10)
            ]

        self.assertListEqual(
            list(child_org.get_exportable_fields()), child_fields
        )

        child_org.parent_org = parent_org
        child_org.save()

        self.assertListEqual(
            list(child_org.get_exportable_fields()), parent_fields
        )

    def test_get_query_threshold(self):
        """Make sure we use the parent's query threshold."""
        parent_org = Organization.objects.create(
            name='Parent', query_threshold=10
        )

        child_org = Organization.objects.create(
            name='Child', query_threshold=9
        )

        self.assertEqual(child_org.get_query_threshold(), 9)

        child_org.parent_org = parent_org
        child_org.save()

        self.assertEqual(child_org.get_query_threshold(), 10)

    def test_is_member(self):
        """Make sure our convenience function works properly."""
        org = Organization.objects.create(name='Org')
        self.assertFalse(org.is_member(self.user))
        OrganizationUser.objects.create(user=self.user, organization=org)
        self.assertTrue(org.is_member(self.user))

    def test_add_member(self):
        """We can add a member using the convenience function."""
        org = Organization.objects.create(name='Org')
        self.assertFalse(
            OrganizationUser.objects.filter(user=self.user).exists()
        )

        org.add_member(self.user)

        self.assertTrue(OrganizationUser.objects.filter(
            user=self.user, organization=org
        ).exists())

    def test_remove_member(self):
        """We can remove a member."""
        org = Organization.objects.create(name='Org')
        OrganizationUser.objects.create(user=self.user, organization=org)

        self.assertTrue(OrganizationUser.objects.filter(
            user=self.user, organization=org
        ).exists())

        org.remove_member(self.user)

        self.assertFalse(OrganizationUser.objects.filter(
            user=self.user, organization=org
        ).exists())

    def test_is_owner(self):
        org = Organization.objects.create(name='Org')
        ou = OrganizationUser.objects.create(
            user=self.user, organization=org, role_level=ROLE_OWNER
        )
        self.assertTrue(org.is_owner(self.user))

        # members aren't owners
        ou.role_level = ROLE_MEMBER
        ou.save()
        self.assertFalse(org.is_owner(self.user))

        # non-members aren't owners
        org.remove_member(self.user)
        self.assertFalse(org.is_owner(self.user))

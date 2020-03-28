# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.models import (
    Compliance, Project
)
from seed.utils.organizations import create_organization


class ProjectTestCase(TestCase):

    def test_basic_project_creation(self):
        user = User.objects.create(username='test', first_name='t', last_name='est')
        org, user_role, _user_created = create_organization(
            user, 'Test Organization'
        )
        p = Project.objects.create(
            name='Test Project',
            owner=user,
            super_organization=org,
            description='A really great test organization.',
        )
        p.save()
        self.assertEqual(p.name, 'Test Project')
        self.assertTrue('Test Project' in str(p))
        self.assertEqual(p.owner, user)
        self.assertEqual(p.super_organization, org)
        self.assertEqual(p.status, Project.ACTIVE_STATUS)
        self.assertEqual(p.description, 'A really great test organization.')
        self.assertEqual(p.slug, 'test-project')
        user.delete()
        org.delete()


class ComplianceTestCase(TestCase):

    def test_basic_compliance_creation(self):
        p = Project(name='test project')
        p.save()
        c = Compliance(project=p)
        c.save()

        self.assertEqual(c.compliance_type, 'Benchmarking')
        #  test relation from compliance to project and vice versa
        self.assertEqual(c.project, p)
        self.assertTrue(p.compliance_set.exists())
        self.assertTrue(p.compliance_set.all()[0], c)
        # test repr or str
        self.assertEqual('Compliance Benchmarking for project Project test project', str(c))
        p.delete()
        c.delete()

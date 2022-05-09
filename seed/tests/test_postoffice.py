# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.models import PostOfficeEmailTemplate
from seed.utils.organizations import create_organization


class TestPostOffice(TestCase):

    def setUp(self):
        self.fake_user = User.objects.create(username='test')
        self.fake_org, _, _ = create_organization(self.fake_user)

    def test_default_template(self):
        template = PostOfficeEmailTemplate.objects.create()
        self.assertEqual(PostOfficeEmailTemplate.objects.count(), 1)

        template.delete()
        self.assertEqual(PostOfficeEmailTemplate.objects.count(), 0)

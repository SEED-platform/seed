# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
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

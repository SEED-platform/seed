# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pmerriam@quickleft.com>'
"""
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.models import (
    StatusLabel as Label,
)
from seed.utils.organizations import (
    create_organization
)


class TestOrganizationCreation(TestCase):

    def test_organization_creation_creates_default_labels(self):
        """Make sure last organization user is change to owner."""
        user = User.objects.create(email='test-user@example.com')
        org, org_user, user_added = create_organization(
            user=user,
            org_name='test-organization',
        )
        self.assertEqual(
            org.labels.count(),
            len(Label.DEFAULT_LABELS),
        )

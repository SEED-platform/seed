"""
Tests for organization utility functions.
:copyright (c) 2015, The Regents of the University of California, Department of Energy contract-operators of the Lawrence Berkeley National Laboratory.
:author Piper Merriam
"""
from django.test import TestCase

from seed.utils.organizations import (
    create_organization
)
from seed.landing.models import SEEDUser as User
from seed.models import (
    StatusLabel as Label,
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

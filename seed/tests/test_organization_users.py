# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import OrganizationUser
from seed.tests.util import AccessLevelBaseTestCase


class TestOrganizationPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.root_ali = self.org.root
        self.child_ali = self.org.root.get_children().first()

        self.root_user = User.objects.get(username='test_user@demo.com')
        self.child_user1 = User.objects.get(username='child_member@demo.com')
        self.child_user2 = User.objects.create(username='child_member2@demo.com')
        OrganizationUser.objects.create(
            user=self.child_user2,
            organization=self.org,
            access_level_instance_id=self.child_ali.id,
            role_level=0,
        )

    def test_org_user_permissions(self):
        user_count = User.objects.count()
        self.login_as_root_member()
        url = reverse_lazy('api:v3:organization-users-list', args=[self.org.id]) + f'?organization_id={self.org.id}'
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200
        users = response.json()['users']
        assert len(users) == user_count

        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200
        users = response.json()['users']
        assert len(users) < user_count
        assert len(users) == 2

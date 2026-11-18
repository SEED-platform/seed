"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core import mail
from django.urls import reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import ROLE_OWNER, AccessLevelInstance, OrganizationUser
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class TestOrganizationPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.root_ali = self.org.root
        self.child_ali = AccessLevelInstance.objects.get_children(self.org.root).first()

        self.root_user = User.objects.get(username="test_user@demo.com")
        self.child_user1 = User.objects.get(username="child_member@demo.com")
        self.child_user2 = User.objects.create(username="child_member2@demo.com")
        OrganizationUser.objects.create(
            user=self.child_user2,
            organization=self.org,
            access_level_instance_id=self.child_ali.id,
            role_level=0,
        )

    def test_org_user_permissions(self):
        user_count = User.objects.count()
        self.login_as_root_member()
        url = reverse_lazy("api:v3:organization-users-list", args=[self.org.id]) + f"?organization_id={self.org.id}"
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        users = response.json()["users"]
        assert len(users) == user_count

        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        users = response.json()["users"]
        assert len(users) < user_count
        assert len(users) == 2

    def test_superuser_adds_themself_to_organization(self):
        # a superuser can see every organization, and joins one they are not a member of as an owner, without an invite email
        other_org, _, _ = create_organization(self.root_user, "Other Org")
        superuser = self.superuser
        assert not OrganizationUser.objects.filter(user=superuser, organization=other_org).exists()

        url = reverse_lazy("api:v3:organization-users-add", args=[other_org.id, superuser.id])
        response = self.client.put(url, content_type="application/json")
        assert response.status_code == 200
        org_user = OrganizationUser.objects.get(user=superuser, organization=other_org)
        assert org_user.role_level == ROLE_OWNER
        assert org_user.access_level_instance == other_org.root
        assert len(mail.outbox) == 0

        # adding someone else still invites them
        response = self.client.put(
            reverse_lazy("api:v3:organization-users-add", args=[other_org.id, self.child_user1.id]), content_type="application/json"
        )
        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [self.child_user1.email]

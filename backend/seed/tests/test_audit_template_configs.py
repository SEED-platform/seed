"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django_celery_beat.models import PeriodicTask

from seed.audit_template.audit_template import AUTO_SYNC_NAME, AuditTemplate
from seed.landing.models import SEEDUser as User
from seed.models import AuditTemplateConfig
from seed.utils.organizations import create_organization


class AuditTemplateCronTests(TestCase):
    def setUp(self):
        settings.AUDIT_TEMPLATE_HOST = "https://staging.labworks.org"
        self.user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        self.user = User.objects.create_superuser(email="test_user@demo.com", **self.user_details)
        self.org, _, _ = create_organization(self.user)
        self.org.save()
        self.at = AuditTemplate(self.org.id)
        self.client.login(**self.user_details)

        self.atc = AuditTemplateConfig.objects.create(organization=self.org, update_at_day=0, update_at_hour=1, update_at_minute=2)

    def tearDown(self):
        AuditTemplateConfig.objects.all().delete()

    def test_audit_template_config_list(self):
        url = reverse("api:v3:audit_template_configs-list") + f"?organization_id={self.org.id}"
        response = self.client.get(url, content_type="application/json")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["organization"] == self.org.id
        assert data[0]["update_at_day"] == 0
        assert data[0]["update_at_hour"] == 1
        assert data[0]["update_at_minute"] == 2

    def test_audit_template_config_create(self):
        AuditTemplateConfig.objects.all().delete()

        url = reverse("api:v3:audit_template_configs-list") + f"?organization_id={self.org.id}"
        params = {"update_at_day": 6, "update_at_hour": 23, "update_at_minute": 59}
        response = self.client.post(url, params, content_type="application/json")

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["organization"] == self.org.id
        assert data["update_at_day"] == 6
        assert data["update_at_hour"] == 23
        assert data["update_at_minute"] == 59

        # testing one-to-one relationship
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 400
        assert response.json()["errors"] == {"organization": ["audit template config with this organization already exists."]}

    def test_audit_template_config_create_schedules_sync_only_with_a_complete_schedule(self):
        AuditTemplateConfig.objects.all().delete()
        url = reverse("api:v3:audit_template_configs-list") + f"?organization_id={self.org.id}"
        sync_tasks = PeriodicTask.objects.filter(name=AUTO_SYNC_NAME + str(self.org.id))

        # without a day, the config is saved but no sync is scheduled
        response = self.client.post(url, {"update_at_hour": 23, "update_at_minute": 59}, content_type="application/json")
        assert response.status_code == 201
        assert response.json()["data"]["update_at_day"] is None
        assert not sync_tasks.exists()

        AuditTemplateConfig.objects.all().delete()
        response = self.client.post(
            url, {"update_at_day": 6, "update_at_hour": 23, "update_at_minute": 59}, content_type="application/json"
        )
        assert response.status_code == 201
        crontab = sync_tasks.get().crontab
        assert (crontab.day_of_week, crontab.hour, crontab.minute) == ("6", "23", "59")

    def test_audit_template_config_update(self):
        # Invalid params
        url = reverse("api:v3:audit_template_configs-detail", args=[self.atc.id]) + f"?organization_id={self.org.id}"
        params = {"update_at_day": 10, "update_at_hour": 50, "update_at_minute": 100}
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 400
        errors = response.json()["errors"]
        assert errors["update_at_day"] == ["Ensure this value is less than or equal to 6."]
        assert errors["update_at_hour"] == ["Ensure this value is less than or equal to 23."]
        assert errors["update_at_minute"] == ["Ensure this value is less than or equal to 59."]

        self.atc.refresh_from_db()
        assert self.atc.update_at_day == 0
        assert self.atc.update_at_hour == 1
        assert self.atc.update_at_minute == 2

        # valid params
        params = {"update_at_day": 5, "update_at_hour": 15, "update_at_minute": 50}
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["update_at_day"] == 5
        self.atc.refresh_from_db()
        assert self.atc.update_at_day == data["update_at_day"]
        assert self.atc.update_at_hour == data["update_at_hour"]
        assert self.atc.update_at_minute == data["update_at_minute"]

        # no changes detected
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 200
        assert response.json()["message"] == "No changes detected."

    def test_audit_template_config_delete(self):
        assert AuditTemplateConfig.objects.count() == 1
        url = reverse("api:v3:audit_template_configs-detail", args=[self.atc.id]) + f"?organization_id={self.org.id}"
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204
        assert AuditTemplateConfig.objects.count() == 0


class AuditTemplateConfigOrganizationTests(TestCase):
    def setUp(self):
        self.user_details = {
            "username": "test_owner@demo.com",
            "password": "test_pass",
        }
        self.user = User.objects.create_user(email="test_owner@demo.com", **self.user_details)
        self.org, _, _ = create_organization(self.user, "org-a")

        other_user = User.objects.create_user(username="other_owner@demo.com", password="test_pass", email="other_owner@demo.com")
        self.other_org, _, _ = create_organization(other_user, "org-b")
        self.other_atc = AuditTemplateConfig.objects.create(
            organization=self.other_org, update_at_day=0, update_at_hour=1, update_at_minute=2
        )

        self.client.login(**self.user_details)

    def tearDown(self):
        AuditTemplateConfig.objects.all().delete()

    def test_audit_template_config_update_other_organization(self):
        url = reverse("api:v3:audit_template_configs-detail", args=[self.other_atc.id]) + f"?organization_id={self.org.id}"
        params = {"update_at_day": 5, "update_at_hour": 15, "update_at_minute": 50}
        response = self.client.put(url, params, content_type="application/json")

        assert response.json() == {"status": "error", "message": "No such resource."}
        self.other_atc.refresh_from_db()
        assert self.other_atc.organization_id == self.other_org.id
        assert self.other_atc.update_at_day == 0

    def test_audit_template_config_delete_other_organization(self):
        url = reverse("api:v3:audit_template_configs-detail", args=[self.other_atc.id]) + f"?organization_id={self.org.id}"
        response = self.client.delete(url, content_type="application/json")

        assert response.json() == {"status": "error", "message": "No such resource."}
        assert AuditTemplateConfig.objects.filter(pk=self.other_atc.id).exists()

    def test_audit_template_config_create_ignores_body_organization(self):
        AuditTemplateConfig.objects.all().delete()

        url = reverse("api:v3:audit_template_configs-list") + f"?organization_id={self.org.id}"
        params = {"organization": self.other_org.id, "update_at_day": 6, "update_at_hour": 23, "update_at_minute": 59}
        response = self.client.post(url, params, content_type="application/json")

        assert response.status_code == 201
        assert response.json()["data"]["organization"] == self.org.id
        assert not AuditTemplateConfig.objects.filter(organization=self.other_org).exists()

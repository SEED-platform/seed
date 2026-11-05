"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author nicholas.long@nlr.gov
"""

import json

from django.urls import reverse_lazy

from seed.lib.superperms.orgs.models import ROLE_VIEWER
from seed.models import GreenAssessment, GreenAssessmentProperty, GreenAssessmentURL
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class TestGreenAssessmentsPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.green_assessment = GreenAssessment.objects.create(organization_id=self.org.id, is_numeric_score=True)

    def test_green_assessments_list(self):
        url = reverse_lazy("api:v3:green_assessments-list") + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

    def test_green_assessments_award_body_icontains_filter(self):
        GreenAssessment.objects.create(organization_id=self.org.id, name="Energy Star", award_body="EPA", is_numeric_score=True)
        GreenAssessment.objects.create(organization_id=self.org.id, name="EPA Score", award_body="USGBC", is_numeric_score=True)
        url = reverse_lazy("api:v3:green_assessments-list") + "?organization_id=" + str(self.org.id) + "&award_body_icontains=ep"

        self.login_as_root_owner()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert [assessment["name"] for assessment in response.json()["data"]] == ["Energy Star"]

    def test_green_assessments_get(self):
        url = reverse_lazy("api:v3:green_assessments-detail", args=[self.green_assessment.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

    def test_green_assessments_destroy(self):
        url = reverse_lazy("api:v3:green_assessments-detail", args=[self.green_assessment.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204

    def test_green_assessments_create(self):
        url = reverse_lazy("api:v3:green_assessments-list") + "?organization_id=" + str(self.org.id)
        params = json.dumps({"name": "boo", "recognition_type": "AWD", "is_numeric_score": True})

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 403
        assert not GreenAssessment.objects.filter(name="boo").exists()

        # root users can
        self.login_as_root_owner()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 201

    def test_green_assessments_put(self):
        url = reverse_lazy("api:v3:green_assessments-detail", args=[self.green_assessment.pk]) + "?organization_id=" + str(self.org.id)
        params = json.dumps({"name": "boo", "recognition_type": "AWD", "is_numeric_score": True})

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 200

    def test_green_assessments_patch(self):
        url = reverse_lazy("api:v3:green_assessments-detail", args=[self.green_assessment.pk]) + "?organization_id=" + str(self.org.id)
        params = json.dumps({"name": "boo", "recognition_type": "AWD", "is_numeric_score": True})

        # child user cannot
        self.login_as_child_member()
        response = self.client.patch(url, params, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.patch(url, params, content_type="application/json")
        assert response.status_code == 200


class TestGreenAssessmentUrlsPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.view = self.property_view_factory.get_property_view()
        self.green_assessment = GreenAssessment.objects.create(organization_id=self.org.id, is_numeric_score=True)
        self.property_assessment = GreenAssessmentProperty.objects.create(assessment=self.green_assessment, view=self.view)
        self.green_assessment_url = GreenAssessmentURL.objects.create(property_assessment=self.property_assessment)

    def test_green_assessment_urls_list(self):
        url = reverse_lazy("api:v3:green_assessment_urls-list") + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

    def test_green_assessment_urls_get(self):
        url = (
            reverse_lazy("api:v3:green_assessment_urls-detail", args=[self.green_assessment_url.pk])
            + "?organization_id="
            + str(self.org.id)
        )

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

    def test_green_assessment_urls_destroy(self):
        url = (
            reverse_lazy("api:v3:green_assessment_urls-detail", args=[self.green_assessment_url.pk])
            + "?organization_id="
            + str(self.org.id)
        )

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204

    def test_green_assessment_urls_create(self):
        url = reverse_lazy("api:v3:green_assessment_urls-list") + "?organization_id=" + str(self.org.id)
        params = json.dumps({"url": "http://whatever.com", "property_assessment": self.property_assessment.pk})

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 403
        assert not GreenAssessmentURL.objects.filter(url="http://whatever.com").exists()

        # root users can
        self.login_as_root_owner()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 201

    def test_green_assessment_urls_put(self):
        url = (
            reverse_lazy("api:v3:green_assessment_urls-detail", args=[self.green_assessment_url.pk])
            + "?organization_id="
            + str(self.org.id)
        )
        params = json.dumps({"url": "http://whatever.com", "property_assessment": self.property_assessment.pk})

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 200

    def test_green_assessment_urls_patch(self):
        url = (
            reverse_lazy("api:v3:green_assessment_urls-detail", args=[self.green_assessment_url.pk])
            + "?organization_id="
            + str(self.org.id)
        )
        params = json.dumps({"url": "http://whatever.com", "property_assessment": self.property_assessment.pk})

        # child user cannot
        self.login_as_child_member()
        response = self.client.patch(url, params, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.patch(url, params, content_type="application/json")
        assert response.status_code == 200


class TestGreenAssessmentPropertiesPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        self.view = self.property_view_factory.get_property_view()
        self.green_assessment = GreenAssessment.objects.create(organization_id=self.org.id, is_numeric_score=True)
        self.property_assessment = GreenAssessmentProperty.objects.create(assessment=self.green_assessment, view=self.view)
        self.green_assessment_url = GreenAssessmentURL.objects.create(property_assessment=self.property_assessment)

    def test_green_assessment_properties_list(self):
        url = reverse_lazy("api:v3:green_assessment_properties-list") + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

    def test_green_assessment_properties_get(self):
        url = (
            reverse_lazy("api:v3:green_assessment_properties-detail", args=[self.property_assessment.pk])
            + "?organization_id="
            + str(self.org.id)
        )

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

    def test_green_assessment_properties_bedes_format(self):
        url = (
            reverse_lazy("api:v3:green_assessment_properties-bedes-format", args=[self.property_assessment.pk])
            + "?organization_id="
            + str(self.org.id)
        )

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

    def test_green_assessment_properties_reso_format(self):
        url = (
            reverse_lazy("api:v3:green_assessment_properties-reso-format", args=[self.property_assessment.pk])
            + "?organization_id="
            + str(self.org.id)
        )

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

    def test_green_assessment_properties_destroy(self):
        url = (
            reverse_lazy("api:v3:green_assessment_properties-detail", args=[self.property_assessment.pk])
            + "?organization_id="
            + str(self.org.id)
        )

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204

    def test_green_assessment_properties_create(self):
        url = reverse_lazy("api:v3:green_assessment_properties-list") + "?organization_id=" + str(self.org.id)
        params = json.dumps({"assessment": self.green_assessment.pk, "view": self.view.pk})

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 403
        assert GreenAssessmentProperty.objects.filter(view=self.view).count() == 1

        # root users can
        self.login_as_root_owner()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 201
        assert GreenAssessmentProperty.objects.filter(view=self.view).count() == 2

    def test_green_assessment_properties_put(self):
        url = (
            reverse_lazy("api:v3:green_assessment_properties-detail", args=[self.property_assessment.pk])
            + "?organization_id="
            + str(self.org.id)
        )
        params = json.dumps({"assessment": self.green_assessment.pk, "view": self.view.pk})

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 200

    def test_green_assessment_properties_patch(self):
        url = (
            reverse_lazy("api:v3:green_assessment_properties-detail", args=[self.property_assessment.pk])
            + "?organization_id="
            + str(self.org.id)
        )
        params = json.dumps({"assessment": self.green_assessment.pk, "view": self.view.pk})

        # child user cannot
        self.login_as_child_member()
        response = self.client.patch(url, params, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.patch(url, params, content_type="application/json")
        assert response.status_code == 200


class TestGreenAssessmentCrossOrganizationReferences(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.view = self.property_view_factory.get_property_view()
        self.green_assessment = GreenAssessment.objects.create(organization_id=self.org.id, is_numeric_score=True)
        self.property_assessment = GreenAssessmentProperty.objects.create(assessment=self.green_assessment, view=self.view)
        self.green_assessment_url = GreenAssessmentURL.objects.create(property_assessment=self.property_assessment, url="http://a.com")

        # the root owner is only a viewer in another org
        self.other_org, _, _ = create_organization(self.superuser, "test-organization-b")
        self.other_org.add_member(self.root_owner_user, self.other_org.root.id, ROLE_VIEWER)
        self.other_view = self.property_view_factory.get_property_view(organization=self.other_org)
        self.other_assessment = GreenAssessment.objects.create(organization_id=self.other_org.id, is_numeric_score=True)
        self.other_property_assessment = GreenAssessmentProperty.objects.create(assessment=self.other_assessment, view=self.other_view)

        self.login_as_root_owner()

    def test_green_assessment_properties_create_rejects_other_organization_references(self):
        url = reverse_lazy("api:v3:green_assessment_properties-list") + "?organization_id=" + str(self.org.id)

        for assessment, view in [
            (self.other_assessment, self.other_view),
            (self.green_assessment, self.other_view),
            (self.other_assessment, self.view),
        ]:
            params = json.dumps({"assessment": assessment.pk, "view": view.pk})
            response = self.client.post(url, params, content_type="application/json")
            assert response.status_code == 403
        assert GreenAssessmentProperty.objects.count() == 2

        params = json.dumps({"assessment": self.green_assessment.pk, "view": self.view.pk})
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 201

    def test_green_assessment_properties_patch_rejects_other_organization_references(self):
        url = (
            reverse_lazy("api:v3:green_assessment_properties-detail", args=[self.property_assessment.pk])
            + "?organization_id="
            + str(self.org.id)
        )

        response = self.client.patch(url, json.dumps({"view": self.other_view.pk}), content_type="application/json")
        assert response.status_code == 403
        response = self.client.patch(url, json.dumps({"assessment": self.other_assessment.pk}), content_type="application/json")
        assert response.status_code == 403
        self.property_assessment.refresh_from_db()
        assert self.property_assessment.view_id == self.view.pk
        assert self.property_assessment.assessment_id == self.green_assessment.pk

        response = self.client.patch(url, json.dumps({"view": self.view.pk}), content_type="application/json")
        assert response.status_code == 200

    def test_green_assessment_urls_reject_other_organization_property_assessment(self):
        list_url = reverse_lazy("api:v3:green_assessment_urls-list") + "?organization_id=" + str(self.org.id)
        detail_url = (
            reverse_lazy("api:v3:green_assessment_urls-detail", args=[self.green_assessment_url.pk])
            + "?organization_id="
            + str(self.org.id)
        )
        params = json.dumps({"url": "http://b.com", "property_assessment": self.other_property_assessment.pk})

        response = self.client.post(list_url, params, content_type="application/json")
        assert response.status_code == 403
        response = self.client.patch(detail_url, params, content_type="application/json")
        assert response.status_code == 403
        assert not GreenAssessmentURL.objects.filter(property_assessment=self.other_property_assessment).exists()

        params = json.dumps({"url": "http://b.com", "property_assessment": self.property_assessment.pk})
        response = self.client.post(list_url, params, content_type="application/json")
        assert response.status_code == 201
        response = self.client.patch(detail_url, params, content_type="application/json")
        assert response.status_code == 200

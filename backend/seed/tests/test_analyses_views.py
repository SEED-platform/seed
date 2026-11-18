"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse_lazy
from django.utils import timezone as tz

from seed.landing.models import SEEDUser as User
from seed.models import Analysis, AnalysisEvent, AnalysisOutputFile, AnalysisPropertyView, Meter, MeterReading
from seed.test_helpers.fake import FakeCycleFactory, FakePropertyFactory, FakePropertyStateFactory, FakePropertyViewFactory
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class TestAnalysesView(TestCase):
    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
            "email": "test_user@demo.com",
            "first_name": "Test",
            "last_name": "User",
        }
        self.user = User.objects.create_user(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.org_b, self.org_user, _ = create_organization(self.user)
        self.client.login(**user_details)

        cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle_a = cycle_factory.get_cycle(name="Cycle A")
        self.cycle_b = cycle_factory.get_cycle(name="Cycle B")

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_a = self.property_factory.get_property()
        property_b = self.property_factory.get_property()

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        property_state_a = self.property_state_factory.get_property_state()
        property_state_b = self.property_state_factory.get_property_state()
        property_state_c = self.property_state_factory.get_property_state()
        property_state_d = self.property_state_factory.get_property_state()

        # create an analysis with two property views, each with the same property but a different cycle
        self.analysis_a = Analysis.objects.create(
            name="test a",
            service=Analysis.BSYNCR,
            status=Analysis.CREATING,
            user=self.user,
            organization=self.org,
            access_level_instance=self.org.root,
        )
        self.analysis_property_view_a = AnalysisPropertyView.objects.create(
            analysis=self.analysis_a, property=self.property_a, cycle=self.cycle_a, property_state=property_state_a
        )
        self.analysis_property_view_b = AnalysisPropertyView.objects.create(
            analysis=self.analysis_a, property=self.property_a, cycle=self.cycle_b, property_state=property_state_b
        )

        # create an analysis with two property views, each with the same cycle but a different property
        self.analysis_b = Analysis.objects.create(
            name="test b",
            service=Analysis.BSYNCR,
            status=Analysis.READY,
            user=self.user,
            organization=self.org,
            access_level_instance=self.org.root,
        )
        self.analysis_property_view_c = AnalysisPropertyView.objects.create(
            analysis=self.analysis_b, property=self.property_a, cycle=self.cycle_a, property_state=property_state_c
        )
        self.analysis_property_view_d = AnalysisPropertyView.objects.create(
            analysis=self.analysis_b, property=property_b, cycle=self.cycle_a, property_state=property_state_d
        )

        # create an analysis with no property views
        self.analysis_c = Analysis.objects.create(
            name="test c",
            service=Analysis.BSYNCR,
            status=Analysis.QUEUED,
            user=self.user,
            organization=self.org,
            access_level_instance=self.org.root,
        )

        # create an analysis with a different organization
        self.analysis_d = Analysis.objects.create(
            name="test d",
            service=Analysis.BSYNCR,
            status=Analysis.RUNNING,
            user=self.user,
            organization=self.org_b,
            access_level_instance=self.org.root,
        )

        # create an output file and add to 3 analysis property views
        self.analysis_output_file_a = AnalysisOutputFile.objects.create(
            file=SimpleUploadedFile("test file a", b"test file a contents"), content_type=AnalysisOutputFile.BUILDINGSYNC
        )
        self.analysis_output_file_a.analysis_property_views.add(self.analysis_property_view_a)
        self.analysis_output_file_a.analysis_property_views.add(self.analysis_property_view_b)
        self.analysis_output_file_a.analysis_property_views.add(self.analysis_property_view_c)

        # create an output file and add to 1 analysis property view
        self.analysis_output_file_b = AnalysisOutputFile.objects.create(
            file=SimpleUploadedFile("test file b", b"test file b contents"), content_type=AnalysisOutputFile.BUILDINGSYNC
        )
        self.analysis_output_file_b.analysis_property_views.add(self.analysis_property_view_a)

    def test_list_with_organization(self):
        response = self.client.get("/api/v3/analyses/?organization_id=" + str(self.org.pk))
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["analyses"]), 3)

        analysis_a = next((x for x in result["analyses"] if x["id"] == self.analysis_a.id), None)
        self.assertIsNotNone(analysis_a)
        self.assertEqual(analysis_a["number_of_analysis_property_views"], 2)
        self.assertEqual(len(analysis_a["cycles"]), 2)

        analysis_b = next((x for x in result["analyses"] if x["id"] == self.analysis_b.id), None)
        self.assertIsNotNone(analysis_b)
        self.assertEqual(analysis_b["number_of_analysis_property_views"], 2)
        self.assertEqual(len(analysis_b["cycles"]), 1)

        analysis_c = next((x for x in result["analyses"] if x["id"] == self.analysis_c.id), None)
        self.assertIsNotNone(analysis_c)
        self.assertEqual(analysis_c["number_of_analysis_property_views"], 0)
        self.assertEqual(len(analysis_c["cycles"]), 0)

    def test_list_with_property(self):
        response = self.client.get(
            "".join(
                [
                    "/api/v3/properties/",
                    str(self.property_a.pk),
                    "/analyses/?organization_id=",
                    str(self.org.pk),
                ]
            )
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["analyses"]), 2)

        analysis_a = next((x for x in result["analyses"] if x["id"] == self.analysis_a.id), None)
        self.assertIsNotNone(analysis_a)
        self.assertEqual(analysis_a["number_of_analysis_property_views"], 2)
        self.assertEqual(len(analysis_a["cycles"]), 2)

        analysis_b = next((x for x in result["analyses"] if x["id"] == self.analysis_b.id), None)
        self.assertIsNotNone(analysis_b)
        self.assertEqual(analysis_b["number_of_analysis_property_views"], 2)
        self.assertEqual(len(analysis_b["cycles"]), 1)

    def test_list_organization_missing(self):
        response = self.client.get("/api/v3/analyses/")
        self.assertEqual(response.status_code, 400)

    def test_retrieve_with_organization(self):
        response = self.client.get("".join(["/api/v3/analyses/", str(self.analysis_a.pk), "/?organization_id=", str(self.org.pk)]))
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["analysis"]["id"], self.analysis_a.id)
        self.assertEqual(result["analysis"]["number_of_analysis_property_views"], 2)
        self.assertEqual(len(result["analysis"]["cycles"]), 2)

    def test_retrieve_organization_missing(self):
        response = self.client.get("/api/v3/analyses/" + str(self.analysis_a.pk) + "/")
        self.assertEqual(response.status_code, 400)

    def test_list_views(self):
        response = self.client.get("".join(["/api/v3/analyses/", str(self.analysis_a.pk), "/views/?organization_id=", str(self.org.pk)]))
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["views"]), 2)

        view_a = next((x for x in result["views"] if x["id"] == self.analysis_property_view_a.id), None)
        self.assertIsNotNone(view_a)
        self.assertEqual(len(view_a["output_files"]), 2)

        view_b = next((x for x in result["views"] if x["id"] == self.analysis_property_view_b.id), None)
        self.assertIsNotNone(view_b)
        self.assertEqual(len(view_b["output_files"]), 1)

    def test_list_views_with_cycle(self):
        property = self.property_factory.get_property()

        property_state_1 = self.property_state_factory.get_property_state()
        analysis_x = Analysis.objects.create(
            name="test x",
            service=Analysis.BSYNCR,
            status=Analysis.QUEUED,
            user=self.user,
            organization=self.org,
            access_level_instance=self.org.root,
        )
        AnalysisPropertyView.objects.create(analysis=analysis_x, property=property, cycle=self.cycle_a, property_state=property_state_1)

        property_state_2 = self.property_state_factory.get_property_state()
        analysis_y = Analysis.objects.create(
            name="test y",
            service=Analysis.BSYNCR,
            status=Analysis.QUEUED,
            user=self.user,
            organization=self.org,
            access_level_instance=self.org.root,
        )
        AnalysisPropertyView.objects.create(analysis=analysis_y, property=property, cycle=self.cycle_b, property_state=property_state_2)

        response = self.client.get(f"/api/v3/properties/{property.pk}/analyses/?organization_id={self.org.pk}")
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(sorted([a["id"] for a in result["analyses"]]), [analysis_x.pk, analysis_y.pk])

        response = self.client.get(f"/api/v3/properties/{property.pk}/analyses/?organization_id={self.org.pk}&cycle_id={self.cycle_a.pk}")
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(sorted([a["id"] for a in result["analyses"]]), [analysis_x.pk])

    def test_retrieve_view_with_output_file(self):
        response = self.client.get(
            "".join(
                [
                    "/api/v3/analyses/",
                    str(self.analysis_b.pk),
                    "/views/",
                    str(self.analysis_property_view_c.pk),
                    "/?organization_id=",
                    str(self.org.pk),
                ]
            )
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["view"]["id"], self.analysis_property_view_c.id)
        self.assertEqual(len(result["view"]["output_files"]), 1)

    def test_retrieve_view_with_no_output_file(self):
        response = self.client.get(
            "".join(
                [
                    "/api/v3/analyses/",
                    str(self.analysis_b.pk),
                    "/views/",
                    str(self.analysis_property_view_d.pk),
                    "/?organization_id=",
                    str(self.org.pk),
                ]
            )
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["view"]["id"], self.analysis_property_view_d.id)
        self.assertEqual(len(result["view"]["output_files"]), 0)


class TestAnalysesViewPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        self.cycle = self.cycle_factory.get_cycle(name="Cycle A")
        self.root_analysis = Analysis.objects.create(
            name="test",
            service=Analysis.BSYNCR,
            status=Analysis.READY,
            user=self.root_owner_user,
            organization=self.org,
            access_level_instance=self.org.root,
            configuration={"model_type": "Simple Linear Regression"},
        )

        self.root_property = self.property_factory.get_property(access_level_instance=self.root_level_instance)
        self.child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)

        self.root_view = self.property_view_factory.get_property_view(prprty=self.root_property, cycle=self.cycle)
        self.child_view = self.property_view_factory.get_property_view(prprty=self.child_property, cycle=self.cycle)

        self.root_analysis_property_view = AnalysisPropertyView.objects.create(
            analysis=self.root_analysis, property=self.root_property, cycle=self.cycle, property_state=self.root_view.state
        )
        self.child_analysis_property_view = AnalysisPropertyView.objects.create(
            analysis=self.root_analysis, property=self.child_property, cycle=self.cycle, property_state=self.child_view.state
        )

        self.meter = Meter.objects.create(
            property=self.root_property,
            source=Meter.PORTFOLIO_MANAGER,
            source_id="Source ID",
            type=Meter.ELECTRICITY_GRID,
        )
        self.meter.save()
        MeterReading.objects.create(
            meter=self.meter, start_time=tz.now(), end_time=tz.now(), reading=12345, source_unit="kWh", conversion_factor=1.00
        )

    def test_analysis_list(self):
        url = reverse_lazy("api:v3:analyses-list") + "?organization_id=" + str(self.org.id)

        # child user can
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert len(response.json()["analyses"]) == 0
        assert response.status_code == 200

        # root users can
        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert len(response.json()["analyses"]) == 1
        assert response.status_code == 200

    def test_analysis_create(self):
        url = reverse_lazy("api:v3:analyses-list") + "?organization_id=" + str(self.org.id)
        params = json.dumps(
            {
                "service": "EUI",
                "property_view_ids": [self.root_view.id],
                "name": "boo",
                "access_level_instance_id": self.root_level_instance.id,
                "end_time": "2016-02-01 00:00:00",
                "configuration": {"select_meters": "all"},
            }
        )

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 404

        # root users can
        self.login_as_root_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 200

    def test_analysis_get(self):
        url = reverse_lazy("api:v3:analyses-detail", args=[self.root_analysis.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404

        # root users can
        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

    def test_analysis_destroy(self):
        url = reverse_lazy("api:v3:analyses-detail", args=[self.root_analysis.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 404

        # root users can
        self.login_as_root_member()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 200

    def test_analysis_start(self):
        url = reverse_lazy("api:v3:analyses-start", args=[self.root_analysis.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, content_type="application/json")
        assert response.status_code == 404

        # root users can
        self.login_as_root_member()
        response = self.client.post(url, content_type="application/json")
        assert response.status_code == 200

    @override_settings(SEED_BETTER_ENABLED=False)
    def test_better_analysis_start_is_rejected_when_disabled(self):
        self.root_analysis.service = Analysis.BETTER
        self.root_analysis.save()
        url = reverse_lazy("api:v3:analyses-start", args=[self.root_analysis.pk]) + "?organization_id=" + str(self.org.id)

        self.login_as_root_member()
        response = self.client.post(url, content_type="application/json")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["message"], "BETTER is disabled on this deployment")

    def test_analysis_stop(self):
        url = reverse_lazy("api:v3:analyses-stop", args=[self.root_analysis.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, content_type="application/json")
        assert response.status_code == 404

        # root users can
        self.login_as_root_member()
        response = self.client.post(url, content_type="application/json")
        assert response.status_code == 200

    def test_analysis_progress_key(self):
        url = reverse_lazy("api:v3:analyses-progress-key", args=[self.root_analysis.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404

        # root users can
        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

    def test_analysis_stats(self):
        url = reverse_lazy("api:v3:analyses-stats") + "?organization_id=" + str(self.org.id) + "&cycle_id=" + str(self.cycle.pk)

        # child user can
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert response.json()["total_records"] == 1

        # root users can
        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert response.json()["total_records"] == 2

    def test_analysis_list_only_includes_views_of_listed_analyses(self):
        child_analysis = Analysis.objects.create(
            name="child",
            service=Analysis.BSYNCR,
            status=Analysis.READY,
            user=self.root_owner_user,
            organization=self.org,
            access_level_instance=self.child_level_instance,
            configuration={"model_type": "Simple Linear Regression"},
        )
        child_analysis_property_view = AnalysisPropertyView.objects.create(
            analysis=child_analysis,
            property=self.child_property,
            cycle=self.cycle,
            property_state=self.property_state_factory.get_property_state(),
        )
        url = reverse_lazy("api:v3:analyses-list") + "?organization_id=" + str(self.org.id)

        # child user only gets the views of the child analysis, not those of the root analysis
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert [analysis["id"] for analysis in response.json()["analyses"]] == [child_analysis.id]
        assert [view["id"] for view in response.json()["views"]] == [child_analysis_property_view.id]
        assert list(response.json()["original_views"]) == [str(child_analysis_property_view.id)]

        # root users get the views of all analyses
        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert {view["id"] for view in response.json()["views"]} == {
            child_analysis_property_view.id,
            self.root_analysis_property_view.id,
            self.child_analysis_property_view.id,
        }

    def test_analysis_list_parses_include_views(self):
        url = reverse_lazy("api:v3:analyses-list") + "?organization_id=" + str(self.org.id)
        self.login_as_root_member()

        for include_views, expected in [(None, True), ("true", True), ("True", True), ("false", False), ("False", False)]:
            query = "" if include_views is None else f"&include_views={include_views}"
            response = self.client.get(url + query)
            assert response.status_code == 200
            assert ("views" in response.json()) is expected

    @mock.patch("seed.views.v3.analyses.AnalysisPipeline.factory")
    def test_analysis_create_rejects_property_views_outside_access_level(self, mock_factory):
        mock_factory.return_value.prepare_analysis.return_value = {"progress_key": "key"}
        url = reverse_lazy("api:v3:analyses-list") + "?organization_id=" + str(self.org.id)

        def params(property_view_id):
            return json.dumps(
                {
                    "service": "EUI",
                    "property_view_ids": [property_view_id],
                    "name": f"analysis of {property_view_id}",
                    "access_level_instance_id": self.child_level_instance.id,
                    "configuration": {"select_meters": "all"},
                }
            )

        # child user cannot analyze a property outside their access level instance
        self.login_as_child_member()
        response = self.client.post(url, params(self.root_view.id), content_type="application/json")
        assert response.status_code == 404
        assert not Analysis.objects.filter(name=f"analysis of {self.root_view.id}").exists()
        mock_factory.assert_not_called()

        # root users cannot analyze it within a child-level analysis either
        self.login_as_root_member()
        response = self.client.post(url, params(self.root_view.id), content_type="application/json")
        assert response.status_code == 404

        # nor analyze another org's property within a root-level analysis
        other_org, _, _ = create_organization(self.root_owner_user, "other org")
        other_org_view = FakePropertyViewFactory(organization=other_org).get_property_view()
        other_org_params = json.loads(params(other_org_view.id))
        other_org_params["access_level_instance_id"] = self.root_level_instance.id
        response = self.client.post(url, json.dumps(other_org_params), content_type="application/json")
        assert response.status_code == 404
        assert not Analysis.objects.filter(name=f"analysis of {other_org_view.id}").exists()
        mock_factory.assert_not_called()

        # child user can analyze their own property
        self.login_as_child_member()
        response = self.client.post(url, params(self.child_view.id), content_type="application/json")
        assert response.status_code == 200
        assert Analysis.objects.filter(name=f"analysis of {self.child_view.id}").exists()
        mock_factory.return_value.prepare_analysis.assert_called_once_with([self.child_view.id], start_analysis=False)

    @mock.patch("seed.views.v3.analyses.AnalysisPipeline.factory")
    def test_analysis_create_leaves_missing_property_views_to_the_pipeline(self, mock_factory):
        mock_factory.return_value.prepare_analysis.return_value = {"progress_key": "key"}
        url = reverse_lazy("api:v3:analyses-list") + "?organization_id=" + str(self.org.id)
        stale_view = self.property_view_factory.get_property_view(prprty=self.child_property, cycle=self.cycle_factory.get_cycle(name="B"))
        stale_view_id = stale_view.id
        stale_view.delete()
        params = json.dumps(
            {
                "service": "EUI",
                "property_view_ids": [self.child_view.id, stale_view_id],
                "name": "with stale view",
                "access_level_instance_id": self.child_level_instance.id,
                "configuration": {"select_meters": "all"},
            }
        )

        # IDs that don't exist are still passed on, to be reported as analysis messages
        self.login_as_child_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 200
        analysis = Analysis.objects.get(name="with stale view")
        assert list(AnalysisEvent.objects.filter(analysis=analysis).values_list("property_id", flat=True)) == [self.child_property.id]
        mock_factory.return_value.prepare_analysis.assert_called_once_with([self.child_view.id, stale_view_id], start_analysis=False)

    @mock.patch("seed.views.v3.analyses.AnalysisPipeline.factory")
    def test_analysis_create_parses_start_analysis(self, mock_factory):
        mock_factory.return_value.prepare_analysis.return_value = {"progress_key": "key"}
        params = json.dumps(
            {
                "service": "EUI",
                "property_view_ids": [self.root_view.id],
                "name": "boo",
                "access_level_instance_id": self.root_level_instance.id,
                "configuration": {"select_meters": "all"},
            }
        )
        self.login_as_root_member()

        for start_analysis, expected in [("false", False), ("False", False), ("true", True), ("True", True)]:
            url = reverse_lazy("api:v3:analyses-list") + f"?organization_id={self.org.id}&start_analysis={start_analysis}"
            response = self.client.post(url, params, content_type="application/json")
            assert response.status_code == 200
            mock_factory.return_value.prepare_analysis.assert_called_with([self.root_view.id], start_analysis=expected)

    def test_analysis_create_requires_name(self):
        url = reverse_lazy("api:v3:analyses-list") + "?organization_id=" + str(self.org.id)
        params = json.dumps(
            {
                "service": "EUI",
                "property_view_ids": [self.root_view.id],
                "access_level_instance_id": self.root_level_instance.id,
                "configuration": {"select_meters": "all"},
            }
        )

        self.login_as_root_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.json()["status"] == "error"
        assert "name" in response.json()["errors"]

    def test_analysis_used_columns_includes_property_and_taxlot_columns(self):
        taxlot = self.taxlot_factory.get_taxlot(access_level_instance=self.root_level_instance)
        self.taxlot_view_factory.get_taxlot_view(taxlot=taxlot, cycle=self.cycle)
        url = reverse_lazy("api:v3:analyses-used-columns") + "?organization_id=" + str(self.org.id)

        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        used_columns = {(column["table_name"], column["column_name"]) for column in response.json()["columns"]}
        # property columns with data are not dropped when there are also taxlots
        assert ("PropertyState", "year_built") in used_columns
        assert ("TaxLotState", "jurisdiction_tax_lot_id") in used_columns


class TestAnalysesViewViewPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        self.cycle = self.cycle_factory.get_cycle(name="Cycle A")
        self.root_analysis = Analysis.objects.create(
            name="test",
            service=Analysis.BSYNCR,
            status=Analysis.READY,
            user=self.root_owner_user,
            organization=self.org,
            access_level_instance=self.org.root,
            configuration={"model_type": "Simple Linear Regression"},
        )

        self.root_property = self.property_factory.get_property(access_level_instance=self.root_level_instance)
        self.child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)

        self.root_view = self.property_view_factory.get_property_view(prprty=self.root_property, cycle=self.cycle)
        self.child_view = self.property_view_factory.get_property_view(prprty=self.child_property, cycle=self.cycle)

        self.root_analysis_property_view = AnalysisPropertyView.objects.create(
            analysis=self.root_analysis, property=self.root_property, cycle=self.cycle, property_state=self.root_view.state
        )
        self.child_analysis_property_view = AnalysisPropertyView.objects.create(
            analysis=self.root_analysis, property=self.child_property, cycle=self.cycle, property_state=self.child_view.state
        )

        self.meter = Meter.objects.create(
            property=self.root_property,
            source=Meter.PORTFOLIO_MANAGER,
            source_id="Source ID",
            type=Meter.ELECTRICITY_GRID,
        )
        self.meter.save()
        MeterReading.objects.create(
            meter=self.meter, start_time=tz.now(), end_time=tz.now(), reading=12345, source_unit="kWh", conversion_factor=1.00
        )

    def test_analysis_view_lit(self):
        url = reverse_lazy("api:v3:analysis-views-list", args=[self.root_analysis.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404

        # root users can
        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

    def test_analysis_view_get(self):
        url = reverse_lazy("api:v3:analysis-views-detail", args=[self.root_analysis.pk, self.root_analysis_property_view.pk])
        url += "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404

        # root users can
        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

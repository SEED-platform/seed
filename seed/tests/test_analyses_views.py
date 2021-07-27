# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
import json

from seed.landing.models import SEEDUser as User
from seed.models import (
    Analysis,
    AnalysisPropertyView,
    AnalysisOutputFile
)
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory
)
from seed.utils.organizations import create_organization


class TestAnalysesView(TestCase):

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Test',
            'last_name': 'User',
        }
        self.user = User.objects.create_user(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.org_b, self.org_user, _ = create_organization(self.user)
        self.client.login(**user_details)

        cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        cycle_a = cycle_factory.get_cycle(name="Cycle A")
        cycle_b = cycle_factory.get_cycle(name="Cycle B")

        property_factory = FakePropertyFactory(organization=self.org)
        self.property_a = property_factory.get_property()
        property_b = property_factory.get_property()

        property_state_factory = FakePropertyStateFactory(organization=self.org)
        property_state_a = property_state_factory.get_property_state()
        property_state_b = property_state_factory.get_property_state()
        property_state_c = property_state_factory.get_property_state()
        property_state_d = property_state_factory.get_property_state()

        # create an analysis with two property views, each with the same property but a different cycle
        self.analysis_a = Analysis.objects.create(
            name='test a',
            service=Analysis.BSYNCR,
            status=Analysis.CREATING,
            user=self.user,
            organization=self.org
        )
        self.analysis_property_view_a = AnalysisPropertyView.objects.create(
            analysis=self.analysis_a,
            property=self.property_a,
            cycle=cycle_a,
            property_state=property_state_a
        )
        self.analysis_property_view_b = AnalysisPropertyView.objects.create(
            analysis=self.analysis_a,
            property=self.property_a,
            cycle=cycle_b,
            property_state=property_state_b
        )

        # create an analysis with two property views, each with the same cycle but a different property
        self.analysis_b = Analysis.objects.create(
            name='test b',
            service=Analysis.BSYNCR,
            status=Analysis.READY,
            user=self.user,
            organization=self.org
        )
        self.analysis_property_view_c = AnalysisPropertyView.objects.create(
            analysis=self.analysis_b,
            property=self.property_a,
            cycle=cycle_a,
            property_state=property_state_c
        )
        self.analysis_property_view_d = AnalysisPropertyView.objects.create(
            analysis=self.analysis_b,
            property=property_b,
            cycle=cycle_a,
            property_state=property_state_d
        )

        # create an analysis with no property views
        self.analysis_c = Analysis.objects.create(
            name='test c',
            service=Analysis.BSYNCR,
            status=Analysis.QUEUED,
            user=self.user,
            organization=self.org
        )

        # create an analysis with a different organization
        self.analysis_d = Analysis.objects.create(
            name='test d',
            service=Analysis.BSYNCR,
            status=Analysis.RUNNING,
            user=self.user,
            organization=self.org_b
        )

        # create an output file and add to 3 analysis property views
        self.analysis_output_file_a = AnalysisOutputFile.objects.create(
            file=SimpleUploadedFile('test file a', b'test file a contents'),
            content_type=AnalysisOutputFile.BUILDINGSYNC
        )
        self.analysis_output_file_a.analysis_property_views.add(self.analysis_property_view_a)
        self.analysis_output_file_a.analysis_property_views.add(self.analysis_property_view_b)
        self.analysis_output_file_a.analysis_property_views.add(self.analysis_property_view_c)

        # create an output file and add to 1 analysis property view
        self.analysis_output_file_b = AnalysisOutputFile.objects.create(
            file=SimpleUploadedFile('test file b', b'test file b contents'),
            content_type=AnalysisOutputFile.BUILDINGSYNC
        )
        self.analysis_output_file_b.analysis_property_views.add(self.analysis_property_view_a)

    def test_list_with_organization(self):
        response = self.client.get('/api/v3/analyses/?organization_id=' + str(self.org.pk))
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['analyses']), 3)

        analysis_a = next((x for x in result['analyses'] if x['id'] == self.analysis_a.id), None)
        self.assertIsNotNone(analysis_a)
        self.assertEqual(analysis_a['number_of_analysis_property_views'], 2)
        self.assertEqual(len(analysis_a['cycles']), 2)

        analysis_b = next((x for x in result['analyses'] if x['id'] == self.analysis_b.id), None)
        self.assertIsNotNone(analysis_b)
        self.assertEqual(analysis_b['number_of_analysis_property_views'], 2)
        self.assertEqual(len(analysis_b['cycles']), 1)

        analysis_c = next((x for x in result['analyses'] if x['id'] == self.analysis_c.id), None)
        self.assertIsNotNone(analysis_c)
        self.assertEqual(analysis_c['number_of_analysis_property_views'], 0)
        self.assertEqual(len(analysis_c['cycles']), 0)

    def test_list_with_property(self):
        response = self.client.get("".join([
            '/api/v3/analyses/?organization_id=',
            str(self.org.pk),
            '&property_id=',
            str(self.property_a.pk)
        ]))
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['analyses']), 2)

        analysis_a = next((x for x in result['analyses'] if x['id'] == self.analysis_a.id), None)
        self.assertIsNotNone(analysis_a)
        self.assertEqual(analysis_a['number_of_analysis_property_views'], 2)
        self.assertEqual(len(analysis_a['cycles']), 2)

        analysis_b = next((x for x in result['analyses'] if x['id'] == self.analysis_b.id), None)
        self.assertIsNotNone(analysis_b)
        self.assertEqual(analysis_b['number_of_analysis_property_views'], 1)
        self.assertEqual(len(analysis_b['cycles']), 1)

    def test_list_organization_missing(self):
        response = self.client.get('/api/v3/analyses/')
        self.assertEqual(response.status_code, 400)

    def test_retrieve_with_organization(self):
        response = self.client.get("".join([
            '/api/v3/analyses/',
            str(self.analysis_a.pk),
            '/?organization_id=',
            str(self.org.pk)
        ]))
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['analysis']['id'], self.analysis_a.id)
        self.assertEqual(result['analysis']['number_of_analysis_property_views'], 2)
        self.assertEqual(len(result['analysis']['cycles']), 2)

    def test_retrieve_organization_missing(self):
        response = self.client.get('/api/v3/analyses/' + str(self.analysis_a.pk) + '/')
        self.assertEqual(response.status_code, 400)

    def test_list_views(self):
        response = self.client.get("".join([
            '/api/v3/analyses/',
            str(self.analysis_a.pk),
            '/views/?organization_id=',
            str(self.org.pk)
        ]))
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['views']), 2)

        view_a = next((x for x in result['views'] if x['id'] == self.analysis_property_view_a.id), None)
        self.assertIsNotNone(view_a)
        self.assertEqual(len(view_a['output_files']), 2)

        view_b = next((x for x in result['views'] if x['id'] == self.analysis_property_view_b.id), None)
        self.assertIsNotNone(view_b)
        self.assertEqual(len(view_b['output_files']), 1)

    def test_retrieve_view_with_output_file(self):
        response = self.client.get("".join([
            '/api/v3/analyses/',
            str(self.analysis_b.pk),
            '/views/',
            str(self.analysis_property_view_c.pk),
            '/?organization_id=',
            str(self.org.pk)
        ]))
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['view']['id'], self.analysis_property_view_c.id)
        self.assertEqual(len(result['view']['output_files']), 1)

    def test_retrieve_view_with_no_output_file(self):
        response = self.client.get("".join([
            '/api/v3/analyses/',
            str(self.analysis_b.pk),
            '/views/',
            str(self.analysis_property_view_d.pk),
            '/?organization_id=',
            str(self.org.pk)
        ]))
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['view']['id'], self.analysis_property_view_d.id)
        self.assertEqual(len(result['view']['output_files']), 0)

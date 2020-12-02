# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.test import TestCase
import json

from seed.landing.models import SEEDUser as User
from seed.models import (
    Analysis,
    AnalysisPropertyView
)
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory
)
from seed.utils.organizations import create_organization


class TestAnalyses(TestCase):

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
            name = 'test a',
            service = 1,
            status = 10,
            user = self.user,
            organization = self.org
        )
        property_view_a = AnalysisPropertyView.objects.create(
            analysis = self.analysis_a,
            property = self.property_a,
            cycle = cycle_a,
            property_state=property_state_a
        )
        property_view_b = AnalysisPropertyView.objects.create(
            analysis = self.analysis_a,
            property = self.property_a,
            cycle = cycle_b,
            property_state=property_state_b
        )

        # create an analysis with two property views, each with the same cycle but a different property
        self.analysis_b = Analysis.objects.create(
            name = 'test b',
            service = 1,
            status = 20,
            user = self.user,
            organization = self.org
        )
        property_view_c = AnalysisPropertyView.objects.create(
            analysis = self.analysis_b,
            property = self.property_a,
            cycle = cycle_a,
            property_state=property_state_c
        )
        property_view_d = AnalysisPropertyView.objects.create(
            analysis = self.analysis_b,
            property = property_b,
            cycle = cycle_a,
            property_state=property_state_d
        )

        # create an analysis with no property views
        self.analysis_c = Analysis.objects.create(
            name = 'test c',
            service = 1,
            status = 10,
            user = self.user,
            organization = self.org
        )

        # create an analysis with a different organization
        self.analysis_d = Analysis.objects.create(
            name = 'test d',
            service = 1,
            status = 10,
            user = self.user,
            organization = self.org_b
        )

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

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.test import TestCase
from quantityfield.units import ureg

from seed.landing.models import SEEDUser as User
from seed.models import AnalysisPropertyView, Analysis
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyViewFactory,
    FakeAnalysisFactory,
)
from seed.utils.organizations import create_organization


class TestAnalysisPropertyViews(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Test',
            'last_name': 'User',
        }
        self.user = User.objects.create_user(**user_details)
        self.org_a, _, _ = create_organization(self.user)
        self.org_b, _, _ = create_organization(self.user)

        cycle_a = FakeCycleFactory(organization=self.org_a, user=self.user).get_cycle(name="Cycle Org A")
        cycle_b = FakeCycleFactory(organization=self.org_b, user=self.user).get_cycle(name="Cycle Org B")

        self.analysis_a = (
            FakeAnalysisFactory(organization=self.org_a, user=self.user)
            .get_analysis(
                name='Quite neat',
                service=Analysis.BSYNCR,
                configuration={'model_type': 'Simple Linear Regression'}
            )
        )

        view_factory_a = FakePropertyViewFactory(cycle=cycle_a, organization=self.org_a, user=self.user)
        self.property_views_a = [
            view_factory_a.get_property_view(
                # override unitted fields so that hashes are correct
                site_eui=ureg.Quantity(
                    float(view_factory_a.fake.random_int(min=50, max=600)),
                    "kBtu / foot ** 2 / year"
                ),
                gross_floor_area=ureg.Quantity(
                    float(view_factory_a.fake.random_number(digits=6)),
                    "foot ** 2"
                ),
            )
            for i in range(2)]

        view_factory_b = FakePropertyViewFactory(cycle=cycle_b, organization=self.org_b, user=self.user)
        self.property_views_b = [
            view_factory_b.get_property_view(
                # override unitted fields so that hashes are correct
                site_eui=ureg.Quantity(
                    float(view_factory_b.fake.random_int(min=50, max=600)),
                    "kBtu / foot ** 2 / year"
                ),
                gross_floor_area=ureg.Quantity(
                    float(view_factory_b.fake.random_number(digits=6)),
                    "foot ** 2"
                ),
            )
            for i in range(2)]

    def test_batch_create_is_successful_with_valid_inputs(self):
        # Act
        analysis_view_ids, failures = AnalysisPropertyView.batch_create(
            analysis_id=self.analysis_a.id,
            property_view_ids=[p.id for p in self.property_views_a],
        )
        analysis_view_ids = analysis_view_ids.values()

        # Assert
        self.assertEqual(0, len(failures))
        self.assertEqual(len(self.property_views_a), len(analysis_view_ids))
        analysis_views = AnalysisPropertyView.objects.filter(id__in=analysis_view_ids, analysis=self.analysis_a)
        self.assertEqual(
            len(analysis_view_ids),
            analysis_views.count()
        )

        # check that the PropertyState has the same content, but is not the same row
        original_property_view = self.property_views_a[0]
        analysis_property_view = AnalysisPropertyView.objects.get(
            property=original_property_view.property,
            cycle=original_property_view.cycle,
        )
        self.assertNotEqual(
            original_property_view.state.id,
            analysis_property_view.property_state.id
        )
        self.assertEqual(
            original_property_view.state.hash_object,
            analysis_property_view.property_state.hash_object
        )

    def test_batch_create_removes_duplicate_ids(self):
        # Setup
        # create an IDs list with a duplicate
        property_view_ids = [p.id for p in self.property_views_a]
        property_view_ids.append(self.property_views_a[0].id)

        # Act
        analysis_view_ids, failures = AnalysisPropertyView.batch_create(
            analysis_id=self.analysis_a.id,
            property_view_ids=property_view_ids,
        )
        analysis_view_ids = analysis_view_ids.values()

        # Assert
        self.assertEqual(0, len(failures))
        self.assertEqual(len(set(property_view_ids)), len(analysis_view_ids))
        self.assertEqual(
            len(analysis_view_ids),
            AnalysisPropertyView.objects.filter(id__in=analysis_view_ids).count()
        )

    def test_batch_create_returns_failures_when_property_views_dont_exist(self):
        # Setup
        bad_property_view_ids = [-1, -2, -3]

        # Act
        analysis_view_ids, failures = AnalysisPropertyView.batch_create(
            analysis_id=self.analysis_a.id,
            property_view_ids=bad_property_view_ids,
        )
        analysis_view_ids = analysis_view_ids.values()

        # Assert
        self.assertEqual(0, len(analysis_view_ids))
        failure_ids = [failure.property_view_id for failure in failures]
        self.assertEqual(set(failure_ids), set(bad_property_view_ids))
        self.assertEqual(failures[0].message, 'No such PropertyView')

    def test_batch_create_returns_failures_for_property_views_outside_of_org(self):
        # Setup
        # create an IDs list with that includes property ids from different org
        property_view_ids = [p.id for p in self.property_views_a]
        property_view_ids += [p.id for p in self.property_views_b]

        # Act
        analysis_view_ids, failures = AnalysisPropertyView.batch_create(
            analysis_id=self.analysis_a.id,
            property_view_ids=property_view_ids,
        )
        analysis_view_ids = analysis_view_ids.values()

        # Assert
        self.assertEqual(len(analysis_view_ids), len(self.property_views_a))
        failure_ids = [failure.property_view_id for failure in failures]
        # the failures should all be from other org
        self.assertEqual(set(failure_ids), set([p.id for p in self.property_views_b]))
        self.assertEqual(failures[0].message, 'No such PropertyView')

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pipermerriam@gmail.com>'
"""
"""
Unit tests for seed/views/labels.py
"""

from unittest import skip

from django.test import TestCase

from seed.factory import SEEDFactory
from seed.landing.models import SEEDUser as User
from seed.models import (
    CanonicalBuilding,
    Project,
)
from seed.tasks import (
    add_buildings,
)
from seed.utils.organizations import (
    create_organization,
)


class TestAddBuildingsToProjectTask(TestCase):

    def get_filter_params(self, project):
        return {
            "project_slug": project.slug,
            "selected_buildings": [],
            "select_all_checkbox": False,
            "filter_params": {
                # "canonical_building__labels": [53],
            },
            "order_by": "",
            "sort_reverse": False,
            "project_loading_cache_key": "SEED_PROJECT_ADDING_BUILDINGS_PERCENTAGE_{}".format(project.slug),
        }

    @staticmethod
    def generate_buildings(organization, count):
        buildings = []

        for i in range(count):
            tax_lot_id = str(i).zfill(5)
            bs = SEEDFactory.building_snapshot(
                canonical_building=CanonicalBuilding.objects.create(active=True),
                tax_lot_id=tax_lot_id,
                super_organization=organization,
            )
            bs.canonical_building.canonical_snapshot = bs
            bs.canonical_building.save()
            buildings.append(bs)

        return buildings

    @skip("Fix for new data model")
    def test_adding_buildings_with_select_all(self):
        """
        Ensure that labels are not actually paginated.
        """
        user = User.objects.create_superuser(
            email='test_user@demo.com',
            username='test_user@demo.com',
            password='secret',
        )
        organization, _, _ = create_organization(user, "test-organization")
        project = Project.objects.create(
            name='test-org-1',
            super_organization=organization,
            owner=user,
        )

        self.generate_buildings(organization, 10)

        self.assertFalse(project.building_snapshots.exists())

        params = self.get_filter_params(project)
        params['select_all_checkbox'] = True

        add_buildings(project.slug, params, user.pk)

        self.assertEqual(project.building_snapshots.count(), 10)

    @skip("Fix for new data model")
    def test_adding_buildings_with_individual_selection(self):
        """
        Ensure that labels are not actually paginated.
        """
        user = User.objects.create_superuser(
            email='test_user@demo.com',
            username='test_user@demo.com',
            password='secret',
        )
        organization, _, _ = create_organization(user, "test-organization")
        project = Project.objects.create(
            name='test-org-1',
            super_organization=organization,
            owner=user,
        )

        buildings = self.generate_buildings(organization, 10)

        self.assertFalse(project.building_snapshots.exists())

        selected_buildings = [b.pk for b in buildings if b.pk % 2 == 0]
        self.assertEqual(len(selected_buildings), 5)

        params = self.get_filter_params(project)
        params['selected_buildings'] = selected_buildings

        add_buildings(project.slug, params, user.pk)

        self.assertEqual(project.building_snapshots.count(), 5)

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.core.urlresolvers import reverse_lazy
from django.test import TestCase

from seed.audit_logs.models import AuditLog
from seed.data_importer.models import ImportRecord
from seed.factory import SEEDFactory
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import (
    ROLE_MEMBER,
    ROLE_OWNER,
    ROLE_VIEWER,
    OrganizationUser,
    Organization,
)
from seed.models import CanonicalBuilding, BuildingSnapshot
from seed.tests.util import FakeRequest


class DeleteViewTests(TestCase):
    """
    Tests of the SEED delete view
    """

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Johnny',
            'last_name': 'Energy',
        }
        self.user = User.objects.create_user(**user_details)
        self.org = Organization.objects.create(name='my org')
        self.org.add_member(self.user)
        self.client.login(**user_details)
        self.fake_request = FakeRequest(user=self.user)
        # arrange
        self.NUMBER_ACTIVE = 50
        NUMBER_INACTIVE = 25
        NUMBER_WITHOUT_CANONICAL = 5
        for i in range(self.NUMBER_ACTIVE):
            cb = CanonicalBuilding(active=True)
            cb.save()
            b = SEEDFactory.building_snapshot(canonical_building=cb)
            cb.canonical_snapshot = b
            cb.save()
            b.super_organization = self.org
            b.save()
        for i in range(NUMBER_INACTIVE):
            cb = CanonicalBuilding(active=False)
            cb.save()
            b = SEEDFactory.building_snapshot(canonical_building=cb)
            cb.canonical_snapshot = b
            cb.save()
            b.super_organization = self.org
            b.save()
        for i in range(NUMBER_WITHOUT_CANONICAL):
            b = SEEDFactory.building_snapshot()
            b.super_organization = self.org
            b.save()

    def _set_role_level(self, role_level, user=None, org=None):
        """helper to set an org user's role level"""
        if user is None:
            user = self.user
        if org is None:
            org = self.org
        ou = OrganizationUser.objects.get(user=user, organization=org)
        ou.role_level = role_level
        ou.save()

    def test_delete_buildings(self):
        """tests delete_buildings"""
        # arrange: standard case, delete all buildings
        self._set_role_level(ROLE_MEMBER)
        self.assertEqual(BuildingSnapshot.objects.filter(
            canonicalbuilding__active=True).count(),
            self.NUMBER_ACTIVE
        )

        # act
        resp = self.client.delete(
            reverse_lazy("seed:delete_buildings"),
            data=json.dumps(
                {
                    'organization_id': self.org.id,
                    'search_payload': {
                        'select_all_checkbox': True
                    }
                }
            ),
            content_type='application/json',
        )

        # assert
        self.assertDictEqual(json.loads(resp.content), {'status': 'success'})
        self.assertEqual(BuildingSnapshot.objects.filter(
            canonicalbuilding__active=True).count(),
            0
        )
        self.assertEqual(
            AuditLog.objects.filter(action='delete_building').count(),
            self.NUMBER_ACTIVE
        )

    def test_delete_buildings_owner(self):
        """tests delete_buildings for owner role"""
        # arrange: standard case, delete all buildings
        self._set_role_level(ROLE_OWNER)
        self.assertEqual(BuildingSnapshot.objects.filter(
            canonicalbuilding__active=True).count(),
            self.NUMBER_ACTIVE
        )

        # act
        resp = self.client.delete(
            reverse_lazy("seed:delete_buildings"),
            data=json.dumps(
                {
                    'organization_id': self.org.id,
                    'search_payload': {
                        'select_all_checkbox': True
                    }
                }
            ),
            content_type='application/json',
        )

        # assert
        self.assertDictEqual(json.loads(resp.content), {'status': 'success'})
        self.assertEqual(BuildingSnapshot.objects.filter(
            canonicalbuilding__active=True).count(),
            0
        )

    def test_delete_buildings_viewer(self):
        """tests delete_buildings for viewer role"""
        # arrange: standard case, try to delete all buildings, get an error
        self._set_role_level(ROLE_VIEWER)
        self.assertEqual(BuildingSnapshot.objects.filter(
            canonicalbuilding__active=True).count(),
            self.NUMBER_ACTIVE
        )

        # act
        resp = self.client.delete(
            reverse_lazy("seed:delete_buildings"),
            data=json.dumps(
                {
                    'organization_id': self.org.id,
                    'search_payload': {
                        'select_all_checkbox': True
                    }
                }
            ),
            content_type='application/json',
        )

        # assert
        self.assertDictEqual(json.loads(resp.content), {
            'status': 'error',
            'message': 'Permission denied'
        })
        # no buildings deleted
        self.assertEqual(BuildingSnapshot.objects.filter(
            canonicalbuilding__active=True).count(),
            self.NUMBER_ACTIVE
        )

    def test_delete_buildings_selected_buildings(self):
        """tests delete_buildings for selected_buildings"""
        # arrange: standard case, try to delete 10 buildings
        self._set_role_level(ROLE_MEMBER)
        self.assertEqual(BuildingSnapshot.objects.filter(
            canonicalbuilding__active=True).count(),
            self.NUMBER_ACTIVE
        )
        ids = BuildingSnapshot.objects.filter(
            canonicalbuilding__active=True
        ).values_list('pk', flat=True)[:10]

        # act
        resp = self.client.delete(
            reverse_lazy("seed:delete_buildings"),
            data=json.dumps(
                {
                    'organization_id': self.org.id,
                    'search_payload': {
                        'select_all_checkbox': False,
                        'selected_buildings': list(ids),
                    }

                }
            ),
            content_type='application/json',
        )

        # assert
        self.assertDictEqual(json.loads(resp.content), {'status': 'success'})
        # check that we have 10 less active buildings
        self.assertEqual(BuildingSnapshot.objects.filter(
            canonicalbuilding__active=True).count(),
            self.NUMBER_ACTIVE - 10
        )
        # check that the 10 buildings are inactive
        self.assertEqual(
            BuildingSnapshot.objects.filter(
                canonicalbuilding__active=False,
                pk__in=list(ids)
            ).count(),
            10
        )

    def test_delete_dataset(self):
        """tests delete_dataset"""
        # arrange
        dataset = ImportRecord.objects.create(
            name='dataset',
            super_organization=self.org,
        )

        # act
        resp = self.client.delete(
            reverse_lazy("apiv2:datasets-detail", args=[dataset.pk]) + '?organization_id=' + str(self.org.id),
            content_type='application/json',
        )

        # assert
        self.assertDictEqual(json.loads(resp.content), {'status': 'success'})
        # dataset should be deleted
        self.assertFalse(ImportRecord.objects.filter(pk=dataset.pk).exists())

    def test_delete_dataset_viewer(self):
        """tests that an Org User with role viewer cannot delete a dataset"""
        # arrange
        self._set_role_level(ROLE_VIEWER)
        dataset = ImportRecord.objects.create(
            name='dataset',
            super_organization=self.org,
        )

        # act
        resp = self.client.delete(
            reverse_lazy("apiv2:datasets-detail", args=[dataset.pk]) + '?organization_id=' + str(self.org.id),
            content_type='application/json',
        )

        # assert
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Permission denied'
            }
        )
        # dataset should still exist
        self.assertTrue(ImportRecord.objects.filter(pk=dataset.pk).exists())

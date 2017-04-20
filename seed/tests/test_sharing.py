# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
Tests related to sharing of data between users, orgs, suborgs, etc.
"""
import json
from unittest import skip

from django.core.urlresolvers import reverse_lazy
from django.test import TestCase

from seed.factory import SEEDFactory
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import (
    Organization,
    ROLE_OWNER,
    ExportableField,
    ROLE_MEMBER
)
from seed.models import (
    CanonicalBuilding,
    BuildingSnapshot
)
from seed.public.models import INTERNAL, PUBLIC, SharedBuildingField


class SharingViewTests(TestCase):
    """
    Tests of the SEED search_buildings
    """

    def setUp(self):
        self.admin_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'show_shared_buildings': True
        }
        self.admin_user = User.objects.create_superuser(**self.admin_details)
        self.parent_org = Organization.objects.create(name='Parent')
        self.parent_org.add_member(self.admin_user, ROLE_OWNER)

        self.eng_user_details = {
            'username': 'eng_owner@demo.com',
            'password': 'eng_pass',
            'email': 'eng_owner@demo.com'
        }
        self.eng_user = User.objects.create_user(**self.eng_user_details)
        self.eng_org = Organization.objects.create(parent_org=self.parent_org,
                                                   name='Engineers')
        self.eng_org.add_member(self.eng_user, ROLE_OWNER)

        self.des_user_details = {
            'username': 'des_owner@demo.com',
            'password': 'des_pass',
            'email': 'des_owner@demo.com'
        }
        self.des_user = User.objects.create_user(**self.des_user_details)
        self.des_org = Organization.objects.create(parent_org=self.parent_org,
                                                   name='Designers')
        self.des_org.add_member(self.des_user, ROLE_MEMBER)

        self._create_buildings()
        self._create_sharing()

    def _search_buildings(self, is_public=False):
        """
        Make a request of the search_buildings view and return the
        json-decoded body.
        """
        url = reverse_lazy("seed:search_buildings")
        if is_public:
            url = reverse_lazy("seed:public_search")
        post_data = {
            'filter_params': {},
            'number_per_page': BuildingSnapshot.objects.count(),
            'order_by': '',
            'page': 1,
            'q': '',
            'sort_reverse': False,
            'project_id': None,
        }

        response = self.client.post(
            url,
            content_type='application/json',
            data=json.dumps(post_data)
        )
        json_string = response.content
        return json.loads(json_string)

    def _create_sharing(self):
        """
        Creates ExportableField objects for this org.
        """
        fields = ['property_name',
                  'year_built',
                  'postal_code']

        for field in fields:
            exportable = ExportableField.objects.create(
                field_model='BuildingSnapshot',
                name=field,
                organization=self.parent_org
            )
            SharedBuildingField.objects.create(
                org=self.parent_org,
                field=exportable,
                field_type=INTERNAL
            )

        # Also create one public field
        # In this case, postal_code!
        SharedBuildingField.objects.create(
            org=self.parent_org,
            field=exportable,
            field_type=PUBLIC
        )

    def _create_buildings(self):
        """
        Create 10 buildings in each child org.

        Also set one shared and one unshared field to a known value.
        """
        for _ in range(10):
            cb = CanonicalBuilding(active=True)
            cb.save()
            b = SEEDFactory.building_snapshot(canonical_building=cb,
                                              property_name='ADMIN BUILDING',
                                              address_line_1='100 Admin St')
            cb.canonical_snapshot = b
            cb.save()
            b.super_organization = self.parent_org
            b.save()
        for _ in range(10):
            cb = CanonicalBuilding(active=True)
            cb.save()
            b = SEEDFactory.building_snapshot(canonical_building=cb,
                                              property_name='ENG BUILDING',
                                              address_line_1='100 Eng St')
            cb.canonical_snapshot = b
            cb.save()
            b.super_organization = self.eng_org
            b.save()
        for _ in range(10):
            cb = CanonicalBuilding(active=True)
            cb.save()
            b = SEEDFactory.building_snapshot(canonical_building=cb,
                                              property_name='DES BUILDING',
                                              address_line_1='100 Des St')
            cb.canonical_snapshot = b
            cb.save()
            b.super_organization = self.des_org
            b.save()

    def test_scenario(self):
        """
        Make sure setUp works.
        """
        self.assertTrue(self.des_org in self.parent_org.child_orgs.all())
        self.assertTrue(self.eng_org in self.parent_org.child_orgs.all())
        self.assertTrue(self.parent_org.is_owner(self.admin_user))
        self.assertFalse(self.parent_org.is_owner(self.eng_user))
        self.assertFalse(self.parent_org.is_owner(self.des_user))
        self.assertFalse(self.des_org.is_owner(self.des_user))
        self.assertTrue(self.des_org.is_member(self.des_user))
        self.assertTrue(self.eng_org.is_owner(self.eng_user))

    def test_public_viewer(self):
        """Public viewer requires no credentials, and should see public fields.

        In this case, only postal_code data.
        """
        results = self._search_buildings(is_public=True)

        fields = []

        for f in results['buildings']:
            fields.extend(f.keys())

        fields = list(set(fields))

        self.assertListEqual(fields, [u'postal_code'])

    @skip("Fix for new data model")
    def test_parent_viewer(self):
        """
        The admin user should be able to see all buildings with all fields.
        """
        self.client.login(**self.admin_details)

        result = self._search_buildings()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['number_returned'],
                         BuildingSnapshot.objects.count())
        self.assertEqual(len(result['buildings']),
                         BuildingSnapshot.objects.count())

        # parent org sees all fields on all buildings
        for b in result['buildings']:
            self.assertTrue(b['property_name'] in
                            ('ENG BUILDING', 'DES BUILDING', 'ADMIN BUILDING'))
            if b['property_name'] == 'ENG BUILDING':
                self.assertEqual(b['address_line_1'],
                                 '100 Eng St')
            elif b['property_name'] == 'DES BUILDING':
                self.assertEqual(b['address_line_1'],
                                 '100 Des St')
            elif b['property_name'] == 'ADMIN_BUILDING':
                self.assertEqual(b['address_line_1'],
                                 '100 Admin St')

    @skip("Fix for new data model")
    def test_suborg_view_not_shared(self):
        """
        A suborg user that doesn't have 'show_shared_buildings' set
        should only see their own suborg's buildings.
        """
        self.assertFalse(self.eng_user.show_shared_buildings)
        self.client.login(**self.eng_user_details)
        result = self._search_buildings()

        self.assertEqual(result['status'], 'success')

        expected_count = self.eng_org.building_snapshots.count()
        self.assertEqual(result['number_returned'],
                         expected_count)
        self.assertEqual(len(result['buildings']),
                         expected_count)

        # eng org only sees own buildings
        for b in result['buildings']:
            self.assertEqual(b['property_name'], 'ENG BUILDING')
            self.assertEqual(b['address_line_1'], '100 Eng St')

    @skip("Fix for new data model")
    def test_suborg_view_show_shared(self):
        """
        A suborg user with 'show_shared_buildings' set should see all buildings
        in the org tree, but only the shared fields for buildings outside
        the suborg.
        """
        self.des_user.show_shared_buildings = True
        self.des_user.save()
        self.client.login(**self.des_user_details)
        result = self._search_buildings()

        self.assertEqual(result['status'], 'success')

        expected_count = BuildingSnapshot.objects.count()
        self.assertEqual(result['number_returned'],
                         expected_count)
        self.assertEqual(len(result['buildings']),
                         expected_count)

        # des org user should see shared fields
        for b in result['buildings']:
            # property_name is shared
            self.assertTrue(b['property_name'] in
                            ('ENG BUILDING', 'DES BUILDING', 'ADMIN BUILDING'))
            if b['property_name'] == 'ENG BUILDING':
                # address_line_1 is unshared
                self.assertTrue('address_line_1' not in b)
            elif b['property_name'] == 'DES BUILDING':
                self.assertEqual(b['address_line_1'],
                                 '100 Des St')

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.test import TestCase

from seed.models import BuildingSnapshot


class TestJsonManager(TestCase):

    def setUp(self):
        self.model = BuildingSnapshot.objects.create()
        self.model.extra_data = {'superdata': 'always here', 'ratio': 0.43}
        self.model.save()

    def test_order_by_returns_all_buildings(self):
        """Test that we're able to order by values of a json field."""
        b = BuildingSnapshot.objects.create(source_type=3)
        b.extra_data = {'ratio': 0.12, 'counter': '10'}
        b.save()

        b = BuildingSnapshot.objects.create(source_type=3)
        b.extra_data = {'ratio': 0.80, 'counter': '1001'}
        b.save()

        buildings = list(BuildingSnapshot.objects.all().json_order_by(
            'ratio', order_by='ratio'
        ))

        self.assertEqual(buildings[0].extra_data['ratio'], 0.12)
        self.assertEqual(buildings[1].extra_data['ratio'], 0.43)
        self.assertEqual(buildings[2].extra_data['ratio'], 0.80)

        # Now test what happens when we sort in reverse order.
        buildings2 = list(BuildingSnapshot.objects.all().json_order_by(
            'ratio', order_by='ratio', order_by_rev=True
        ))

        self.assertEqual(buildings2[0].extra_data['ratio'], 0.80)
        self.assertEqual(buildings2[1].extra_data['ratio'], 0.43)
        self.assertEqual(buildings2[2].extra_data['ratio'], 0.12)

        # Now test alpha numeric sorting
        buildings3 = list(BuildingSnapshot.objects.all().json_order_by(
            'counter', order_by='counter'
        ))

        self.assertEqual(buildings3[0].extra_data.get('counter'), None)
        self.assertEqual(buildings3[1].extra_data['counter'], '10')
        self.assertEqual(buildings3[2].extra_data['counter'], '1001')

        # Now test reverse sort on alpha numeric sorting
        buildings4 = list(BuildingSnapshot.objects.all().json_order_by(
            'counter', order_by='counter', order_by_rev=True
        ))

        self.assertEqual(buildings4[0].extra_data['counter'], '1001')
        self.assertEqual(buildings4[1].extra_data['counter'], '10')
        self.assertEqual(buildings4[2].extra_data.get('counter'), None)

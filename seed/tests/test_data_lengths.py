# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.test import TestCase

from seed.models import BuildingSnapshot


class TestBuildingSnapshot(TestCase):

    def setUp(self):
        self.bs = BuildingSnapshot()

    def tearDown(self):
        self.bs = None

    def test_tax_lot_id(self):
        """
        """
        self.bs.tax_lot_id = '-' * 130
        self.bs.save()
        self.assertEqual(len(self.bs.tax_lot_id), 128)

    def test_tax_lot_id_int(self):
        """
        """
        self.bs.tax_lot_id = 123123123
        self.bs.save()
        self.assertEqual(self.bs.tax_lot_id, 123123123)

        # Check that the data is converted correctly
        bs2 = BuildingSnapshot.objects.get(pk=self.bs.pk)
        self.assertEqual(bs2.tax_lot_id, u'123123123')

    def test_pm_property_id(self):
        """
        """
        self.bs.pm_property_id = '-' * 130
        self.bs.save()
        self.assertEqual(len(self.bs.pm_property_id), 128)

    def test_custom_id_1(self):
        """
        """
        self.bs.custom_id_1 = '-' * 130
        self.bs.save()
        self.assertEqual(len(self.bs.custom_id_1), 128)

    def test_lot_number(self):
        """
        """
        self.bs.lot_number = '-' * 130
        self.bs.save()
        self.assertEqual(len(self.bs.lot_number), 128)

    def test_block_number(self):
        """
        """
        self.bs.block_number = '-' * 130
        self.bs.save()
        self.assertEqual(len(self.bs.block_number), 128)

    def test_district(self):
        """
        """
        self.bs.district = '-' * 130
        self.bs.save()
        self.assertEqual(len(self.bs.district), 128)

    def test_owner(self):
        """
        The owner field of the BuildingSnapshot model should
        truncate values to a max of 128 characters
        """
        self.bs.owner = "*" * 130
        self.bs.save()
        self.assertEqual(len(self.bs.owner), 128)

    def test_owner_email(self):
        """
        """
        self.bs.owner_email = '-' * 130
        self.bs.save()
        self.assertEqual(len(self.bs.owner_email), 128)

    def test_owner_telephone(self):
        """
        """
        self.bs.owner_telephone = '-' * 130
        self.bs.save()
        self.assertEqual(len(self.bs.owner_telephone), 128)

    def test_owner_address(self):
        """
        """
        self.bs.owner_address = '-' * 130
        self.bs.save()
        self.assertEqual(len(self.bs.owner_address), 128)

    def test_owner_city_state(self):
        """
        """
        self.bs.owner_city_state = '-' * 130
        self.bs.save()
        self.assertEqual(len(self.bs.owner_city_state), 128)

    def test_owner_postal_code(self):
        """
        """
        self.bs.owner_postal_code = '-' * 130
        self.bs.save()
        self.assertEqual(len(self.bs.owner_postal_code), 128)

    def test_property_name(self):
        """
        """
        self.bs.property_name = '-' * 260
        self.bs.save()
        self.assertEqual(len(self.bs.property_name), 255)

    def test_address_line_1(self):
        """
        """
        self.bs.address_line_1 = '-' * 260
        self.bs.save()
        self.assertEqual(len(self.bs.address_line_1), 255)

    def test_address_line_2(self):
        """
        """
        self.bs.address_line_2 = '-' * 260
        self.bs.save()
        self.assertEqual(len(self.bs.address_line_2), 255)

    def test_city(self):
        """
        """
        self.bs.city = '-' * 260
        self.bs.save()
        self.assertEqual(len(self.bs.city), 255)

    def test_postal_code(self):
        """
        """
        self.bs.postal_code = '-' * 260
        self.bs.save()
        self.assertEqual(len(self.bs.postal_code), 255)

    def test_state_province(self):
        """
        """
        self.bs.state_province = '-' * 260
        self.bs.save()
        self.assertEqual(len(self.bs.state_province), 255)

    def test_building_certification(self):
        """
        """
        self.bs.building_certification = '-' * 260
        self.bs.save()
        self.assertEqual(len(self.bs.building_certification), 255)

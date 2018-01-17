# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from os import path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from config.settings.common import BASE_DIR
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import User
from seed.models.building_file import BuildingFile


class TestBuildingFiles(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

    def test_file_type_lookup(self):
        self.assertEqual(BuildingFile.str_to_file_type(None), None)
        self.assertEqual(BuildingFile.str_to_file_type(''), None)
        self.assertEqual(BuildingFile.str_to_file_type(1), 1)
        self.assertEqual(BuildingFile.str_to_file_type('1'), 1)
        self.assertEqual(BuildingFile.str_to_file_type('BuildingSync'), 1)
        self.assertEqual(BuildingFile.str_to_file_type('BUILDINGSYNC'), 1)
        self.assertEqual(BuildingFile.str_to_file_type('Unknown'), 0)
        self.assertEqual(BuildingFile.str_to_file_type('GeoJSON'), 2)
        self.assertEqual(BuildingFile.str_to_file_type('hpxml'), 3)

    def test_buildingsync_constructor(self):
        filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'ex_1.xml')
        file = open(filename, 'rb')
        simple_uploaded_file = SimpleUploadedFile(file.name, file.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )

        status, property_state, property_view, messages = bf.process(self.org.id, self.org.cycles.first())
        self.assertTrue(status)
        self.assertEqual(property_state.address_line_1, '123 Main Street')
        self.assertEqual(messages, [])

    def test_hpxml_constructor(self):
        filename = path.join(BASE_DIR, 'seed', 'hpxml', 'tests', 'data', 'audit.xml')
        file = open(filename, 'rb')
        simple_uploaded_file = SimpleUploadedFile(file.name, file.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.HPXML
        )

        status, property_state, property_view, messages = bf.process(self.org.id, self.org.cycles.first())
        self.assertTrue(status)
        self.assertEqual(property_state.owner, 'Jane Customer')
        self.assertEqual(property_state.energy_score, 8)
        self.assertEqual(messages, [])

    def test_geojson_error(self):
        filename = path.join(BASE_DIR, 'seed', 'building_sync', 'tests', 'data', 'ex_1.xml')
        file = open(filename, 'rb')
        simple_uploaded_file = SimpleUploadedFile(file.name, file.read())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.GEOJSON,
        )

        status, property_state, property_view, messages = bf.process(self.org.id, self.org.cycles.first())
        self.assertFalse(status)
        self.assertEqual(property_view, None)

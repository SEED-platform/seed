# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import pathlib
from os import path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from seed.models import User
from seed.models.building_file import BuildingFile
from seed.utils.organizations import create_organization


class TestBuildingFiles(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)

    def test_file_type_lookup(self):
        self.assertEqual(BuildingFile.str_to_file_type(None), None)
        self.assertEqual(BuildingFile.str_to_file_type(''), None)
        self.assertEqual(BuildingFile.str_to_file_type('Unknown'), 0)
        self.assertEqual(BuildingFile.str_to_file_type('hpxml'), 3)

    def test_hpxml_constructor(self):
        filename = path.join(path.dirname(__file__), 'data', 'audit.xml')
        simple_uploaded_file = SimpleUploadedFile(filename, pathlib.Path(filename).read_bytes())

        bf = BuildingFile.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=BuildingFile.HPXML
        )

        status, property_state, property_view, messages = bf.process(self.org.id, self.org.cycles.first())
        self.assertTrue(status)
        self.assertEqual(property_state.owner, 'Jane Customer')
        self.assertEqual(property_state.energy_score, 8)
        self.assertEqual(messages, {'errors': [], 'warnings': []})

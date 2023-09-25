# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from os import path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from config.settings.common import BASE_DIR
from seed.models import User
from seed.models.inventory_document import InventoryDocument
from seed.utils.organizations import create_organization


class TestInventoryDocuments(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)

    def test_file_type_lookup(self):

        self.assertEqual(InventoryDocument.str_to_file_type(None), None)
        self.assertEqual(InventoryDocument.str_to_file_type(''), None)
        self.assertEqual(InventoryDocument.str_to_file_type(1), 1)
        self.assertEqual(InventoryDocument.str_to_file_type('1'), 1)
        self.assertEqual(InventoryDocument.str_to_file_type('Unknown'), 0)
        self.assertEqual(InventoryDocument.str_to_file_type('PDF'), 1)
        self.assertEqual(InventoryDocument.str_to_file_type('OSM'), 2)
        self.assertEqual(InventoryDocument.str_to_file_type('IDF'), 3)
        self.assertEqual(InventoryDocument.str_to_file_type('DXF'), 4)

    def test_inventorydocument_constructor(self):
        filename = path.join(BASE_DIR, 'seed', 'tests', 'data', 'test-document.pdf')
        with open(filename, 'rb') as f:
            simple_uploaded_file = SimpleUploadedFile(f.name, f.read())

        doc = InventoryDocument.objects.create(
            file=simple_uploaded_file,
            filename=filename,
            file_type=InventoryDocument.PDF,
        )

        self.assertTrue(doc.id is not None)

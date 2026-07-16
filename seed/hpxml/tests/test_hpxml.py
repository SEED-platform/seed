"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import pathlib
from os import path
from types import SimpleNamespace

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from lxml import etree

from seed.hpxml.hpxml import HPXML
from seed.models import User
from seed.models.building_file import BuildingFile
from seed.utils.organizations import create_organization


class TestBuildingFiles(TestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)

    def test_file_type_lookup(self):
        self.assertEqual(BuildingFile.str_to_file_type(None), None)
        self.assertEqual(BuildingFile.str_to_file_type(""), None)
        self.assertEqual(BuildingFile.str_to_file_type("Unknown"), 0)
        self.assertEqual(BuildingFile.str_to_file_type("hpxml"), 3)

    def test_hpxml_constructor(self):
        filename = path.join(path.dirname(__file__), "data", "audit.xml")
        simple_uploaded_file = SimpleUploadedFile(filename, pathlib.Path(filename).read_bytes())

        bf = BuildingFile.objects.create(file=simple_uploaded_file, filename=filename, file_type=BuildingFile.HPXML)

        status, property_state, _property_view, messages = bf.process(self.org.id, self.org.cycles.first())
        self.assertTrue(status)
        self.assertEqual(property_state.owner, "Jane Customer")
        self.assertEqual(property_state.energy_score, 8)
        self.assertEqual(messages, {"errors": [], "warnings": []})

    def test_hpxml_export_parses_owner_name(self):
        property_state = SimpleNamespace(
            extra_data={},
            address_line_1=None,
            address_line_2=None,
            city=None,
            state=None,
            postal_code=None,
            gross_floor_area=None,
            year_built=None,
            conditioned_floor_area=None,
            occupied_floor_area=None,
            energy_score=None,
            owner="Dr. Jane Q. Customer Jr.",
            owner_email=None,
            owner_telephone=None,
            owner_address=None,
            owner_city_state=None,
            owner_postal_code=None,
            building_certification=None,
        )

        root = etree.fromstring(HPXML().export(property_state))
        namespace = {"h": HPXML.NS}

        self.assertEqual(root.xpath("string(//h:Customer/h:CustomerDetails/h:Person/h:Name/h:PrefixName)", namespaces=namespace), "Dr.")
        self.assertEqual(root.xpath("string(//h:Customer/h:CustomerDetails/h:Person/h:Name/h:FirstName)", namespaces=namespace), "Jane")
        self.assertEqual(root.xpath("string(//h:Customer/h:CustomerDetails/h:Person/h:Name/h:MiddleName)", namespaces=namespace), "Q.")
        self.assertEqual(root.xpath("string(//h:Customer/h:CustomerDetails/h:Person/h:Name/h:LastName)", namespaces=namespace), "Customer")
        self.assertEqual(root.xpath("string(//h:Customer/h:CustomerDetails/h:Person/h:Name/h:SuffixName)", namespaces=namespace), "Jr.")

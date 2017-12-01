# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author noel.merket@nrel.gov
"""
import os
import tempfile
from StringIO import StringIO

from django.test import TestCase
from lxml import objectify
from lxml.etree import XMLSyntaxError
import xmltodict

from seed.hpxml.hpxml import HPXML, hpxml_parser
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import (
    Organization,
    OrganizationUser,
)
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
)


class TestHPXML(TestCase):

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details)
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)
        self.xml_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'audit.xml')
        self.hpxml = HPXML()

    def tearDown(self):
        pass

    def test_constructor(self):
        self.assertTrue(self.hpxml.import_file(self.xml_file))
        self.assertRaises(IOError, self.hpxml.import_file, 'no/path/to/file.xml')
        fd, tempfile_path = tempfile.mkstemp()
        try:
            tree = objectify.parse(self.xml_file)
            root = tree.getroot()
            objectify.SubElement(root, 'BogusElement')
            tree.write(tempfile_path, encoding='utf-8')
            self.assertRaises(XMLSyntaxError, self.hpxml.import_file, tempfile_path)
        finally:
            os.close(fd)
            os.remove(tempfile_path)

    def test_get_building(self):
        self.assertTrue(self.hpxml.import_file(self.xml_file))
        bldg = self.hpxml._get_building()
        self.assertEqual(bldg.ProjectStatus.EventType, 'audit')
        self.hpxml.root.Building[1].ProjectStatus.EventType = 'job completion testing/final inspection'
        bldg = self.hpxml._get_building()
        self.assertEqual(bldg.BuildingID.get('id'), 'bldg1p')
        self.hpxml.root.Building[1].ProjectStatus.EventType = 'proposed workscope'
        bldg = self.hpxml._get_building('bldg1p')
        self.assertEqual(bldg.BuildingID.get('id'), 'bldg1p')

    def test_process(self):
        self.assertTrue(self.hpxml.import_file(self.xml_file))
        res = self.hpxml.process()
        expected = {
            'building_id': 'bldg1',
            'address_line_1': '123 Main St',
            'address_line_2': '',
            'city': 'Beverly Hills',
            'state': 'CA',
            'postal_code': '90210',
            'year_built': 1961,
            'conditioned_floor_area': 2400.0,
            'owner': 'Jane Customer',
            'owner_email': 'asdf@jkl.com',
            'energy_score': 8,
            'energy_score_type': 'US DOE Home Energy Score',
            'building_certification': 'Home Performance with Energy Star',
        }
        self.assertDictEqual(expected, res)
        self.hpxml.root.Customer.CustomerDetails.Person.Name.clear()
        res = self.hpxml.process()
        self.assertNotIn('owner', res.keys())

    def test_export_no_property(self):
        self.assertTrue(self.hpxml.import_file(self.xml_file))
        xmlstr = self.hpxml.export(None)
        self.assertGreater(len(xmlstr), 0)
        with open(self.xml_file, 'r') as f:
            orig_d = xmltodict.parse(f, process_namespaces=True)
        new_d = xmltodict.parse(xmlstr, process_namespaces=True)
        self.assertDictEqual(orig_d, new_d)

    def test_bad_owner_name(self):
        self.hpxml.import_file(self.xml_file)
        psfactory = FakePropertyStateFactory(organization=self.org)
        ps = psfactory.get_property_state(organization=self.org)
        ps.extra_data['building_id'] = 'bldg1'
        ps.owner = 'Miller Reyes PLC'
        ps.owner_email = 'janecustomer@jkl.com'
        ps.owner_telephone = '555-555-1234'
        ps.owner_address = '15013 Denver West Pkwy'
        ps.owner_city_state = 'Golden, CO'
        ps.owner_postal_code = '80401'
        ps.building_certification = 'LEED Silver'
        ps.energy_score = 9
        ps.extra_data['energy_score_type'] = 'my energy score'
        ps.save()
        self.hpxml.export(ps)

    def test_export(self):
        self.hpxml.import_file(self.xml_file)
        psfactory = FakePropertyStateFactory(organization=self.org)
        ps = psfactory.get_property_state(organization=self.org)
        ps.extra_data['building_id'] = 'bldg1'
        ps.owner = 'Jane Smith'
        ps.owner_email = 'janecustomer@jkl.com'
        ps.owner_telephone = '555-555-1234'
        ps.owner_address = '15013 Denver West Pkwy'
        ps.owner_city_state = 'Golden, CO'
        ps.owner_postal_code = '80401'
        ps.building_certification = 'LEED Silver'
        ps.energy_score = 9
        ps.extra_data['energy_score_type'] = 'my energy score'
        ps.save()

        xml = self.hpxml.export(ps)
        f = StringIO(xml)
        tree = objectify.parse(f, parser=hpxml_parser)
        root = tree.getroot()
        self.assertEqual(
            int(root.Building.BuildingDetails.BuildingSummary.BuildingConstruction.EnergyScore[1].Score),
            ps.energy_score
        )
        self.assertEqual(
            root.Customer.CustomerDetails.Person.Email[1].EmailAddress,
            ps.owner_email
        )
        self.assertEqual(
            root.Customer.CustomerDetails.Person.Email[0].EmailAddress,
            'asdf@jkl.com'
        )
        self.assertEqual(
            root.Customer.CustomerDetails.Person.Telephone[1].TelephoneNumber,
            ps.owner_telephone
        )
        self.assertEqual(
            root.Customer.CustomerDetails.Person.Telephone[0].TelephoneNumber,
            '555-555-5555'
        )
        address = root.Customer.CustomerDetails.MailingAddress
        self.assertEqual(address.Address1, ps.owner_address)
        self.assertEqual(address.CityMunicipality, 'Golden')
        self.assertEqual(address.StateCode, 'CO')
        self.assertEqual(address.ZipCode.text, ps.owner_postal_code)
        prog_certs = root.Project.ProjectDetails.ProgramCertificate
        self.assertEqual(prog_certs[0], 'Home Performance with Energy Star')
        self.assertEqual(prog_certs[1], 'LEED Silver')

    def test_export_owner_name(self):
        self.hpxml.import_file(self.xml_file)
        psfactory = FakePropertyStateFactory(organization=self.org)
        ps = psfactory.get_property_state(organization=self.org)
        ps.extra_data['building_id'] = 'bldg1'
        ps.owner = 'Dr. John C. Doe Jr.'
        ps.save()

        xml = self.hpxml.export(ps)
        f = StringIO(xml)
        tree = objectify.parse(f, parser=hpxml_parser)
        root = tree.getroot()
        name = root.Customer.CustomerDetails.Person.Name
        self.assertEqual('Dr.', name.PrefixName.text)
        self.assertEqual('John', name.FirstName.text)
        self.assertEqual('C.', name.MiddleName.text)
        self.assertEqual('Doe', name.LastName.text)
        self.assertEqual('Jr.', name.SuffixName.text)

    def test_export_create_project(self):
        self.hpxml.import_file(self.xml_file)
        self.hpxml.root.remove(self.hpxml.root.Project)
        psfactory = FakePropertyStateFactory(organization=self.org)
        ps = psfactory.get_property_state(organization=self.org)
        ps.extra_data['building_id'] = 'bldg1'
        ps.owner = 'Jane Smith'
        ps.building_certification = 'Generic Certification of Green-ness'
        ps.save()

        xml = self.hpxml.export(ps)
        f = StringIO(xml)
        tree = objectify.parse(f, parser=hpxml_parser)
        root = tree.getroot()

        self.assertEqual(root.Project.ProjectDetails.ProgramCertificate, 'other')

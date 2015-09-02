import json
from os import path
from django.core.files import File
from django.test import TestCase
from django.core.urlresolvers import reverse

from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.tests import util
from seed import tasks
from seed.cleansing.models import Cleansing

from seed.models import (
    ASSESSED_RAW,
    ASSESSED_BS,
    PORTFOLIO_BS,
    POSSIBLE_MATCH,
    SYSTEM_MATCH,
    FLOAT,
    BuildingSnapshot,
    CanonicalBuilding,
    Column,
    ColumnMapping,
    Unit,
    get_ancestors,
)


class CleansingDataTest(TestCase):
    def setUp(self):
        self.user_details = {
            'username': 'testuser@example.com',
            'email': 'testuser@example.com',
            'password': 'test_password'
        }
        self.user = User.objects.create_user(**self.user_details)
        self.login_url = reverse('landing:login')

        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        self.import_record = ImportRecord.objects.create(owner=self.user)
        self.import_record.super_organization = self.org
        self.import_record.save()
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record
        )

        self.import_file.is_espm = False
        self.import_file.source_type = 'ASSESSED_RAW'
        self.import_file.file = File(
            open(path.join(path.dirname(__file__), 'test_data', 'covered-buildings-sample-with-errors.csv'))
        )

        self.import_file.save()

        # tasks.save_raw_data(self.import_file.pk)

    def test_simple_login(self):
        self.client.post(self.login_url, self.user_details, secure=True)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_cleanse(self):
        # Import the file and run mapping

        # This is silly, the mappings are backwards from what you would expect. The key is the BS field, and the
        # value is the value in the CSV
        fake_mappings = {
            'city': 'city',
            'Zip': 'Zip',
            'gross_floor_area': 'GBA',
            'building_count': 'BLDGS',
            'year_built': 'AYB_YearBuilt',
            'state_province': 'State',
            'address_line_1': 'Address',
            'owner': 'Owner',
            'property_notes': 'Property Type',
            'tax_lot_id': 'UBI'
        }

        tasks.save_raw_data(self.import_file.id)
        util.make_fake_mappings(fake_mappings, self.org)
        tasks.map_data(self.import_file.id)

        qs = BuildingSnapshot.objects.filter(
            import_file=self.import_file,
            source_type=ASSESSED_BS,
        ).iterator()

        c = Cleansing()
        c.cleanse(qs)

        data = c.results

        self.assertEqual(len(c.results), 2)
        keys = c.results.keys()
        self.assertEqual(len(keys), 2)
        self.assertTrue(data[keys[0]]['address_line_1'], '95373 E Peach Avenue')
        self.assertTrue(data[keys[0]]['tax_lot_id'], '10107/c6596')

        res = [{"field": u"custom_id_1", "message": u"Matching field not found", "severity": u"error"},
               {"field": u"pm_property_id", "message": u"Matching field not found", "severity": u"error"},
               {"field": u"year_built", "message": u"Value [0] < 1500", "severity": u"warning"},
               {"field": u"gross_floor_area", "message": u"Value [10000000000] > 7000000", "severity": u"error"}]
        self.assertEqual(res, data[keys[1]]['cleansing_results'])

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import copy
import json
import logging
import os.path as osp

from django.core.urlresolvers import reverse

from seed.data_importer import tasks
from seed.data_importer.tests.util import (
    DataMappingBaseTestCase,
    FAKE_MAPPINGS,
)
from seed.data_importer.views import ImportFileViewSet
from seed.models import (
    Column,
    PropertyState,
    PropertyView,
    ASSESSED_RAW,
    PropertyAuditLog,
    DATA_STATE_MAPPING,
    DATA_STATE_MATCHING,
    MERGE_STATE_UNKNOWN,
    MERGE_STATE_NEW,
)

_log = logging.getLogger(__name__)


class TestViewsMatching(DataMappingBaseTestCase):
    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties.xlsx')
        self.fake_mappings = copy.copy(FAKE_MAPPINGS['portfolio'])
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        self.import_file.load_import_file(osp.join(osp.dirname(__file__), 'data', filename))
        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.id)
        tasks.map_data(self.import_file.pk)
        tasks.match_buildings(self.import_file.id)

        # import second file that is currently the same, but should be slightly different
        filename_2 = getattr(self, 'filename', 'example-data-properties-small-changes.xlsx')
        _, self.import_file_2 = self.create_import_file(self.user, self.org, self.cycle)
        self.import_file_2.load_import_file(osp.join(osp.dirname(__file__), 'data', filename_2))
        tasks._save_raw_data(self.import_file_2.pk, 'fake_cache_key_2', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file_2.id)
        tasks.map_data(self.import_file_2.pk)
        tasks.match_buildings(self.import_file_2.id)

        # for api tests
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.client.login(**user_details)

    def test_use_description_updated(self):
        """
        Most of the buildings will match, except the ones that haven't changed.
            124 Mainstreet

        TODO: There's an error with automatic matching of 93029 Wellington Blvd - College/University
        TODO: There are significant issues with the matching here!
        """
        state_ids = list(
            PropertyView.objects.filter(cycle=self.cycle).select_related('state').values_list(
                'state_id', flat=True))
        self.assertEqual(len(state_ids), 14)

        property_states = PropertyState.objects.filter(id__in=state_ids)
        # Check that the use descriptions have been updated to the new ones
        # expected = [u'Bar', u'Building', u'Club', u'Coffee House',
        #             u'Daycare', u'Diversity Building', u'House', u'Multifamily Housing',
        #             u'Multistorys', u'Pizza House', u'Residence', u'Residence', u'Residence',
        #             u'Swimming Pool']

        # print sorted([p.use_description for p in property_states])
        results = sorted([p.use_description for p in property_states])
        self.assertTrue('Bar' in results)
        self.assertTrue('Building' in results)
        self.assertTrue('Club' in results)
        self.assertTrue('Coffee House' in results)

        logs = PropertyAuditLog.objects.filter(state_id__in=state_ids)
        self.assertEqual(logs.count(), 14)

    def test_get_filtered_mapping_results_date(self):
        url = reverse("api:v2:import_files-filtered-mapping-results", args=[self.import_file.pk])
        resp = self.client.post(
            url, data=json.dumps({"organization_id": self.org.id}), content_type='application/json'
        )

        body = json.loads(resp.content)
        for prop in body['properties']:
            if prop['custom_id_1'] == '1':
                self.assertEqual(body['properties'][0]['recent_sale_date'], '1888-01-05T08:00:00')
            if prop['custom_id_1'] == '4':
                self.assertEqual(body['properties'][1]['recent_sale_date'], '2017-01-05T08:00:00')
            if prop['custom_id_1'] == '6':
                self.assertEqual(body['properties'][2]['recent_sale_date'], None)

    def test_get_filtered_mapping_results(self):
        url = reverse("api:v2:import_files-filtered-mapping-results", args=[self.import_file_2.pk])
        resp = self.client.post(
            url, data=json.dumps({"get_coparents": True}), content_type='application/json'
        )

        body = json.loads(resp.content)

        # spot check the results
        expected = {
            "lot_number": "1552813",
            "extra_data": {
                "data_007": "a"
            },
            "coparent": {
                "lot_number": "1552813",
                "owner_email": "ULLC@gmail.com",
                "year_ending": "2015-12-31",
                "owner": "U LLC",
                "site_eui": 125.0,
                "custom_id_1": "1",
                "city": "Rust",
                "property_notes": "Case A-1: 1 Property, 1 Tax Lot",
                "pm_property_id": "2264",
                "use_description": "Hotel",
                "gross_floor_area": 12555.0,
                "owner_telephone": "213-852-1238",
                "energy_score": 75,
                "address_line_1": "50 Willow Ave SE"
            },
            "matched": True
        }

        # find lot number 1552813 in body['properties']
        found_prop = [k for k in body['properties'] if k['lot_number'] == '1552813']
        self.assertEqual(len(found_prop), 1)

        found_prop = found_prop[0]
        del found_prop['id']
        del found_prop['coparent']['id']
        self.assertEqual(body['status'], 'success')
        self.assertEqual(len(body['tax_lots']), 12)
        self.assertEqual(len(body['properties']), 14)
        self.assertEqual(expected['lot_number'], found_prop['lot_number'])
        self.assertEqual(expected['matched'], found_prop['matched'])
        self.assertDictContainsSubset(expected['coparent'], found_prop['coparent'])

    def test_get_coparents(self):
        # get a specific test case with coparents
        property_state = PropertyState.objects.filter(
            use_description='Pizza House',
            import_file_id=self.import_file_2,
            data_state__in=[DATA_STATE_MAPPING, DATA_STATE_MATCHING],
            merge_state__in=[MERGE_STATE_UNKNOWN, MERGE_STATE_NEW]
        ).first()

        vs = ImportFileViewSet()
        fields = ['id', 'extra_data', 'lot_number', 'use_description']

        coparents = vs.has_coparent(property_state.id, 'properties', fields)
        expected = {
            'lot_number': u'11160509',
            'gross_floor_area': 23543.0,
            'owner_telephone': u'213-546-9755',
            'energy_score': 63,
            'use_description': 'Retail',
        }
        self.assertDictContainsSubset(expected, coparents)

    def test_unmatch(self):
        # unmatch a specific entry
        property_state = PropertyState.objects.filter(
            use_description='Club',
            import_file_id=self.import_file_2,
            data_state__in=[DATA_STATE_MAPPING, DATA_STATE_MATCHING],
            merge_state__in=[MERGE_STATE_UNKNOWN, MERGE_STATE_NEW]
        ).first()

        vs = ImportFileViewSet()
        fields = ['id', 'extra_data', 'lot_number', 'use_description']

        # get the coparent of the 'Club' to get the ID
        coparents = vs.has_coparent(property_state.id, 'properties', fields)

        # verify that the coparent id is not part of the view
        prop = PropertyView.objects.filter(cycle=self.cycle, state__id=coparents['id'])
        self.assertFalse(prop.exists())

        data = {
            "inventory_type": "properties",
            "state_id": property_state.id,
            "coparent_id": coparents['id']
        }
        url = reverse("api:v2:import_files-unmatch", args=[self.import_file_2.pk])
        resp = self.client.post(
            url, data=json.dumps(data), content_type='application/json'
        )
        body = json.loads(resp.content)
        self.assertEqual(body['status'], 'success')

        # verify that the coparent id is now in the view
        self.assertTrue(prop.exists())

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
import operator
import os.path as osp
from functools import reduce

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Q

from seed.data_importer import tasks
from seed.data_importer.models import ImportFile
from seed.data_importer.tests.util import (
    FAKE_EXTRA_DATA,
    FAKE_MAPPINGS,
    FAKE_ROW,
)
from seed.models import (
    ASSESSED_RAW,
    ASSESSED_BS,
    DATA_STATE_MAPPING,
)
from seed.models import (
    Column,
    PropertyState,
)
from seed.tests.util import DataMappingBaseTestCase

logger = logging.getLogger(__name__)


class TestMatching(DataMappingBaseTestCase):
    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['portfolio']
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        filepath = osp.join(osp.dirname(__file__), '..', 'data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()

    def query_property_matches(self, properties, pm_id, custom_id, ubid, ulid):
        """
        Helper method to return a queryset of PropertyStates that match at least one of the specified
        ids

        :param properties: QuerySet, PropertyStates
        :param pm_id: string, PM Property ID
        :param custom_id: String, Custom ID
        :param ubid: String, Unique Building Identifier
        :param ulid: String, Unique Land/Lot Identifier
        :return: QuerySet of objects that meet criteria.
        """

        """"""
        params = []
        # Not sure what the point of this logic is here. If we are passing in a custom_id then
        # why would we want to check pm_property_id against the custom_id, what if we pass both in?
        # Seems like this favors pm_id
        if pm_id:
            params.append(Q(pm_property_id=pm_id))
            params.append(Q(custom_id_1=pm_id))
            params.append(Q(ubid=pm_id))
        if custom_id:
            params.append(Q(pm_property_id=custom_id))
            params.append(Q(custom_id_1=custom_id))
            params.append(Q(ubid=custom_id))
        if ubid:
            params.append(Q(pm_property_id=ubid))
            params.append(Q(custom_id_1=ubid))
            params.append(Q(ubid=ubid))
        if ulid:
            params.append(Q(ulid=ulid))

        if not params:
            # Return an empty QuerySet if we don't have any params.
            return properties.none()

        return properties.filter(reduce(operator.or_, params)).order_by('id')

    def test_single_id_matches(self):
        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.pk)
        tasks.map_data(self.import_file.pk)

        # verify that there are no properties listed as canonical
        property_states = tasks.list_canonical_property_states(self.org)
        self.assertEqual(len(property_states), 0)

        # promote a properties
        ps = PropertyState.objects.filter(pm_property_id='2264').first()
        ps.promote(self.cycle)

        property_states = tasks.list_canonical_property_states(self.org)
        self.assertEqual(len(property_states), 1)

        matches = self.query_property_matches(property_states, None, None, None, None)
        self.assertEqual(len(matches), 0)
        matches = self.query_property_matches(property_states, '2264', None, None, None)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0], ps)

    def test_multiple_id_matches(self):
        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.pk)
        tasks.map_data(self.import_file.pk)

        # verify that there are no properties listed as canonical
        property_states = tasks.list_canonical_property_states(self.org)
        self.assertEqual(len(property_states), 0)

        # promote two properties
        ps = PropertyState.objects.filter(custom_id_1='13').order_by('id')
        ps_test = ps.first()
        ps_test_2 = ps.last()
        for p in ps:
            p.promote(self.cycle)
            # from seed.utils.generic import pp
            # pp(p)

        property_states = tasks.list_canonical_property_states(self.org)
        self.assertEqual(len(property_states), 2)

        # no arguments passed should return no results
        matches = self.query_property_matches(property_states, None, None, None, None)
        self.assertEqual(len(matches), 0)
        # should return 2 properties
        matches = self.query_property_matches(property_states, None, '13', None, None)
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0], ps_test)
        self.assertEqual(matches[1], ps_test_2)
        # should return only the second property
        matches = self.query_property_matches(property_states, '2342', None, None, None)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0], ps_test_2)
        # should return both properties, the first one should be the pm match, i.e. the first prop
        matches = self.query_property_matches(property_states, '481516', '13', None, None)
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0], ps_test)
        self.assertEqual(matches[1], ps_test_2)
        # if passing in the second pm then it will not be the first
        matches = self.query_property_matches(property_states, '2342', '13', None, None)
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[1], ps_test_2)
        # pass the pm id into the custom id. it should still return the correct buildings.
        # not sure that this is the right behavior, but this is what it does, so just testing.
        matches = self.query_property_matches(property_states, None, '2342', None, None)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0], ps_test_2)
        matches = self.query_property_matches(property_states, '13', None, None, None)
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0], ps_test)
        self.assertEqual(matches[1], ps_test_2)

    def test_handle_id_matches_duplicate_data(self):
        """
        Test for handle_id_matches behavior when matching duplicate data
        """
        # TODO: Fix the PM, tax lot id, and custom ID fields in PropertyState
        bs_data = {
            'pm_property_id': "2360",
            # 'tax_lot_id': '476/460',
            'property_name': 'Garfield Complex',
            'custom_id_1': "89",
            'address_line_1': '12975 Database LN.',
            'address_line_2': '',
            'city': 'Cartoon City',
            'postal_code': "54321",
            'data_state': DATA_STATE_MAPPING,
            'source_type': ASSESSED_BS,
        }

        # Setup mapped AS snapshot.
        PropertyState.objects.create(
            organization=self.org,
            import_file=self.import_file,
            **bs_data
        )

        # Different file, but same ImportRecord.
        # Setup mapped PM snapshot.
        # Should be an identical match.
        new_import_file = ImportFile.objects.create(import_record=self.import_record,
                                                    mapping_done=True)

        tasks.geocode_and_match_buildings_task(new_import_file.pk)

        duplicate_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            mapping_done=True
        )

        PropertyState.objects.create(
            organization=self.org,
            import_file=duplicate_import_file,
            **bs_data
        )

        # get a list of unhandled
        # unmatched_properties = self.import_file.find_unmatched_property_states()
        # unmatched_properties_2 = duplicate_import_file.find_unmatched_property_states()
        # from seed.utils.generic import pp
        # print(unmatched_properties)
        # for p in unmatched_properties:
        #     pp(p)
        # print(len(unmatched_properties))
        #
        # for p in unmatched_properties_2:
        #     pp(p)
        # print(len(unmatched_properties_2))

        # TODO: figure out why this isn't working here
        # self.assertRaises(tasks.DuplicateDataError, tasks.handle_id_matches,
        #                   new_snapshot, duplicate_import_file,
        #                   self.user.pk)

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.core.files.uploadedfile import SimpleUploadedFile

import logging

import os.path as osp

from seed.data_importer import tasks
from seed.data_importer.tests.util import (
    FAKE_MAPPINGS,
)
from seed.lib.mcm import mapper
from seed.models import (
    ASSESSED_RAW,
    DATA_STATE_IMPORT,
    Column,
)
from seed.models.column_mappings import get_column_mapping
from seed.test_helpers.fake import (
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import DataMappingBaseTestCase

logger = logging.getLogger(__name__)


class TestMapping(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)

    def test_mapping(self):
        """Test objects in database can be converted to mapped fields"""
        # for mapping, you have to create an import file, even it is just one record. This is
        # more of an ID to track imports

        state = self.property_state_factory.get_property_state_as_extra_data(
            import_file_id=self.import_file.id,
            source_type=ASSESSED_RAW,
            data_state=DATA_STATE_IMPORT,
            random_extra=42
        )
        # set import_file save done to true
        self.import_file.raw_save_done = True
        self.import_file.save()

        # Create mappings from the new states
        # TODO #239: Convert this to a single helper method to suggest and save
        suggested_mappings = mapper.build_column_mapping(
            list(state.extra_data.keys()),
            Column.retrieve_all_by_tuple(self.org),
            previous_mapping=get_column_mapping,
            map_args=[self.org],
            thresh=80
        )

        # Convert mapping suggests to the format needed for saving
        mappings = []
        for raw_column, suggestion in suggested_mappings.items():
            # Single suggestion looks like:'lot_number': ['PropertyState', 'lot_number', 100]
            mapping = {
                "from_field": raw_column,
                "from_units": None,
                "to_table_name": suggestion[0],
                "to_field": suggestion[1],
                "to_field_display_name": suggestion[1],
            }
            mappings.append(mapping)

        # Now save the mappings
        # print(mappings)
        Column.create_mappings(mappings, self.org, self.user, self.import_file.id)
        # END TODO

        tasks.map_data(self.import_file.id)

        props = self.import_file.find_unmatched_property_states()
        self.assertEqual(len(props), 1)
        self.assertEqual(state.extra_data['year_built'], props.first().year_built)
        self.assertEqual(state.extra_data['random_extra'], props.first().extra_data['random_extra'])

        # from seed.utils.generic import pp
        # for p in props:
        #     pp(p)


class TestDuplicateFileHeaders(DataMappingBaseTestCase):
    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties-duplicate-headers.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['portfolio']
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        filepath = osp.join(osp.dirname(__file__), 'data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()

    def test_duplicate_headers_throws_400(self):
        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.pk)

        with self.assertRaises(Exception):
            tasks.map_data(self.import_file.pk)

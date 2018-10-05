# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import logging
import os.path as osp

from django.core.files.uploadedfile import SimpleUploadedFile

from seed.data_importer import tasks
from seed.data_importer.tests.util import (
    FAKE_MAPPINGS,
)
from seed.models import (
    ASSESSED_RAW,
    Column,
)

logger = logging.getLogger(__name__)

from seed.data_importer.equivalence_partitioner import EquivalencePartitioner
from seed.tests.util import DataMappingBaseTestCase


class TestEquivalenceWithFile(DataMappingBaseTestCase):
    def setUp(self):
        super(TestEquivalenceWithFile, self).setUp()

        filename = getattr(self, 'filename', 'covered-buildings-sample.csv')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['covered_building']
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        filepath = osp.join(osp.dirname(__file__), '..', '..', '..', 'tests', 'data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()

        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.id)
        tasks.map_data(self.import_file.pk)

    def test_equivalence(self):
        all_unmatched_properties = self.import_file.find_unmatched_property_states()
        unmatched_properties, duplicate_property_states = tasks.filter_duplicated_states(
            all_unmatched_properties
        )
        partitioner = EquivalencePartitioner.make_propertystate_equivalence()

        equiv_classes = partitioner.calculate_equivalence_classes(unmatched_properties)
        self.assertEqual(len(equiv_classes), 512)

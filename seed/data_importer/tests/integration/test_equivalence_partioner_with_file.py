# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import logging
import os.path as osp
import pathlib

from django.core.files.uploadedfile import SimpleUploadedFile

from seed.data_importer import match, tasks
from seed.data_importer.equivalence_partitioner import EquivalencePartitioner
from seed.data_importer.tests.util import FAKE_MAPPINGS
from seed.lib.progress_data.progress_data import ProgressData
from seed.models import ASSESSED_RAW, Column, PropertyState
from seed.tests.util import DataMappingBaseTestCase

logger = logging.getLogger(__name__)


class TestEquivalenceWithFile(DataMappingBaseTestCase):
    def setUp(self):
        super().setUp()

        filename = getattr(self, 'filename', 'covered-buildings-sample.csv')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['covered_building']
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        filepath = osp.join(osp.dirname(__file__), '..', '..', '..', 'tests', 'data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=pathlib.Path(filepath).read_bytes()
        )
        self.import_file.save()

        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.id)
        tasks.map_data(self.import_file.pk)

    def test_equivalence(self):
        all_unmatched_properties = self.import_file.find_unmatched_property_states()
        sub_progress_data = ProgressData(func_name='match_sub_progress', unique_id=123)
        sub_progress_data.save()
        unmatched_property_ids, duplicate_property_count = match.filter_duplicate_states(
            all_unmatched_properties,
            sub_progress_data.key,
        )
        partitioner = EquivalencePartitioner.make_propertystate_equivalence()

        unmatched_properties = list(PropertyState.objects.filter(pk__in=unmatched_property_ids))
        equiv_classes = partitioner.calculate_equivalence_classes(unmatched_properties)
        self.assertEqual(len(equiv_classes), 512)

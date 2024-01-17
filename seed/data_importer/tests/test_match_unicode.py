
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

from seed.data_importer import tasks
from seed.data_importer.tests.util import FAKE_MAPPINGS
from seed.lib.mcm.cleaners import normalize_unicode_and_characters
from seed.models import (
    ASSESSED_RAW,
    DATA_STATE_MAPPING,
    Column,
    PropertyState,
    PropertyView
)
from seed.tests.util import DataMappingBaseTestCase

logger = logging.getLogger(__name__)


class TestUnicodeNormalization(DataMappingBaseTestCase):
    def test_unicode_normalization(self):
        """Test a few cases. The unicodedata.normalize('NFC', text) method combines the
        the letter and diacritics, which seems to provide the best compatibility."""
        # Guillemets
        unicode_text = "Café «Déjà Vu»"
        expected_out = "Café <<Déjà Vu>>"
        normalized_text = normalize_unicode_and_characters(unicode_text)
        self.assertEqual(normalized_text, expected_out)

        # This passes straight through (no diacritics)
        unicode_text = "شكرا لك"
        normalized_text = normalize_unicode_and_characters(unicode_text)
        self.assertEqual(normalized_text, unicode_text)

        # mdash to `--`
        unicode_text = "– über schön! —"
        expected_out = "- über schön! --"
        normalized_text = normalize_unicode_and_characters(unicode_text)
        self.assertEqual(normalized_text, expected_out)

        # \u004E\u0303 is Ñ (N + tilde) and the normalization converts it to a
        # single unicode character. ñ stays and combines the diacritic and letter
        unicode_text = "\u004E\u0303a\u006E\u0303o malcriado"
        expected_out = "Ñaño malcriado"
        normalized_text = normalize_unicode_and_characters(unicode_text)
        self.assertEqual(normalized_text, expected_out)


class TestUnicodeImport(DataMappingBaseTestCase):
    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties-unicode.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['unicode']
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        filepath = osp.join(osp.dirname(__file__), 'data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=pathlib.Path(filepath).read_bytes()
        )
        self.import_file.save()

        # self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        # self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_unicode_import(self):
        """Test that unicode characters are imported correctly"""
        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.pk)
        tasks.map_data(self.import_file.pk)

        # Check to make sure all the properties imported
        ps = PropertyState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file,
        )
        self.assertEqual(len(ps), 3)

        # check that the property has the unicode characters
        ps = PropertyState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file,
            custom_id_1='unicode-1',
        )[0]
        self.assertEqual(ps.property_name, 'Déjà vu Café')
        # check if there is an extra data key with unicode
        self.assertEqual('بيانات اضافية' in ps.extra_data, True)

        # check that we can query on unicode character
        ps = PropertyState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file,
            property_name='🏦 Bank',
        )[0]
        self.assertIsNotNone(ps)

        tasks.geocode_and_match_buildings_task(self.import_file.id)

        qry = PropertyView.objects.filter(state__custom_id_1='unicode-1')
        self.assertEqual(qry.count(), 1)
        state = qry.first().state

        self.assertEqual(state.property_name, "Déjà vu Café")

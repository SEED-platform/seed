"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
import os.path as osp
import pathlib

from django.core.files.uploadedfile import SimpleUploadedFile

from seed.data_importer import tasks
from seed.data_importer.tests.util import FAKE_EXTRA_DATA, FAKE_MAPPINGS, FAKE_ROW
from seed.models import ASSESSED_RAW, DATA_STATE_MAPPING, Column, PropertyState, TaxLotState, TaxLotView
from seed.tests.util import DataMappingBaseTestCase

logger = logging.getLogger(__name__)


class TestCaseB(DataMappingBaseTestCase):
    def setUp(self):
        filename = getattr(self, "filename", "example-data-properties.xlsx")
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS["portfolio"]
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        filepath = osp.join(osp.dirname(__file__), "..", "data", filename)
        self.import_file.file = SimpleUploadedFile(name=filename, content=pathlib.Path(filepath).read_bytes())
        self.import_file.save()

    def test_match_buildings(self):
        """case B (many property <-> one tax lot)"""
        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.pk)
        # Set remap to True because for some reason this file id has been imported before.
        tasks.map_data(self.import_file.pk, True)

        # Check to make sure all the properties imported
        ps = PropertyState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file,
        )
        self.assertEqual(len(ps), 14)

        # Check to make sure the tax lots were imported
        ts = TaxLotState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file,
        )
        self.assertEqual(len(ts), 18)

        # verify that the lot_number has the tax_lot information. For this case it is one-to-many
        p_test = PropertyState.objects.filter(
            pm_property_id="5233255",
            organization=self.org,
            data_state=DATA_STATE_MAPPING,
            import_file=self.import_file,
        ).first()
        self.assertEqual(p_test.lot_number, "333/66555;333/66125;333/66148")

        tasks.geocode_and_match_buildings_task(self.import_file.id)

        # make sure the property only has one tax lot and vice versa
        tlv = TaxLotView.objects.filter(state__jurisdiction_tax_lot_id="11160509", cycle=self.cycle)
        self.assertEqual(len(tlv), 1)
        tlv = tlv[0]
        properties = tlv.property_states()
        self.assertEqual(len(properties), 3)

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from seed.data_importer.tasks import EquivalencePartitioner
from seed.data_importer.tests.util import DataMappingBaseTestCase

logger = logging.getLogger(__name__)


class EZState(object):

    def __init__(self, *args, **kwds):
        for arg in args:
            setattr(self, arg, None)

        for (k, v) in kwds.items():
            setattr(self, k, v)


class PropertyState(EZState):

    def __init__(self, **kwds):
        super(PropertyState, self).__init__("pm_property_id", "custom_id_1", "normalized_address", **kwds)


class TaxLotState(EZState):

    def __init__(self, **kwds):
        super(TaxLotState, self).__init__("jurisdiction_tax_lot_id", "custom_id_1", "normalized_address", **kwds)


class TestEquivalenceClassGenerator(DataMappingBaseTestCase):

    def test_equivalence(self):
        partitioner = EquivalencePartitioner.make_propertystate_equivalence()

        p1 = PropertyState(pm_property_id=100)
        p2 = PropertyState(pm_property_id=100)
        p3 = PropertyState(pm_property_id=200)
        p4 = PropertyState(custom_id_1=100)

        equivalence_classes = partitioner.calculate_equivalence_classes([p1, p2])
        self.assertEqual(len(equivalence_classes), 1)

        equivalence_classes = partitioner.calculate_equivalence_classes([p1, p3])
        self.assertEqual(len(equivalence_classes), 2)

        equivalence_classes = partitioner.calculate_equivalence_classes([p1, p4])
        self.assertEqual(len(equivalence_classes), 1)

        return

    def test_a_dummy_class_basics(self):
        tls1 = TaxLotState(jurisdiction_tax_lot_id="1")
        tls2 = TaxLotState(jurisdiction_tax_lot_id="1", custom_id_1="100")
        tls3 = TaxLotState(jurisdiction_tax_lot_id="1", custom_id_1="100", normalized_address="123 fake street")

        self.assertEqual(tls1.jurisdiction_tax_lot_id, "1")
        self.assertEqual(tls1.custom_id_1, None)
        self.assertEqual(tls1.normalized_address, None)

        self.assertEqual(tls2.jurisdiction_tax_lot_id, "1")
        self.assertEqual(tls2.custom_id_1, "100")
        self.assertEqual(tls2.normalized_address, None)

        self.assertEqual(tls3.jurisdiction_tax_lot_id, "1")
        self.assertEqual(tls3.custom_id_1, "100")
        self.assertEqual(tls3.normalized_address, "123 fake street")

        return

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import random

from seed.models import (BuildingSnapshot)
from seed.test_helpers.factory.helpers import DjangoFunctionalFactory


class SEEDFactory(DjangoFunctionalFactory):
    """model factory for SEED"""

    @classmethod
    def building_snapshot(cls, canonical_building=None, *args, **kwargs):
        """creates an BuildingSnapshot inst.

           if canonical_building (CanonicalBuilding inst.) is None, then a
           CanonicalBuilding inst. is created and a BuildingSnapshot inst. is
           created and linked to the CanonicalBuilding inst.

           Usage:
            ab = SEEDFactory.assessed_building()
            cb = ab.canonical_building
            b_snapshot = cb.canonical_snapshot
            print ab.year_built == b_snapshot.year_built  # True

           or loop through to create a whole bunch:
            for i in range(10):
                SEEDFactory.building_snapshot(name='tester_' % i)

        """

        defaults = {
            "tax_lot_id": cls.rand_str(length=50),
            "pm_property_id": cls.rand_str(length=50),
            "custom_id_1": cls.rand_str(length=50),
            "gross_floor_area": random.uniform(35000, 50000),
            "year_built": random.randint(1900, 2012),
            "address_line_1": cls.rand_street_address(),
            "postal_code": str(random.randint(43214, 97214)),
            "property_name": cls.rand_name(),
        }

        b, created = BuildingSnapshot.objects.get_or_create(
            tax_lot_id=defaults['tax_lot_id'],
            canonical_building=canonical_building,
        )

        defaults.update(kwargs)
        if created:
            for k, v in defaults.items():
                setattr(b, k, v)
            b.save()

        return b

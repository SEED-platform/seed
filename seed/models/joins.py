# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import unicode_literals

import logging

from django.db import models

# from seed.models.measures import Measure

logger = logging.getLogger(__name__)


class TaxLotProperty(models.Model):
    property_view = models.ForeignKey('PropertyView')
    taxlot_view = models.ForeignKey('TaxLotView')
    cycle = models.ForeignKey('Cycle')

    # If there is a complex TaxLot/Property association, this field
    # lists the "main" tax lot that Properties should be reported under.
    # User controlled flag.
    primary = models.BooleanField(default=True)

    def __unicode__(self):
        return u'M2M Property View %s / TaxLot View %s' % (
            self.property_view_id, self.taxlot_view_id)

    class Meta:
        unique_together = ('property_view', 'taxlot_view',)
        index_together = [
            ['cycle', 'property_view'],
            ['cycle', 'taxlot_view'],
            ['property_view', 'taxlot_view']
        ]


class PropertyMeasure(models.Model):
    RECOMMENDED = 1
    PROPOSED = 2
    IMPLEMENTED = 3

    IMPLEMENTATION_TYPES = (
        (RECOMMENDED, 'Recommended'),
        (PROPOSED, 'Proposed'),
        (IMPLEMENTED, 'Implemented'),
    )

    measure = models.ForeignKey('Measure', on_delete=models.DO_NOTHING)
    property_state = models.ForeignKey('PropertyState', on_delete=models.DO_NOTHING)
    implementation_status = models.IntegerField(choices=IMPLEMENTATION_TYPES, default=RECOMMENDED)

    @classmethod
    def str_to_impl_status(cls, impl_status):
        if not impl_status:
            return None

        value = [y[0] for x, y in enumerate(cls.IMPLEMENTATION_TYPES) if y[1] == impl_status]
        if len(value) == 1:
            return value[0]
        else:
            return None

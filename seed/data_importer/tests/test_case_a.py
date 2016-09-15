# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import datetime
import logging
from unittest import skip

from dateutil import parser
from django.test import TestCase
from mock import patch

from seed.data_importer import tasks
from seed.data_importer.models import ImportFile
from seed.data_importer.tests import util as test_util
from seed.models import (
    ASSESSED_RAW,
    ASSESSED_BS,
    PORTFOLIO_BS,
    POSSIBLE_MATCH,
    SYSTEM_MATCH,
    DATA_STATE_IMPORT,
    Cycle,
    PropertyState,
    PropertyView,
    Column,
    get_ancestors,
    DATA_STATE_MAPPING
)
from seed.tests import util

logger = logging.getLogger(__name__)


class TestCaseA(TestCase):

    def setUp(self):
        test_util.import_example_data(self, 'example-data-properties.xlsx')

    def test_match_buildings(self):
        """Good case for testing our matching system."""

        cycle, _ = Cycle.objects.get_or_create(
            name=u'Test Hack Cycle 2015',
            organization=self.fake_org,
            start=datetime.datetime(2015, 1, 1),
            end=datetime.datetime(2015, 12, 31),
        )

        ps = PropertyState.objects.filter(data_state=DATA_STATE_MAPPING,
                                          super_organization=self.fake_org)
        print len(ps)

        # Promote case A (one property <-> one tax lot)
        ps = PropertyState.objects.filter(building_portfolio_manager_identifier=2264)[0]

        ps.promote(cycle)

        ps = tasks.get_canonical_snapshots(self.fake_org)
        from django.db.models.query import QuerySet
        self.assertTrue(isinstance(ps, QuerySet))
        logger.debug("There are %s properties" % len(ps))
        for p in ps:
            from seed.utils.generic import pp
            pp(p)

        self.assertEqual(len(ps), 1)
        self.assertEqual(ps[0].address_line_1, '50 Willow Ave SE')

        ed = ps[0].extra_data
        self.assertEqual(ed['extra_data_1'], 'a')
        self.assertEqual('extra_data_2' in ed.keys(), False)

        # # Promote 5 of these to views to test the remaining code
        # promote_mes = PropertyState.objects.filter(
        #     data_state=DATA_STATE_MAPPING,
        #     super_organization=self.fake_org)[:5]
        # for promote_me in promote_mes:
        #     promote_me.promote(cycle)
        #
        # ps = tasks.get_canonical_snapshots(self.fake_org)
        # from django.db.models.query import QuerySet
        # self.assertTrue(isinstance(ps, QuerySet))
        # logger.debug("There are %s properties" % len(ps))
        # for p in ps:
        #     print p
        #
        # self.assertEqual(len(ps), 5)
        # self.assertEqual(ps[0].address_line_1, '1211 Bryant Street')
        # self.assertEqual(ps[4].address_line_1, '1031 Ellis Lane')

        # tasks.match_buildings(self.import_file.pk, self.fake_user.pk)

        # self.assertEqual(result.property_name, snapshot.property_name)
        # self.assertEqual(result.property_name, new_snapshot.property_name)
        # # Since these two buildings share a common ID, we match that way.
        # # self.assertEqual(result.confidence, 0.9)
        # self.assertEqual(
        #     sorted([r.pk for r in result.parents.all()]),
        #     sorted([new_snapshot.pk, snapshot.pk])
        # )
        # self.assertGreater(AuditLog.objects.count(), 0)
        # self.assertEqual(
        #     AuditLog.objects.first().action_note,
        #     'System matched building ID.'
        # )

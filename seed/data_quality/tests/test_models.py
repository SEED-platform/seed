# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from django.test import TestCase

from seed.data_quality.models import DataQualityCheck, Rule
from seed.data_quality.models import (
    TYPE_NUMBER,
    RULE_TYPE_DEFAULT,
    SEVERITY_ERROR,
    CATEGORY_IN_RANGE_CHECKING
)
from seed.lib.superperms.orgs.models import Organization
from seed.models import StatusLabel

_log = logging.getLogger(__name__)


class DataQualityRules(TestCase):
    def setUp(self):
        self.org = Organization.objects.create()

    def test_ensure_default_rules(self):
        dq = DataQualityCheck.retrieve(self.org)
        initial_pk = dq.pk
        self.assertEqual(dq.rules.count(), 27)
        self.assertEqual(dq.results, {})

        dq = DataQualityCheck.retrieve(self.org)
        self.assertEqual(dq.rules.count(), 27)
        self.assertEqual(initial_pk, dq.pk)

        dq = DataQualityCheck.retrieve(self.org.pk)
        self.assertEqual(dq.rules.count(), 27)

    def test_remove_all_rules(self):
        dq = DataQualityCheck.retrieve(self.org)
        count = Rule.objects.filter(data_quality_check_id=dq.pk).count()
        self.assertEqual(count, 27)

        dq.remove_all_rules()
        self.assertEqual(dq.rules.count(), 0)
        # ensure that the database has no rules for this dq associated with it
        count = Rule.objects.filter(data_quality_check_id=dq.pk).count()
        self.assertEqual(count, 0)

    def test_add_new_rule_exception(self):
        dq = DataQualityCheck.retrieve(self.org)
        new_rule = {
            'wrong': 'data'
        }
        with self.assertRaisesRegexp(
                TypeError,
                "Rule data is not defined correctly: 'wrong' is an invalid keyword argument for this function"
        ):
            dq.add_rule(new_rule)

    def test_add_new_rule(self):
        dq = DataQualityCheck.retrieve(self.org)

        new_rule = {
            'table_name': 'PropertyState',
            'field': 'conditioned_floor_area',
            'data_type': TYPE_NUMBER,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 0,
            'max': 7000000,
            'severity': SEVERITY_ERROR,
            'units': 'square feet',
            'category': CATEGORY_IN_RANGE_CHECKING,
        }
        dq.add_rule(new_rule)
        self.assertEqual(dq.rules.count(), 28)

    def test_filter_rules(self):
        dq = DataQualityCheck.retrieve(self.org)
        rules = dq.rules.filter(category=CATEGORY_IN_RANGE_CHECKING, enabled=True)
        self.assertEqual(rules.count(), 17)

    def test_rule_with_label(self):
        dq = DataQualityCheck.retrieve(self.org)
        rules = dq.rules.filter(status_label__isnull=False)
        self.assertEqual(rules.count(), 0)

        sl_data = {'name': 'test label on rule', 'super_organization': self.org}
        status_label, _ = StatusLabel.objects.get_or_create(**sl_data)
        sls = StatusLabel.objects.filter(**sl_data)
        self.assertEqual(sls.count(), 1)
        new_rule = {
            'table_name': 'PropertyState',
            'field': 'conditioned_floor_area',
            'data_type': TYPE_NUMBER,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 0,
            'max': 7000000,
            'severity': SEVERITY_ERROR,
            'units': 'square feet',
            'category': CATEGORY_IN_RANGE_CHECKING,
            'status_label': status_label
        }
        dq.add_rule(new_rule)
        rules = dq.rules.filter(status_label__isnull=False)
        self.assertEqual(rules.count(), 1)
        self.assertEqual(rules[0].status_label, status_label)

        # delete the rule and make sure that the status label removes
        dq.remove_all_rules()
        sls = StatusLabel.objects.filter(**sl_data)
        self.assertEqual(sls.count(), 0)

    def test_rule_with_label_set_to_null(self):
        dq = DataQualityCheck.retrieve(self.org)
        sl_data = {'name': 'test label on rule for null', 'super_organization': self.org}
        status_label, _ = StatusLabel.objects.get_or_create(**sl_data)
        new_rule = {
            'name': 'Name not to be forgotten',
            'table_name': 'PropertyState',
            'field': 'conditioned_floor_area',
            'data_type': TYPE_NUMBER,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 0,
            'max': 7000000,
            'severity': SEVERITY_ERROR,
            'units': 'square feet',
            'category': CATEGORY_IN_RANGE_CHECKING,
            'status_label': status_label
        }
        dq.add_rule(new_rule)

        rules = dq.rules.filter(status_label__isnull=False)

        self.assertEqual(rules.count(), 1)
        self.assertEqual(rules[0].status_label, status_label)
        status_label.delete()

        rules = dq.rules.filter(name='Name not to be forgotten')
        self.assertEqual(rules.count(), 1)
        self.assertEqual(rules[0].status_label, None)

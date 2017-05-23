# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from django.test import TestCase

from seed.lib.superperms.orgs.models import Organization
from seed.models import StatusLabel
from seed.models.data_quality import (
    DataQualityCheck,
    Rule,
    DEFAULT_RULES,
    TYPE_NUMBER,
    TYPE_STRING,
    RULE_TYPE_DEFAULT,
    SEVERITY_ERROR,
)

_log = logging.getLogger(__name__)


class RuleTests(TestCase):

    def setUp(self):
        self.org = Organization.objects.create()

    def test_min_max(self):
        new_rule = {
            'data_type': TYPE_NUMBER,
            'min': 0,
            'max': 100,
        }
        r = Rule.objects.create(**new_rule)
        self.assertTrue(r.minimum_valid(0))
        self.assertFalse(r.minimum_valid(-1))
        self.assertTrue(r.maximum_valid(100))
        self.assertFalse(r.maximum_valid(101))

    def test_valid_enum(self):
        new_rule = {
            'data_type': TYPE_STRING,
            'text_match': 'alpha',
        }
        r = Rule.objects.create(**new_rule)
        self.assertTrue(r.valid_enum('alpha'))
        self.assertFalse(r.valid_enum('beta'))
        self.assertTrue(r.valid_enum(u'alpha'))
        self.assertFalse(r.valid_enum(u'beta'))


class DataQualityCheckCase(TestCase):

    def setUp(self):
        self.org = Organization.objects.create()

    def test_multiple_data_quality_check_objects(self):
        dq = DataQualityCheck.retrieve(self.org)
        self.assertEqual(dq.name, 'Default Data Quality Check')

        DataQualityCheck.objects.create(organization=self.org, name='test manual creation')
        DataQualityCheck.objects.create(organization=self.org, name='test manual creation 2')
        DataQualityCheck.objects.create(organization=self.org, name='test manual creation 3')
        dq = DataQualityCheck.retrieve(self.org)

        # The method above will delete the multiple objects and return the original
        self.assertEqual(dq.name, 'Default Data Quality Check')


class DataQualityCheckRules(TestCase):

    def setUp(self):
        self.org = Organization.objects.create()

    def test_ensure_default_rules(self):
        dq = DataQualityCheck.retrieve(self.org)
        initial_pk = dq.pk

        self.assertEqual(dq.rules.count(), len(DEFAULT_RULES))
        self.assertEqual(dq.results, {})
        self.assertEqual(initial_pk, dq.pk)

        # check again to make sure that it doesn't append more rules to the same org
        dq = DataQualityCheck.retrieve(self.org.pk)
        self.assertEqual(dq.rules.count(), len(DEFAULT_RULES))

    def test_remove_all_rules(self):
        dq = DataQualityCheck.retrieve(self.org)
        count = Rule.objects.filter(data_quality_check_id=dq.pk).count()
        self.assertEqual(count, len(DEFAULT_RULES))

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

    def test_add_new_rule_and_reset(self):
        dq = DataQualityCheck.retrieve(self.org)

        new_rule = {
            'table_name': 'PropertyState',
            'field': 'conditioned_floor_area',
            'data_type': TYPE_NUMBER,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 0,
            'max': 7000000,
            'severity': SEVERITY_ERROR,
            'units': 'square feet'
        }
        dq.add_rule(new_rule)
        self.assertEqual(dq.rules.count(), len(DEFAULT_RULES) + 1)

        dq.reset_all_rules()
        self.assertEqual(dq.rules.count(), len(DEFAULT_RULES))

    def test_reset_default_rules(self):
        dq = DataQualityCheck.retrieve(self.org)

        new_rule = {
            'table_name': 'PropertyState',
            'field': 'test_floor_area',
            'data_type': TYPE_NUMBER,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 0,
            'max': 7000000,
            'severity': SEVERITY_ERROR,
            'units': 'square feet'
        }
        dq.add_rule(new_rule)
        self.assertEqual(dq.rules.count(), len(DEFAULT_RULES) + 1)

        # change one of the default rules
        rule = dq.rules.filter(field='gross_floor_area').first()
        rule.min = -10000
        rule.save()

        self.assertEqual(dq.rules.filter(field='gross_floor_area').first().min, -10000)
        dq.reset_default_rules()

        self.assertEqual(dq.rules.filter(field='gross_floor_area').first().min, 100)

        # ensure non-default rule still exists
        non_def_rules = dq.rules.filter(field='test_floor_area')
        self.assertEqual(non_def_rules.count(), 1)

    def test_filter_rules(self):
        dq = DataQualityCheck.retrieve(self.org)

        rule_count = dq.rules.filter(enabled=True).count()

        # disable one of the rules
        rule = dq.rules.first()
        rule.enabled = False
        rule.save()

        rules = dq.rules.filter(enabled=True)
        self.assertEqual(rules.count(), rule_count - 1)

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
            'status_label': status_label
        }
        dq.add_rule(new_rule)
        rules = dq.rules.filter(status_label__isnull=False)
        self.assertEqual(rules.count(), 1)
        self.assertEqual(rules[0].status_label, status_label)

        # delete the rule but make sure that the label does not get deleted
        dq.remove_all_rules()
        sls = StatusLabel.objects.filter(**sl_data)
        self.assertEqual(sls.count(), 1)

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
            'status_label': status_label
        }
        dq.add_rule(new_rule)

        rules = dq.rules.filter(status_label__isnull=False)
        self.assertEqual(rules.count(), 1)
        self.assertEqual(rules[0].status_label, status_label)
        status_label.delete()

        rules = dq.rules.filter(name='Name not to be forgotten')
        self.assertEqual(rules.count(), 1)
        # TODO: Check with Alex, the label exists if the rule still points to it, right?
        # print rules[0]
        # self.assertEqual(rules[0].status_label, status_label)

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
from datetime import datetime

import pytz
from django.test import TestCase
from django.utils.timezone import make_aware, make_naive

from seed.lib.superperms.orgs.models import Organization
from seed.models import StatusLabel
from seed.models.data_quality import (
    DataQualityCheck,
    Rule,
    DEFAULT_RULES,
    TYPE_NUMBER,
    TYPE_DATE,
    TYPE_YEAR,
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

    def text_min_only(self):
        new_rule = {
            'data_type': TYPE_NUMBER,
            'min': 5,
        }
        r = Rule.objects.create(**new_rule)
        self.assertTrue(r.minimum_valid(0))
        self.assertFalse(r.minimum_valid(10))
        self.assertTrue(r.maximum_valid(100))
        self.assertTrue(r.maximum_valid(999999))

    def text_max_only(self):
        new_rule = {
            'data_type': TYPE_NUMBER,
            'max': 100,
        }
        r = Rule.objects.create(**new_rule)
        self.assertTrue(r.minimum_valid(0))
        self.assertTrue(r.minimum_valid(999999))
        self.assertTrue(r.maximum_valid(50))
        self.assertFalse(r.maximum_valid(200))

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

    def test_valid_enum_regex(self):
        # test with regex
        new_rule = {
            'data_type': TYPE_STRING,
            'text_match': '.*(a|b)cd(4|8).*'
        }
        r = Rule.objects.create(**new_rule)
        self.assertTrue(r.valid_enum('bcd8'))
        self.assertTrue(r.valid_enum('pretext acd4 posttext'))
        self.assertTrue(r.valid_enum('pretextbcd8posttext'))
        self.assertFalse(r.valid_enum('pretextbcd6posttext'))

    def test_type_value_return(self):
        """Test to make sure that the return is correct if value is not a string"""
        new_rule = {
            'data_type': TYPE_STRING,
        }
        r = Rule.objects.create(**new_rule)
        self.assertEqual(r.str_to_data_type(int(576)), 576)
        self.assertEqual(r.str_to_data_type(576.5), 576.5)

    def test_type_value_string(self):
        new_rule = {
            'data_type': TYPE_STRING,
        }
        r = Rule.objects.create(**new_rule)
        self.assertEqual(r.str_to_data_type(None), None)
        self.assertEqual(r.str_to_data_type(''), '')
        self.assertEqual(r.str_to_data_type('576'), '576')
        self.assertEqual(r.str_to_data_type('abcd'), 'abcd')
        self.assertEqual(r.str_to_data_type(u'abcd'), u'abcd')

    def test_type_value_number(self):
        new_rule = {
            'data_type': TYPE_NUMBER,
        }
        r = Rule.objects.create(**new_rule)
        self.assertEqual(r.str_to_data_type(None), None)
        self.assertEqual(r.str_to_data_type(''), None)
        self.assertEqual(r.str_to_data_type('576'), 576)
        self.assertEqual(r.str_to_data_type('576.5'), 576.5)
        with self.assertRaisesRegexp(TypeError, ".*string to float.*abcd"):
            r.str_to_data_type('abcd')

    def test_type_value_date(self):
        new_rule = {
            'data_type': TYPE_DATE,
        }
        r = Rule.objects.create(**new_rule)

        self.assertEqual(r.str_to_data_type(None), None)
        self.assertEqual(r.str_to_data_type(''), None)
        dt = make_aware(datetime(2016, 0o7, 15, 12, 30), pytz.UTC)
        self.assertEqual(r.str_to_data_type(dt.strftime("%Y-%m-%d %H:%M")), dt)
        self.assertEqual(r.str_to_data_type('abcd'), None)

    def test_type_value_year(self):
        new_rule = {
            'data_type': TYPE_YEAR,
        }
        r = Rule.objects.create(**new_rule)

        self.assertEqual(r.str_to_data_type(None), None)
        self.assertEqual(r.str_to_data_type(''), None)
        dt = make_aware(datetime(2016, 0o7, 15, 12, 30), pytz.UTC)
        self.assertEqual(r.str_to_data_type(dt.strftime("%Y-%m-%d %H:%M")), dt.date())
        self.assertEqual(r.str_to_data_type('abcd'), None)

    def test_format_rule_string_string(self):
        new_rule = {
            'data_type': TYPE_STRING,
            'max': 27,
        }
        r = Rule.objects.create(**new_rule)
        self.assertEqual(r.format_strings('something blue'), ['None', '27', 'something blue'])

    def test_format_strings_int(self):
        new_rule = {
            'data_type': TYPE_NUMBER,
            'min': 27,
        }
        r = Rule.objects.create(**new_rule)
        self.assertEqual(r.format_strings(int(100)), ['27', None, '100'])

        new_rule = {
            'data_type': TYPE_NUMBER,
            'max': 27,
        }
        r = Rule.objects.create(**new_rule)
        self.assertEqual(r.format_strings(int(100)), [None, '27', '100'])

    def test_format_strings_float(self):
        new_rule = {
            'data_type': TYPE_NUMBER,
            'min': 27,
        }
        r = Rule.objects.create(**new_rule)
        self.assertEqual(r.format_strings(100.0), ['27', None, '100.0'])

        new_rule = {
            'data_type': TYPE_NUMBER,
            'max': 27,
        }
        r = Rule.objects.create(**new_rule)
        self.assertEqual(r.format_strings(123.45), [None, '27', '123.45'])

    def test_format_strings_datetime(self):
        new_rule = {
            'data_type': TYPE_YEAR,
            'min': '20170101'
        }
        r = Rule.objects.create(**new_rule)
        # the strings are tz naive, but must be passed in as tz aware.
        dt = make_aware(datetime(2016, 0o7, 15, 12, 30), pytz.UTC)
        self.assertEqual(r.format_strings(dt),
                         ['2017-01-01 00:00:00', None, str(make_naive(dt, pytz.UTC))])

        new_rule = {
            'data_type': TYPE_YEAR,
            'max': '20170101'
        }
        r = Rule.objects.create(**new_rule)
        self.assertEqual(r.format_strings(dt),
                         [None, '2017-01-01 00:00:00', str(make_naive(dt, pytz.UTC))])

    def test_format_strings_date(self):
        new_rule = {
            'data_type': TYPE_YEAR,
            'min': '20170101'
        }
        r = Rule.objects.create(**new_rule)
        # the strings are tz naive, but must be passed in as tz aware.
        dt = make_aware(datetime(2016, 0o7, 15, 12, 30), pytz.UTC).date()
        self.assertEqual(r.format_strings(dt),
                         ['2017-01-01', None, str(dt)])

        new_rule = {
            'data_type': TYPE_YEAR,
            'max': '20170101'
        }
        r = Rule.objects.create(**new_rule)
        self.assertEqual(r.format_strings(dt),
                         [None, '2017-01-01', str(dt)])


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

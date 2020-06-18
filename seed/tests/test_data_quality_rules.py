# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from copy import deepcopy

from django.urls import reverse

from seed.models.data_quality import (
    DataQualityCheck,
    Rule,
)
from seed.models.models import ASSESSED_RAW

from seed.tests.util import DataMappingBaseTestCase


class RuleViewTests(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)

        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.client.login(
            username='test_user@demo.com',
            password='test_pass',
            email='test_user@demo.com'
        )

    def test_update_rule_valid_severity_label_validation(self):
        # Start with 1 Rule
        dq = DataQualityCheck.retrieve(self.org.id)
        dq.remove_all_rules()
        base_rule_info = {
            'field': 'address_line_1',
            'table_name': 'PropertyState',
            'enabled': True,
            'data_type': Rule.TYPE_STRING,
            'rule_type': Rule.RULE_TYPE_DEFAULT,
            'condition': Rule.RULE_INCLUDE,
            'required': False,
            'not_null': False,
            'min': None,
            'max': None,
            'text_match': 'Test Rule 1',
            'severity': Rule.SEVERITY_ERROR,
            'units': "",
        }
        dq.add_rule(base_rule_info)
        rule = dq.rules.get()

        # Send invalid update request
        put_data = deepcopy(base_rule_info)
        put_data['severity'] = dict(Rule.SEVERITY).get(Rule.SEVERITY_VALID)
        put_data['status_label'] = None
        url = reverse('api:v3:data_quality_check-rules-detail', kwargs={
            'nested_organization_id': self.org.id,
            'pk': rule.id
        })
        res = self.client.put(url, content_type='application/json', data=json.dumps(put_data))

        self.assertEqual(res.status_code, 400)
        self.assertTrue('Label must be assigned when using \'Valid\' Data Severity.' in json.loads(res.content)['general_validation_error'])

        # Add label to rule and change severity to valid, then try to remove label
        rule.status_label = self.org.labels.first()
        rule.severity = Rule.SEVERITY_VALID
        rule.save()

        put_data_2 = deepcopy(base_rule_info)
        del put_data_2['severity']  # don't update severity
        put_data_2['status_label'] = ""
        url = reverse('api:v3:data_quality_check-rules-detail', kwargs={
            'nested_organization_id': self.org.id,
            'pk': rule.id
        })
        res = self.client.put(url, content_type='application/json', data=json.dumps(put_data_2))

        self.assertEqual(res.status_code, 400)
        self.assertTrue('Label must be assigned when using \'Valid\' Data Severity.' in json.loads(res.content)['general_validation_error'])

    def test_update_rule_include_empty_text_match_validation(self):
        # Start with 1 Rule
        dq = DataQualityCheck.retrieve(self.org.id)
        dq.remove_all_rules()
        base_rule_info = {
            'field': 'address_line_1',
            'table_name': 'PropertyState',
            'enabled': True,
            'data_type': Rule.TYPE_STRING,
            'rule_type': Rule.RULE_TYPE_DEFAULT,
            'condition': Rule.RULE_INCLUDE,
            'required': False,
            'not_null': False,
            'min': None,
            'max': None,
            'text_match': 'Test Rule 1',
            'severity': Rule.SEVERITY_ERROR,
            'units': "",
        }
        dq.add_rule(base_rule_info)
        rule = dq.rules.get()

        # Send invalid update request
        put_data = deepcopy(base_rule_info)
        put_data['text_match'] = None
        url = reverse('api:v3:data_quality_check-rules-detail', kwargs={
            'nested_organization_id': self.org.id,
            'pk': rule.id
        })
        res = self.client.put(url, content_type='application/json', data=json.dumps(put_data))

        self.assertEqual(res.status_code, 400)
        self.assertTrue('Rule must not include or exclude an empty string.' in json.loads(res.content)['general_validation_error'])

        # Remove text_match and make condition NOT_NULL, then try making condition EXCLUDE
        rule.text_match = None
        rule.condition = Rule.RULE_NOT_NULL
        rule.save()

        put_data_2 = deepcopy(base_rule_info)
        del put_data_2['text_match']  # don't update text_match
        put_data_2['condition'] = Rule.RULE_EXCLUDE
        url = reverse('api:v3:data_quality_check-rules-detail', kwargs={
            'nested_organization_id': self.org.id,
            'pk': dq.rules.get().id
        })
        res = self.client.put(url, content_type='application/json', data=json.dumps(put_data_2))

        self.assertEqual(res.status_code, 400)
        self.assertTrue('Rule must not include or exclude an empty string.' in json.loads(res.content)['general_validation_error'])

    def test_valid_data_rule_without_label_does_not_actually_update_or_delete_any_rules(self):
        # Start with 3 Rules
        dq = DataQualityCheck.retrieve(self.org.id)
        dq.remove_all_rules()
        base_rule_info = {
            'field': 'address_line_1',
            'table_name': 'PropertyState',
            'enabled': True,
            'data_type': Rule.TYPE_STRING,
            'rule_type': Rule.RULE_TYPE_DEFAULT,
            'condition': Rule.RULE_INCLUDE,
            'required': False,
            'not_null': False,
            'min': None,
            'max': None,
            'text_match': 'Test Rule 1',
            'severity': Rule.SEVERITY_ERROR,
            'units': "",
            'status_label_id': None
        }
        dq.add_rule(base_rule_info)

        rule_2_info = deepcopy(base_rule_info)
        rule_2_info['text_match'] = 'Test Rule 2'
        dq.add_rule(rule_2_info)

        rule_3_info = deepcopy(base_rule_info)
        rule_3_info['text_match'] = 'Test Rule 3'
        dq.add_rule(rule_3_info)

        self.assertEqual(dq.rules.count(), 3)

        property_rules = [base_rule_info, rule_2_info, rule_3_info]

        # Make some adjustments to mimic how data is expected in API endpoint
        rule_3_info['severity'] = dict(Rule.SEVERITY).get(Rule.SEVERITY_ERROR)
        for rule in property_rules:
            rule['data_type'] = dict(Rule.DATA_TYPES).get(rule['data_type'])
            rule['label'] = None

        # Make 2 rules trigger the "valid without label" failure
        base_rule_info['severity'] = dict(Rule.SEVERITY).get(Rule.SEVERITY_VALID)
        rule_2_info['severity'] = dict(Rule.SEVERITY).get(Rule.SEVERITY_VALID)

        url = reverse('api:v2:data_quality_checks-save-data-quality-rules') + '?organization_id=' + str(self.org.pk)
        post_data = {
            "data_quality_rules": {
                "properties": property_rules,
                "taxlots": [],
            },
        }
        res = self.client.post(url, content_type='application/json', data=json.dumps(post_data))

        self.assertEqual(res.status_code, 400)
        self.assertEqual(json.loads(res.content)['message'], 'Label must be assigned when using Valid Data Severity.')

        # Count 3 total rules. None of them were updated
        self.assertEqual(dq.rules.count(), 3)
        self.assertEqual(dq.rules.filter(severity=Rule.SEVERITY_VALID).count(), 0)

    def test_include_exclude_without_text_match_does_not_actually_update_or_delete_any_rules(self):
        # Start with 3 Rules
        dq = DataQualityCheck.retrieve(self.org.id)
        dq.remove_all_rules()
        base_rule_info = {
            'field': 'address_line_1',
            'table_name': 'PropertyState',
            'enabled': True,
            'data_type': Rule.TYPE_STRING,
            'rule_type': Rule.RULE_TYPE_DEFAULT,
            'condition': Rule.RULE_INCLUDE,
            'required': False,
            'not_null': False,
            'min': None,
            'max': None,
            'text_match': 'Test Rule 1',
            'severity': Rule.SEVERITY_ERROR,
            'units': "",
            'status_label_id': None
        }
        dq.add_rule(base_rule_info)

        rule_2_info = deepcopy(base_rule_info)
        rule_2_info['text_match'] = 'Test Rule 2'
        dq.add_rule(rule_2_info)

        rule_3_info = deepcopy(base_rule_info)
        rule_3_info['text_match'] = 'Test Rule 3'
        dq.add_rule(rule_3_info)

        self.assertEqual(dq.rules.count(), 3)

        property_rules = [base_rule_info, rule_2_info, rule_3_info]

        # Make some adjustments to mimic how data is expected in API endpoint
        rule_3_info['severity'] = dict(Rule.SEVERITY).get(Rule.SEVERITY_ERROR)
        for rule in property_rules:
            rule['data_type'] = dict(Rule.DATA_TYPES).get(rule['data_type'])
            rule['label'] = None

        # Make 2 rules trigger the include or exclude without text_match failure
        base_rule_info['text_match'] = ''

        rule_2_info['condition'] = Rule.RULE_EXCLUDE
        rule_2_info['text_match'] = ''

        url = reverse('api:v2:data_quality_checks-save-data-quality-rules') + '?organization_id=' + str(self.org.pk)
        post_data = {
            "data_quality_rules": {
                "properties": property_rules,
                "taxlots": [],
            },
        }
        res = self.client.post(url, content_type='application/json', data=json.dumps(post_data))

        self.assertEqual(res.status_code, 400)
        self.assertEqual(json.loads(res.content)['message'], 'Rule must not include or exclude an empty string.')

        # Count 3 total rules. None of them were updated
        self.assertEqual(dq.rules.count(), 3)
        self.assertEqual(dq.rules.filter(condition=Rule.RULE_EXCLUDE).count(), 0)
        self.assertEqual(dq.rules.filter(text_match='').count(), 0)

    def test_failed_rule_creation_doesnt_prevent_other_rules_from_being_created(self):
        # Start with 0 Rules
        dq = DataQualityCheck.retrieve(self.org.id)
        dq.remove_all_rules()

        # Post 3 rules - one of which will fail
        base_rule_post_data = {
            'field': 'address_line_1',
            'table_name': 'PropertyState',
            'enabled': True,
            'data_type': dict(Rule.DATA_TYPES).get(Rule.TYPE_STRING),
            'rule_type': Rule.RULE_TYPE_DEFAULT,
            'condition': Rule.RULE_INCLUDE,
            'required': False,
            'not_null': False,
            'min': None,
            'max': None,
            'text_match': 'Test Rule 1',
            'severity': dict(Rule.SEVERITY).get(Rule.SEVERITY_ERROR),
            'units': "",
            'label': None
        }

        rule_2_post_data = deepcopy(base_rule_post_data)
        rule_2_post_data['text_match'] = 'Test Rule 2'
        rule_2_post_data['rule_type'] = 'some invalid rule type'

        rule_3_post_data = deepcopy(base_rule_post_data)
        rule_3_post_data['text_match'] = 'Test Rule 3'
        rule_3_post_data['rule_type'] = Rule.RULE_TYPE_DEFAULT

        property_rules = [base_rule_post_data, rule_2_post_data, rule_3_post_data]

        url = reverse('api:v2:data_quality_checks-save-data-quality-rules') + '?organization_id=' + str(self.org.pk)
        post_data = {
            "data_quality_rules": {
                "properties": property_rules,
                "taxlots": [],
            },
        }
        res = self.client.post(url, content_type='application/json', data=json.dumps(post_data))

        self.assertEqual(res.status_code, 400)
        self.assertEqual(json.loads(res.content)['message'], "Rule could not be recreated: invalid literal for int() with base 10: 'some invalid rule type'")

        # Count 2 total rules - the first and second rules
        self.assertEqual(dq.rules.count(), 2)
        self.assertEqual(dq.rules.filter(text_match__in=['Test Rule 1', 'Test Rule 3']).count(), 2)

    def test_multiple_unique_errors_get_reported(self):
        # Start with 3 Rules
        dq = DataQualityCheck.retrieve(self.org.id)
        dq.remove_all_rules()
        base_rule_info = {
            'field': 'address_line_1',
            'table_name': 'PropertyState',
            'enabled': True,
            'data_type': Rule.TYPE_STRING,
            'rule_type': Rule.RULE_TYPE_DEFAULT,
            'condition': Rule.RULE_INCLUDE,
            'required': False,
            'not_null': False,
            'min': None,
            'max': None,
            'text_match': 'Test Rule 1',
            'severity': Rule.SEVERITY_ERROR,
            'units': "",
            'status_label_id': None
        }
        dq.add_rule(base_rule_info)

        rule_2_info = deepcopy(base_rule_info)
        rule_2_info['text_match'] = 'Test Rule 2'
        dq.add_rule(rule_2_info)

        rule_3_info = deepcopy(base_rule_info)
        rule_3_info['text_match'] = 'Test Rule 3'
        dq.add_rule(rule_3_info)

        self.assertEqual(dq.rules.count(), 3)

        property_rules = [base_rule_info, rule_2_info, rule_3_info]

        # Make some adjustments to mimic how data is expected in API endpoint
        rule_3_info['severity'] = dict(Rule.SEVERITY).get(Rule.SEVERITY_ERROR)
        for rule in property_rules:
            rule['data_type'] = dict(Rule.DATA_TYPES).get(rule['data_type'])
            rule['label'] = None

        # Make 1 rule trigger the include without text_match failure
        base_rule_info['text_match'] = ''

        # Make 1 rule trigger the "valid without label" failure
        rule_2_info['severity'] = dict(Rule.SEVERITY).get(Rule.SEVERITY_VALID)

        url = reverse('api:v2:data_quality_checks-save-data-quality-rules') + '?organization_id=' + str(self.org.pk)
        post_data = {
            "data_quality_rules": {
                "properties": property_rules,
                "taxlots": [],
            },
        }
        res = self.client.post(url, content_type='application/json', data=json.dumps(post_data))

        self.assertEqual(res.status_code, 400)
        self.assertTrue('Rule must not include or exclude an empty string.' in json.loads(res.content)['message'])
        self.assertTrue('Label must be assigned when using Valid Data Severity.' in json.loads(res.content)['message'])

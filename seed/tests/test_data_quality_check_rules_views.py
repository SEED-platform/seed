# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
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

from seed.utils.organizations import create_organization


class RuleViewTests(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)

        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.client.login(
            username='test_user@demo.com',
            password='test_pass',
            email='test_user@demo.com'
        )

    def test_get_rules(self):
        url = reverse('api:v3:data_quality_check-rules-list', kwargs={'nested_organization_id': self.org.id})
        response = self.client.get(url)
        rules = json.loads(response.content)

        self.assertEqual(len(rules), 22)

        property_count = 0
        taxlot_count = 0
        for r in rules:
            if r['table_name'] == 'PropertyState':
                property_count += 1
            elif r['table_name'] == 'TaxLotState':
                taxlot_count += 1

        self.assertEqual(taxlot_count, 2)
        self.assertEqual(property_count, 20)

    def test_reset_rules(self):
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

        url = reverse('api:v3:data_quality_check-rules-reset', kwargs={'nested_organization_id': self.org.id})
        response = self.client.put(url)
        rules = json.loads(response.content)

        self.assertEqual(len(rules), 22)

        property_count = 0
        taxlot_count = 0
        for r in rules:
            if r['table_name'] == 'PropertyState':
                property_count += 1
            elif r['table_name'] == 'TaxLotState':
                taxlot_count += 1

        self.assertEqual(taxlot_count, 2)
        self.assertEqual(property_count, 20)

    def test_create_rule_using_org_id_to_establish_dq_check_relationship(self):
        # Ensure no address_line_2 rules exist by default beforehand
        dq = DataQualityCheck.retrieve(self.org.id)
        self.assertEqual(0, dq.rules.filter(field='address_line_2').count())

        base_rule_info = {
            'field': 'address_line_2',
            'table_name': 'PropertyState',
            'enabled': True,
            'data_type': Rule.TYPE_STRING,
            'rule_type': Rule.RULE_TYPE_DEFAULT,
            'condition': Rule.RULE_INCLUDE,
            'required': False,
            'not_null': False,
            'min': None,
            'max': None,
            'text_match': 'some random text',
            'severity': Rule.SEVERITY_ERROR,
            'units': "",
            'status_label': None,
        }

        url = reverse('api:v3:data_quality_check-rules-list', kwargs={'nested_organization_id': self.org.id})
        self.client.post(url, content_type='application/json', data=json.dumps(base_rule_info))

        dq = DataQualityCheck.retrieve(self.org.id)
        self.assertEqual(1, dq.rules.filter(field='address_line_2').count())

    def test_create_rule_validations(self):
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
            'text_match': None,
            'severity': Rule.SEVERITY_VALID,
            'units': "",
            'status_label': None,
        }

        url = reverse('api:v3:data_quality_check-rules-list', kwargs={'nested_organization_id': self.org.id})
        res = self.client.post(url, content_type='application/json', data=json.dumps(base_rule_info))

        expected_message = 'Label must be assigned when using \'Valid\' Data Severity. Rule must not include or exclude an empty string. '
        self.assertTrue(expected_message in json.loads(res.content)['message'])

    def test_update_rule_status_label_validation(self):
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

        # Send invalid update request that includes a label id from another org
        new_org, _, _ = create_organization(self.user, "test-organization-a")
        wrong_org_label_id = new_org.labels.first().id
        put_data = deepcopy(base_rule_info)
        put_data['status_label'] = wrong_org_label_id
        url = reverse('api:v3:data_quality_check-rules-detail', kwargs={
            'nested_organization_id': self.org.id,
            'pk': rule.id
        })
        res = self.client.put(url, content_type='application/json', data=json.dumps(put_data))

        self.assertEqual(res.status_code, 400)
        self.assertTrue(f'Label with ID {wrong_org_label_id} not found in organization, {self.org.id}.' in json.loads(res.content)['status_label'])

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
        put_data['severity'] = Rule.SEVERITY_VALID
        put_data['status_label'] = None
        url = reverse('api:v3:data_quality_check-rules-detail', kwargs={
            'nested_organization_id': self.org.id,
            'pk': rule.id
        })
        res = self.client.put(url, content_type='application/json', data=json.dumps(put_data))

        self.assertEqual(res.status_code, 400)
        self.assertTrue('Label must be assigned when using \'Valid\' Data Severity. ' in json.loads(res.content)['message'])

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
        self.assertTrue('Label must be assigned when using \'Valid\' Data Severity. ' in json.loads(res.content)['message'])

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
        self.assertTrue('Rule must not include or exclude an empty string. ' in json.loads(res.content)['message'])

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
        self.assertTrue('Rule must not include or exclude an empty string. ' in json.loads(res.content)['message'])

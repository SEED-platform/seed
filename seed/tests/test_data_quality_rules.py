# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from copy import deepcopy

from django.core.urlresolvers import reverse

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

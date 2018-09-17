# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.forms.models import model_to_dict

from seed.models.data_quality import (
    DataQualityCheck,
    Rule,
    DataQualityTypeCastError,
)
from seed.models.models import ASSESSED_RAW
from seed.test_helpers.fake import (
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import DataMappingBaseTestCase


class DataQualityCheckTests(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)

        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_default_create(self):
        dq = DataQualityCheck.retrieve(self.org.id)
        self.assertEqual(dq.rules.count(), 22)
        # Example rule to check
        ex_rule = {
            'table_name': 'PropertyState',
            'field': 'conditioned_floor_area',
            'data_type': Rule.TYPE_AREA,
            'rule_type': Rule.RULE_TYPE_DEFAULT,
            'min': 0,
            'max': 7000000,
            'severity': Rule.SEVERITY_ERROR,
            'units': 'ft**2',
        }

        rule = Rule.objects.filter(
            table_name='PropertyState', field='conditioned_floor_area', severity=Rule.SEVERITY_ERROR
        )
        self.assertDictContainsSubset(ex_rule, model_to_dict(rule.first()))

    def test_remove_rules(self):
        dq = DataQualityCheck.retrieve(self.org.id)
        self.assertEqual(dq.rules.count(), 22)
        dq.remove_all_rules()
        self.assertEqual(dq.rules.count(), 0)

    def test_add_custom_rule(self):
        dq = DataQualityCheck.retrieve(self.org.id)
        dq.remove_all_rules()

        ex_rule = {
            'table_name': 'PropertyState',
            'field': 'some_floor_area',
            'data_type': Rule.TYPE_AREA,
            'rule_type': Rule.RULE_TYPE_DEFAULT,
            'min': 8760,
            'max': 525600,
            'severity': Rule.SEVERITY_ERROR,
            'units': 'm**2',
        }

        dq.add_rule(ex_rule)
        self.assertEqual(dq.rules.count(), 1)
        self.assertDictContainsSubset(ex_rule, model_to_dict(dq.rules.first()))

    def test_add_custom_rule_exception(self):
        dq = DataQualityCheck.retrieve(self.org.id)
        dq.remove_all_rules()

        ex_rule = {
            'table_name_does_not_exist': 'PropertyState',
        }

        with self.assertRaises(Exception) as exc:
            dq.add_rule(ex_rule)
        self.assertEqual(str(exc.exception),
                         "Rule data is not defined correctly: 'table_name_does_not_exist' is an invalid keyword argument for this function")

    def test_check_property_state_example_data(self):
        dq = DataQualityCheck.retrieve(self.org.id)
        ps_data = {
            'no_default_data': True,
            'custom_id_1': 'abcd',
            'address_line_1': '742 Evergreen Terrace',
            'pm_property_id': 'PMID',
            'site_eui': 525600,
        }
        ps = self.property_state_factory.get_property_state(None, **ps_data)

        dq.check_data(ps.__class__.__name__, [ps])

        # {
        #   11: {
        #           'id': 11,
        #           'custom_id_1': 'abcd',
        #           'pm_property_id': 'PMID',
        #           'address_line_1': '742 Evergreen Terrace',
        #           'data_quality_results': [
        #               {
        #                  'severity': u'error', 'value': '525600', 'field': u'site_eui', 'table_name': u'PropertyState', 'message': u'Site EUI out of range', 'detailed_message': u'Site EUI [525600] > 1000', 'formatted_field': u'Site EUI'
        #               }
        #           ]
        #       }
        error_found = False
        for index, row in dq.results.items():
            self.assertEqual(row['custom_id_1'], 'abcd')
            self.assertEqual(row['pm_property_id'], 'PMID')
            self.assertEqual(row['address_line_1'], '742 Evergreen Terrace')
            for violation in row['data_quality_results']:
                if violation['message'] == u'Site EUI out of range':
                    error_found = True
                    self.assertEqual(violation['detailed_message'], u'Site EUI [525600] > 1000')

        self.assertEqual(error_found, True)

    def test_text_match(self):
        dq = DataQualityCheck.retrieve(self.org.id)
        dq.remove_all_rules()
        new_rule = {
            'table_name': 'PropertyState',
            'field': 'address_line_1',
            'data_type': Rule.TYPE_STRING,
            'rule_type': Rule.RULE_TYPE_DEFAULT,
            'severity': Rule.SEVERITY_ERROR,
            'not_null': True,
            'text_match': 742,
        }
        dq.add_rule(new_rule)
        ps_data = {
            'no_default_data': True,
            'custom_id_1': 'abcd',
            'address_line_1': '742 Evergreen Terrace',
            'pm_property_id': 'PMID',
            'site_eui': 525600,
        }
        ps = self.property_state_factory.get_property_state(None, **ps_data)
        dq.check_data(ps.__class__.__name__, [ps])
        self.assertEqual(dq.results, {})

    def test_str_to_data_type_string(self):
        rule = Rule.objects.create(name='str_rule', data_type=Rule.TYPE_STRING)
        self.assertEqual(rule.str_to_data_type(' '), '')
        self.assertEqual(rule.str_to_data_type(None), None)
        self.assertEqual(rule.str_to_data_type(27.5), 27.5)

    def test_str_to_data_type_float(self):
        rule = Rule.objects.create(name='flt_rule', data_type=Rule.TYPE_NUMBER)
        self.assertEqual(rule.str_to_data_type('   '), None)
        self.assertEqual(rule.str_to_data_type(None), None)
        self.assertEqual(rule.str_to_data_type(27.5), 27.5)
        with self.assertRaises(DataQualityTypeCastError):
            self.assertEqual(rule.str_to_data_type('not-a-number'), '')

    def test_str_to_data_type_date(self):
        rule = Rule.objects.create(name='date_rule', data_type=Rule.TYPE_DATE)
        d = rule.str_to_data_type('07/04/2000 08:55:30')
        self.assertEqual(d.strftime("%Y-%m-%d %H  %M  %S"), '2000-07-04 08  55  30')
        self.assertEqual(rule.str_to_data_type(None), None)
        self.assertEqual(rule.str_to_data_type(27.5), 27.5)  # floats should return float

    def test_str_to_data_type_datetime(self):
        rule = Rule.objects.create(name='year_rule', data_type=Rule.TYPE_YEAR)
        d = rule.str_to_data_type('07/04/2000')
        self.assertEqual(d.strftime("%Y-%m-%d"), '2000-07-04')
        self.assertEqual(rule.str_to_data_type(None), None)
        self.assertEqual(rule.str_to_data_type(27.5), 27.5)  # floats should return float

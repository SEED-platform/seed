# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from seed.models.derived_columns import DerivedColumn
from django.forms.models import model_to_dict
from quantityfield.units import ureg

from seed.models import Column, DerivedColumnParameter, PropertyView
from seed.models.data_quality import (
    DataQualityCheck,
    Rule,
    StatusLabel,
    DataQualityTypeCastError,
    UnitMismatchError,
)
from seed.models.models import ASSESSED_RAW
from seed.test_helpers.fake import (
    FakeDerivedColumnFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
)
from seed.tests.util import DataMappingBaseTestCase, AssertDictSubsetMixin


class DataQualityCheckTests(AssertDictSubsetMixin, DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)

        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)
        self.derived_column_factory = FakeDerivedColumnFactory(organization=self.org, inventory_type=DerivedColumn.PROPERTY_TYPE)

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
        self.assertEqual(
            str(exc.exception),
            "Rule data is not defined correctly: Rule() got an unexpected keyword argument 'table_name_does_not_exist'"
        )

    def test_check_property_state_example_data(self):
        """Trigger 5 rules - 2 default and 3 custom rules - one of each condition type"""
        ps_data = {
            'no_default_data': True,
            'custom_id_1': 'abcd',
            'pm_property_id': 'PMID',
            'site_eui': 525600,
        }
        ps = self.property_state_factory.get_property_state(None, **ps_data)

        # Add 3 additionals rule to default set
        dq = DataQualityCheck.retrieve(self.org.id)
        rule_info = {
            'field': 'custom_id_1',
            'table_name': 'PropertyState',
            'enabled': True,
            'data_type': Rule.TYPE_STRING,
            'rule_type': Rule.RULE_TYPE_DEFAULT,
            'condition': Rule.RULE_INCLUDE,
            'required': False,
            'not_null': False,
            'min': None,
            'max': None,
            'text_match': 'zzzzzzzzz',
            'severity': Rule.SEVERITY_ERROR,
            'units': "",
        }
        dq.add_rule(rule_info)

        rule_info['field'] = 'pm_property_id'
        rule_info['condition'] = Rule.RULE_EXCLUDE
        rule_info['text_match'] = 'PMID'
        dq.add_rule(rule_info)

        rule_info['field'] = 'address_line_2'
        rule_info['condition'] = Rule.RULE_REQUIRED
        dq.add_rule(rule_info)

        # Run DQ check and test that each rule was triggered
        dq.check_data(ps.__class__.__name__, [ps])

        # {
        #   11: {
        #           'id': 11,
        #           'custom_id_1': 'abcd',
        #           'pm_property_id': 'PMID',
        #           'data_quality_results': [
        #               {
        #                  'severity': 'error', 'value': '525600', 'field': 'site_eui', 'table_name': 'PropertyState', 'message': 'Site EUI out of range', 'detailed_message': 'Site EUI [525600] > 1000', 'formatted_field': 'Site EUI'
        #                  ...
        #               }
        #           ]
        #       }
        record_results = dq.results[ps.id]
        self.assertEqual(record_results['custom_id_1'], 'abcd')
        self.assertEqual(record_results['pm_property_id'], 'PMID')

        violation_fields = []
        for violation in record_results['data_quality_results']:
            field = violation['field']

            if field == 'address_line_1':
                self.assertEqual(violation['detailed_message'], 'Address Line 1 is null')
            elif field == 'address_line_2':
                self.assertEqual(violation['detailed_message'], 'Address Line 2 is required but is None')
            elif field == 'custom_id_1':
                self.assertEqual(violation['detailed_message'], 'Custom ID 1 [abcd] does not contain "zzzzzzzzz"')
            elif field == 'pm_property_id':
                self.assertEqual(violation['detailed_message'], 'PM Property ID [PMID] contains "PMID"')
            elif field == 'site_eui':
                self.assertEqual(violation['detailed_message'], 'Site EUI [525600] > 1000')
            else:  # we should have hit one of the cases above
                self.fail('invalid "field" provided')

            violation_fields.append(field)

        expected_fields = [
            'address_line_1',
            'address_line_2',
            'custom_id_1',
            'pm_property_id',
            'site_eui',
        ]
        self.assertCountEqual(expected_fields, violation_fields)

    def test_check_example_with_extra_data_fields(self):
        """Trigger 5 ED rules - 2 default and 3 custom rules - one of each condition type"""
        ps_data = {
            'no_default_data': True,
            'custom_id_1': 'abcd',
            'extra_data': {
                'range_and_out_of_range': 1,
                'include_and_doesnt': 'aaaaa',
                'exclude_and_does': 'foo',
            }
        }
        ps = self.property_state_factory.get_property_state(None, **ps_data)

        # Create 5 column objects that correspond to the 3 ED rules since rules don't get
        # checked for anything other than REQUIRED if they don't have a corresponding col object
        column_names = [
            'required_and_missing',
            'not_null_and_missing',
            'range_and_out_of_range',
            'include_and_doesnt',
            'exclude_and_does'
        ]
        for col_name in column_names:
            Column.objects.create(
                column_name=col_name,
                table_name='PropertyState',
                organization=self.org,
                is_extra_data=True,
            )

        dq = DataQualityCheck.retrieve(self.org.id)
        dq.remove_all_rules()
        rule_info = {
            'field': 'required_and_missing',
            'table_name': 'PropertyState',
            'enabled': True,
            'data_type': Rule.TYPE_STRING,
            'rule_type': Rule.RULE_TYPE_DEFAULT,
            'condition': Rule.RULE_REQUIRED,
            'required': False,
            'not_null': False,
            'min': None,
            'max': None,
            'text_match': None,
            'severity': Rule.SEVERITY_ERROR,
            'units': "",
        }
        dq.add_rule(rule_info)

        rule_info['field'] = 'not_null_and_missing'
        rule_info['condition'] = Rule.RULE_NOT_NULL
        dq.add_rule(rule_info)

        rule_info['field'] = 'range_and_out_of_range'
        rule_info['condition'] = Rule.RULE_RANGE
        rule_info['min'] = 100
        dq.add_rule(rule_info)

        rule_info['field'] = 'include_and_doesnt'
        rule_info['condition'] = Rule.RULE_INCLUDE
        rule_info['text_match'] = 'zzzzzzzzz'
        dq.add_rule(rule_info)

        rule_info['field'] = 'exclude_and_does'
        rule_info['condition'] = Rule.RULE_EXCLUDE
        rule_info['text_match'] = 'foo'
        dq.add_rule(rule_info)

        # Run DQ check and test that each rule was triggered
        dq.check_data(ps.__class__.__name__, [ps])
        record_results = dq.results[ps.id]

        violation_fields = []
        for violation in record_results['data_quality_results']:
            field = violation['field']

            if field == 'required_and_missing':
                self.assertEqual(violation['detailed_message'], 'required_and_missing is required but is None')
            elif field == 'not_null_and_missing':
                self.assertEqual(violation['detailed_message'], 'not_null_and_missing is null')
            elif field == 'range_and_out_of_range':
                self.assertEqual(violation['detailed_message'], 'range_and_out_of_range [1] < 100')
            elif field == 'include_and_doesnt':
                self.assertEqual(violation['detailed_message'], 'include_and_doesnt [aaaaa] does not contain "zzzzzzzzz"')
            elif field == 'exclude_and_does':
                self.assertEqual(violation['detailed_message'], 'exclude_and_does [foo] contains "foo"')
            else:  # we should have hit one of the cases above
                self.fail('invalid "field" provided')

            violation_fields.append(field)

        self.assertCountEqual(column_names, violation_fields)

    def test_check_property_state_example_data_with_labels(self):
        dq = DataQualityCheck.retrieve(self.org.id)

        # Create labels and apply them to the rules being triggered later
        site_eui_label = StatusLabel.objects.create(name='Check Site EUI', super_organization=self.org)
        site_eui_rule = dq.rules.get(table_name='PropertyState', field='site_eui', max='1000')
        site_eui_rule.status_label = site_eui_label
        site_eui_rule.save()

        year_built_label = StatusLabel.objects.create(name='Check Year Built', super_organization=self.org)
        year_built_rule = dq.rules.get(table_name='PropertyState', field='year_built')
        year_built_rule.status_label = year_built_label
        year_built_rule.save()

        # Create state and associate it to view
        ps_data = {
            'no_default_data': True,
            'custom_id_1': 'abcd',
            'address_line_1': '742 Evergreen Terrace',
            'pm_property_id': 'PMID',
            'site_eui': 525600,
            'year_built': 1699,
        }
        ps = self.property_state_factory.get_property_state(None, **ps_data)
        property = self.property_factory.get_property()
        PropertyView.objects.create(
            property=property, cycle=self.cycle, state=ps
        )

        dq.check_data(ps.__class__.__name__, [ps])

        dq_results = dq.results[ps.id]['data_quality_results']
        labels = [r['label'] for r in dq_results]
        self.assertCountEqual(['Check Site EUI', 'Check Year Built'], labels)

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

    def test_min_value(self):
        rule = Rule.objects.create(name='min_str_rule', data_type=Rule.TYPE_NUMBER, min=0.5)
        self.assertTrue(rule.minimum_valid(1000))
        self.assertTrue(rule.minimum_valid('1000'))
        self.assertFalse(rule.minimum_valid(0.1))
        self.assertFalse(rule.minimum_valid('0.1'))
        with self.assertRaises(DataQualityTypeCastError):
            self.assertEqual(rule.minimum_valid('not-a-number'), '')

    def test_max_value(self):
        rule = Rule.objects.create(name='max_str_rule', data_type=Rule.TYPE_NUMBER, max=1000)
        self.assertTrue(rule.maximum_valid(0.1))
        self.assertTrue(rule.maximum_valid('0.1'))
        self.assertFalse(rule.maximum_valid(9999))
        self.assertFalse(rule.maximum_valid('9999'))
        with self.assertRaises(DataQualityTypeCastError):
            self.assertEqual(rule.maximum_valid('not-a-number'), '')

    def test_min_value_quantities(self):
        rule = Rule.objects.create(name='min_str_rule', data_type=Rule.TYPE_EUI, min=10, max=100, units='kBtu/ft**2/year')
        self.assertTrue(rule.minimum_valid(15))
        self.assertTrue(rule.minimum_valid('15'))
        self.assertTrue(rule.maximum_valid(15))
        self.assertTrue(rule.maximum_valid('15'))
        self.assertFalse(rule.minimum_valid(5))
        self.assertFalse(rule.minimum_valid('5'))
        self.assertFalse(rule.maximum_valid(150))
        self.assertFalse(rule.maximum_valid('150'))

        # All of these should value since they are less than 10 (e.g. 5 kbtu/m2/year =~ 0.5 kbtu/ft2/year)
        # different units on check data
        self.assertFalse(rule.minimum_valid(ureg.Quantity(5, "kBtu/ft**2/year")))
        self.assertFalse(rule.minimum_valid(ureg.Quantity(5, "kBtu/m**2/year")))  # ~ 0.5 kbtu/ft2/year
        self.assertFalse(rule.maximum_valid(ureg.Quantity(110, "kBtu/ft**2/year")))
        self.assertFalse(rule.maximum_valid(ureg.Quantity(1100, "kBtu/m**2/year")))  # ~ 102.2 kbtu/ft2/year

        # these should all pass
        self.assertTrue(rule.minimum_valid(ureg.Quantity(10, "kBtu/ft**2/year")))
        self.assertTrue(rule.minimum_valid(ureg.Quantity(110, "kBtu/m**2/year")))  # 10.22 kbtu/ft2/year

        # test the rule with different units
        rule = Rule.objects.create(name='min_str_rule', data_type=Rule.TYPE_EUI, min=10, max=100, units='kBtu/m**2/year')
        self.assertFalse(rule.minimum_valid(ureg.Quantity(0.05, "kBtu/ft**2/year")))  # ~ 0.538 kbtu/m2/year
        self.assertFalse(rule.maximum_valid(ureg.Quantity(15, "kBtu/ft**2/year")))  # ~ 161 kbtu/m2/year
        self.assertFalse(rule.minimum_valid(ureg.Quantity(5, "kBtu/m**2/year")))
        self.assertFalse(rule.maximum_valid(ureg.Quantity(110, "kBtu/m**2/year")))

    def test_incorrect_pint_unit_conversions(self):
        rule = Rule.objects.create(name='min_str_rule', data_type=Rule.TYPE_EUI, min=10, max=100, units='ft**2')
        # this should error out nicely
        with self.assertRaises(UnitMismatchError):
            self.assertFalse(rule.minimum_valid(ureg.Quantity(5, "kBtu/ft**2/year")))

        with self.assertRaises(UnitMismatchError):
            self.assertFalse(rule.maximum_valid(ureg.Quantity(5, "kBtu/ft**2/year")))

    def test_works_with_derived_columns(self):
        # -- Setup
        # create a derived column and properties that have the necessary data
        derived_column_name = 'my_derived_column'
        derived_column = self.derived_column_factory.get_derived_column(
            expression='$gross_floor_area + 1',
            name=derived_column_name
        )
        DerivedColumnParameter.objects.create(
            parameter_name='gross_floor_area',
            derived_column=derived_column,
            source_column=Column.objects.get(column_name='gross_floor_area', table_name='PropertyState')
        )
        # good b/c 0 + 1 will be in our DQ range
        ps_good = self.property_state_factory.get_property_state(gross_floor_area=0)
        # bad b/c 100 + 1 will be out of our DQ range
        ps_bad = self.property_state_factory.get_property_state(gross_floor_area=100)

        # create a rule to check the derived column
        dq = DataQualityCheck.retrieve(self.org.id)
        dq.remove_all_rules()

        ex_rule = {
            'table_name': 'PropertyState',
            'field': derived_column_name,
            'for_derived_column': True,
            'data_type': Rule.TYPE_NUMBER,
            'rule_type': Rule.RULE_TYPE_CUSTOM,
            'condition': Rule.RULE_RANGE,
            'min': 0,
            'max': 10,
            'severity': Rule.SEVERITY_ERROR,
            'units': '',
        }

        dq.add_rule(ex_rule)

        # -- Act
        dq.check_data(ps_good.__class__.__name__, [ps_good, ps_bad])

        # -- Assert
        good_results = dq.results.get(ps_good.id, {}).get('data_quality_results', None)
        self.assertIsNone(good_results)

        bad_results = dq.results[ps_bad.id]['data_quality_results']
        self.assertDictContainsSubset(
            {'field': derived_column_name, 'message': f'{derived_column_name} out of range'},
            bad_results[0]
        )

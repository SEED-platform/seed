# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
import logging
import re
from datetime import date, datetime

import pytz
from django.apps import apps
from django.db import models
from django.utils.timezone import get_current_timezone, make_aware, make_naive

from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    Column,
    StatusLabel,
    PropertyView, TaxLotView)
from seed.models import obj_to_dict
from seed.utils.cache import (
    set_cache_raw, get_cache_raw
)
from seed.utils.time import convert_datestr

_log = logging.getLogger(__name__)

RULE_TYPE_DEFAULT = 0
RULE_TYPE_CUSTOM = 1
RULE_TYPE = [
    (RULE_TYPE_DEFAULT, 'default'),
    (RULE_TYPE_CUSTOM, 'custom'),
]

TYPE_NUMBER = 0
TYPE_STRING = 1
TYPE_DATE = 2
TYPE_YEAR = 3
DATA_TYPES = [
    (TYPE_NUMBER, 'number'),
    (TYPE_STRING, 'string'),
    (TYPE_DATE, 'date'),
    (TYPE_YEAR, 'year')
]

SEVERITY_ERROR = 0
SEVERITY_WARNING = 1
SEVERITY = [
    (SEVERITY_ERROR, 'error'),
    (SEVERITY_WARNING, 'warning')
]

DEFAULT_RULES = [
    {
        'table_name': 'PropertyState',
        'field': 'address_line_1',
        'data_type': TYPE_STRING,
        'not_null': True,
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
    }, {
        'table_name': 'PropertyState',
        'field': 'pm_property_id',
        'data_type': TYPE_STRING,
        'not_null': True,
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
    }, {
        'table_name': 'PropertyState',
        'field': 'custom_id_1',
        'not_null': True,
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
    }, {
        'table_name': 'TaxLotState',
        'field': 'jurisdiction_tax_lot_id',
        'not_null': True,
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
    }, {
        'table_name': 'TaxLotState',
        'field': 'address_line_1',
        'not_null': True,
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
    }, {
        'table_name': 'PropertyState',
        'field': 'conditioned_floor_area',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 0,
        'max': 7000000,
        'severity': SEVERITY_ERROR,
        'units': 'square feet',
    }, {
        'table_name': 'PropertyState',
        'field': 'conditioned_floor_area',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 100,
        'severity': SEVERITY_WARNING,
        'units': 'square feet',
    }, {
        'table_name': 'PropertyState',
        'field': 'energy_score',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 0,
        'max': 100,
        'severity': SEVERITY_ERROR,
    }, {
        'table_name': 'PropertyState',
        'field': 'energy_score',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 10,
        'severity': SEVERITY_WARNING,
    }, {
        'table_name': 'PropertyState',
        'field': 'generation_date',
        'data_type': TYPE_DATE,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 18890101,
        'max': 20201231,
        'severity': SEVERITY_ERROR,
    }, {
        'table_name': 'PropertyState',
        'field': 'gross_floor_area',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 100,
        'max': 7000000,
        'severity': SEVERITY_ERROR,
        'units': 'square feet',
    }, {
        'table_name': 'PropertyState',
        'field': 'occupied_floor_area',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 100,
        'max': 7000000,
        'severity': SEVERITY_ERROR,
        'units': 'square feet',
    }, {
        'table_name': 'PropertyState',
        'field': 'recent_sale_date',
        'data_type': TYPE_DATE,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 18890101,
        'max': 20201231,
        'severity': SEVERITY_ERROR,
    }, {
        'table_name': 'PropertyState',
        'field': 'release_date',
        'data_type': TYPE_DATE,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 18890101,
        'max': 20201231,
        'severity': SEVERITY_ERROR,
    }, {
        'table_name': 'PropertyState',
        'field': 'site_eui',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 0,
        'max': 1000,
        'severity': SEVERITY_ERROR,
        'units': 'kBtu/sq. ft./year',
    }, {
        'table_name': 'PropertyState',
        'field': 'site_eui',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 10,
        'severity': SEVERITY_WARNING,
        'units': 'kBtu/sq. ft./year',
    }, {
        'table_name': 'PropertyState',
        'field': 'site_eui_weather_normalized',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 0,
        'max': 1000,
        'severity': SEVERITY_ERROR,
        'units': 'kBtu/sq. ft./year',
    }, {
        'table_name': 'PropertyState',
        'field': 'source_eui',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 0,
        'max': 1000,
        'severity': SEVERITY_ERROR,
        'units': 'kBtu/sq. ft./year',
    }, {
        'table_name': 'PropertyState',
        'field': 'source_eui',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 10,
        'severity': SEVERITY_WARNING,
        'units': 'kBtu/sq. ft./year',
    }, {
        'table_name': 'PropertyState',
        'field': 'source_eui_weather_normalized',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 10,
        'max': 1000,
        'severity': SEVERITY_ERROR,
        'units': 'kBtu/sq. ft./year',
    }, {
        'table_name': 'PropertyState',
        'field': 'year_built',
        'data_type': TYPE_YEAR,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 1700,
        'max': 2019,
        'severity': SEVERITY_ERROR,
    }, {
        'table_name': 'PropertyState',
        'field': 'year_ending',
        'data_type': TYPE_DATE,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 18890101,
        'max': 20201231,
        'severity': SEVERITY_ERROR,
    }
]


class ComparisonError(Exception):
    pass


class Rule(models.Model):
    """
    Rules for DataQualityCheck
    """
    name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=1000, blank=True)
    data_quality_check = models.ForeignKey('DataQualityCheck', related_name='rules',
                                           on_delete=models.CASCADE, null=True)
    status_label = models.ForeignKey(StatusLabel, null=True, on_delete=models.DO_NOTHING)
    table_name = models.CharField(max_length=200, default='PropertyState', blank=True)
    field = models.CharField(max_length=200)
    enabled = models.BooleanField(default=True)
    data_type = models.IntegerField(choices=DATA_TYPES, null=True)
    rule_type = models.IntegerField(choices=RULE_TYPE, null=True)
    required = models.BooleanField(default=False)
    not_null = models.BooleanField(default=False)
    min = models.FloatField(null=True)
    max = models.FloatField(null=True)
    text_match = models.CharField(max_length=200, null=True)
    severity = models.IntegerField(choices=SEVERITY, default=SEVERITY_ERROR)
    units = models.CharField(max_length=100, blank=True)

    def __unicode__(self):
        return json.dumps(obj_to_dict(self))

    def valid_text(self, value):
        """
        Validate the rule matches the specified text. Text is matched by regex.

        :param value: Value to validate rule against
        :return: bool, True is valid, False if the value does not match
        """

        if self.data_type == TYPE_STRING and isinstance(value, (str, unicode)):
            if self.text_match is None or self.text_match == '':
                return True

            if not re.search(self.text_match, value, re.IGNORECASE):
                return False

        return True

    def minimum_valid(self, value):
        """
        Validate that the value is not less than the minimum specified by the rule.

        :param value: Value to validate rule against
        :return: bool, True is valid, False if the value is out of range
        """
        # Convert the rule into the correct types for checking the data
        rule_min = self.min
        if rule_min is None:
            return True
        else:
            if isinstance(value, datetime):
                value = value.astimezone(get_current_timezone()).replace(tzinfo=pytz.UTC)
                rule_min = make_aware(datetime.strptime(str(int(rule_min)), '%Y%m%d'), pytz.UTC)
            elif isinstance(value, date):
                value = value
                rule_min = datetime.strptime(str(int(rule_min)), '%Y%m%d').date()
            elif isinstance(value, int):
                rule_min = int(rule_min)
            elif not isinstance(value, (str, unicode)):
                # must be a float...
                value = float(value)

            try:
                if value < rule_min:
                    return False
                else:
                    # If rule_min is undefined/None or value is okay, then it is valid.
                    return True
            except ValueError:
                raise ComparisonError("Value could not be compared numerically")

    def maximum_valid(self, value):
        """
        Validate that the value is not greater than the maximum specified by the rule.

        :param value: Value to validate rule against
        :return: bool, True is valid, False if the value is out of range
        """
        # Convert the rule into the correct types for checking the data
        rule_max = self.max
        if rule_max is None:
            return True
        else:
            if isinstance(value, datetime):
                value = value.astimezone(get_current_timezone()).replace(tzinfo=pytz.UTC)
                rule_max = make_aware(datetime.strptime(str(int(rule_max)), '%Y%m%d'), pytz.UTC)
            elif isinstance(value, date):
                value = value
                rule_max = datetime.strptime(str(int(rule_max)), '%Y%m%d').date()
            elif isinstance(value, int):
                rule_max = int(rule_max)
            elif not isinstance(value, (str, unicode)):
                # must be a float...
                value = float(value)

            try:
                if value > rule_max:
                    return False
                else:
                    return True
            except ValueError:
                raise ComparisonError("Value could not be compared numerically")

    def str_to_data_type(self, value):
        """
        If the check is coming from a field in the database then it will be typed correctly;
        however, for extra_data, the values are typically strings or unicode. Therefore, the
        values are typed before they are checked using the rule's data type definition.

        :param value: variant, value to type
        :return: typed value
        """

        if isinstance(value, (str, unicode)):
            # check if we can type cast the value
            try:
                # since we already checked for data type, does this mean it isn't None, ever?
                if value is not None:
                    if self.data_type == TYPE_NUMBER:
                        if value == '':
                            return None
                        else:
                            return float(value)
                    elif self.data_type == TYPE_STRING:
                        return str(value)
                    elif self.data_type == TYPE_DATE:
                        if value == '':
                            return None
                        else:
                            return convert_datestr(value, True)
                    elif self.data_type == TYPE_YEAR:
                        if value == '':
                            return None
                        else:
                            dt = convert_datestr(value, True)
                            if dt is not None:
                                return dt.date()
            except ValueError as e:
                raise TypeError("Error converting {} with {}".format(value, e))
        else:
            return value

    def format_strings(self, value):
        f_min = self.min
        f_max = self.max
        f_value = value

        # Get the formatted values for reporting
        if isinstance(value, datetime):
            f_value = str(make_naive(value, pytz.UTC))
            if f_min is not None:
                f_min = str(datetime.strptime(str(int(self.min)), '%Y%m%d'))
            if f_max is not None:
                f_max = str(datetime.strptime(str(int(self.max)), '%Y%m%d'))
        elif isinstance(value, date):
            f_value = str(value)
            if f_min is not None:
                f_min = str(datetime.strptime(str(int(self.min)), '%Y%m%d').date())
            if f_max is not None:
                f_max = str(datetime.strptime(str(int(self.max)), '%Y%m%d').date())
        elif isinstance(value, int):
            f_value = str(value)
            if self.min is not None:
                f_min = str(int(self.min))
            if self.max is not None:
                f_max = str(int(self.max))
        elif isinstance(value, float):
            f_value = str(float(value))
            if self.min is not None:
                f_min = str(self.min)
            if self.max is not None:
                f_max = str(self.max)
        elif isinstance(value, (str, unicode)):
            f_value = str(value)
            f_min = str(self.min)
            f_max = str(self.max)
        else:
            raise Exception("Unknown data type ({}:{})".format(value, value.__class__))

        return [f_min, f_max, f_value]


class DataQualityCheck(models.Model):
    """
    Object that stores the high level configuration per organization of the DataQualityCheck
    """
    REQUIRED_FIELDS = {
        'PropertyState': ['address_line_1', 'custom_id_1', 'pm_property_id'],
        'TaxLotState': ['address_line_1', 'custom_id_1', 'jurisdiction_tax_lot_id'],
    }

    organization = models.ForeignKey(Organization)
    name = models.CharField(max_length=255, default='Default Data Quality Check')

    @classmethod
    def retrieve(cls, organization):
        """
        DataQualityCheck was previously a simple object but has been migrated to a django model.
        This method ensures that the data quality model will be backwards compatible.

        This is the preferred method to initialize a new object.

        :param organization: int or instance of Organization
        :return: obj, DataQualityCheck
        """

        if DataQualityCheck.objects.filter(organization=organization).count() > 1:
            # Ensure that only one object is returned. For an unknown reason, the production
            # database has multiple DataQualityCheck objects for an organizaiton, but there are no
            # calls to create a DataQualityCheck other than the .retrieve method.
            first = DataQualityCheck.objects.filter(organization=organization).first()
            dqcs = DataQualityCheck.objects.filter(organization=organization).exclude(
                id__in=[first.pk])
            for dqc in dqcs:
                _log.info(
                    "More than one DataQualityCheck for organization. Deleting {}".format(dqc.name))
                dqc.delete()

        dq, _ = DataQualityCheck.objects.get_or_create(organization=organization)

        if dq.rules.count() == 0:
            _log.debug("No rules found in DataQualityCheck, initializing default rules")
            dq.initialize_rules()

        return dq

    def __init__(self, *args, **kwargs):
        # Add member variable for temp storage of results
        self.results = {}
        self.reset_results()

        # tuple based column lookup for the display name, initialize to blank here,
        # set in check_data
        self.column_lookup = {}

        super(DataQualityCheck, self).__init__(*args, **kwargs)

    @staticmethod
    def initialize_cache(identifier):
        """
        Initialize the cache for storing the results. This is called before the
        celery tasks are chunked up.

        :param identifier: Import file primary key
        :return: string, cache key
        """

        k = DataQualityCheck.cache_key(identifier)
        set_cache_raw(k, [])
        return k

    @staticmethod
    def cache_key(identifier):
        """
        Static method to return the location of the data_quality results from redis.

        :param identifier: Import file primary key
        :return:
        """
        return "data_quality_results__%s" % identifier

    def check_data(self, record_type, rows):
        """
        Send in data as a queryset from the Property/Taxlot ids.

        :param record_type: one of PropertyState | TaxLotState
        :param rows: rows of data to be checked for data quality
        :return: None
        """

        # grab the columns so we can grab the display names
        columns = Column.retrieve_all(self.organization, record_type)

        # create lookup tuple for the display name
        for c in columns:
            self.column_lookup[(c['table'], c['name'])] = c['displayName']

        # grab all the rules once, save query time
        rules = list(
            self.rules.filter(enabled=True, table_name=record_type).order_by('field', 'severity'))

        # Get the list of the field names that will show in every result
        fields = self.get_fieldnames(record_type)
        for row in rows:
            # Initialize the ID if it does not exist yet. Add in the other
            # fields that are of interest to the GUI
            if row.id not in self.results:
                self.results[row.id] = {}
                for field in fields:
                    self.results[row.id][field] = getattr(row, field)
                self.results[row.id]['data_quality_results'] = []

            # Run the checks
            self._check(rules, row)

        # Prune the results will remove any entries that have zero data_quality_results
        for k, v in self.results.items():
            if not v['data_quality_results']:
                del self.results[k]

    def get_fieldnames(self, record_type):
        """Get fieldnames to apply to results."""
        field_names = ['id']
        field_names.extend(DataQualityCheck.REQUIRED_FIELDS[record_type])
        return field_names

    def reset_results(self):
        self.results = {}

    def _check(self, rules, row):
        """
        Check for errors in the min/max of the values.

        :param rules: list, rules to run from database objects
        :param row: dict, row of data to check
        :return: None
        """
        linked_id = None
        for rule in rules:
            # check if the field exists
            if hasattr(row, rule.field) or rule.field in row.extra_data:
                value = None
                label_applied = False

                if hasattr(row, rule.field):
                    value = getattr(row, rule.field)
                elif rule.field in row.extra_data:
                    value = row.extra_data[rule.field]
                    value = rule.str_to_data_type(value)

                display_name = rule.field
                if (rule.table_name, rule.field) in self.column_lookup:
                    display_name = self.column_lookup[(rule.table_name, rule.field)]

                # get the status_labels for the linked properties and tax lots
                if rule.table_name == 'PropertyState':
                    label = apps.get_model('seed', 'Property_labels')
                    if rule.status_label_id is not None and linked_id is None:
                        if PropertyView.objects.filter(state=row).exists():
                            linked_id = PropertyView.objects.get(state=row).property_id
                else:
                    label = apps.get_model('seed', 'TaxLot_labels')
                    if rule.status_label_id is not None and linked_id is None:
                        if TaxLotView.objects.filter(state=row).exists():
                            linked_id = TaxLotView.objects.get(state=row).taxlot_id

                if (rule.table_name, rule.field) not in self.column_lookup:
                    # If the rule is not in the column lookup, then it may have been a required
                    # field that wasn't mapped
                    if rule.required:
                        self.add_result_missing_req(row.id, rule, display_name, value)
                        label_applied = self.update_status_label(label, rule, linked_id)
                elif value is None or value == '':
                    # Empty fields
                    if rule.required:
                        self.add_result_missing_and_none(row.id, rule, display_name, value)
                        label_applied = self.update_status_label(label, rule, linked_id)
                    elif rule.not_null:
                        self.add_result_is_null(row.id, rule, display_name, value)
                        label_applied = self.update_status_label(label, rule, linked_id)
                elif not rule.valid_text(value):
                    self.add_result_string_error(row.id, rule, display_name, value)
                    label_applied = self.update_status_label(label, rule, linked_id)
                else:
                    try:
                        if not rule.minimum_valid(value):
                            s_min, s_max, s_value = rule.format_strings(value)
                            self.add_result_min_error(row.id, rule, display_name, s_value, s_min)
                            label_applied = self.update_status_label(label, rule, linked_id)
                    except ComparisonError:
                        s_min, s_max, s_value = rule.format_strings(value)
                        self.add_result_comparison_error(row.id, rule, display_name, s_value, s_min)
                        continue

                    try:
                        if not rule.maximum_valid(value):
                            s_min, s_max, s_value = rule.format_strings(value)
                            self.add_result_max_error(row.id, rule, display_name, s_value, s_max)
                            label_applied = self.update_status_label(label, rule, linked_id)
                    except ComparisonError:
                        s_min, s_max, s_value = rule.format_strings(value)
                        self.add_result_comparison_error(row.id, rule, display_name, s_value, s_max)
                        continue

                if not label_applied:
                    self.remove_status_label(label, rule, linked_id)

    def save_to_cache(self, identifier):
        """
        Save the results to the cache database. The data in the cache are
        stored as a list of dictionaries. The data in this class are stored as
        a dict of dict. This is important to remember because the data from the
        cache cannot be simply loaded into the above structure.

        :param identifier: Import file primary key
        :return: None
        """

        # change the format of the data in the cache. Make this a list of
        # objects instead of object of objects.
        existing_results = get_cache_raw(DataQualityCheck.cache_key(identifier))

        l = []
        for key, value in self.results.iteritems():
            l.append(value)

        existing_results += l

        z = sorted(existing_results, key=lambda k: k['id'])
        set_cache_raw(DataQualityCheck.cache_key(identifier), z, 86400)  # 24 hours

    def initialize_rules(self):
        """
        Initialize the default rules for a DataQualityCheck object

        :return: None
        """
        for rule in DEFAULT_RULES:
            self.rules.add(Rule.objects.create(**rule))

    def remove_all_rules(self):
        """
        Removes all the rules associated with this DataQualityCheck instance.

        :return: None
        """

        # call it this way to handle deleting status_labels
        for rule in self.rules.all():
            rule.delete()

    def reset_default_rules(self):
        """
        Reset only the default rules

        :return:
        """
        for rule in DEFAULT_RULES:
            self.rules.filter(field=rule['field'], table_name=rule['table_name']).delete()
        self.initialize_rules()

    def reset_all_rules(self):
        """
        Delete all rules and reinitialize the default set of rules

        :return: None
        """
        self.remove_all_rules()
        self.initialize_rules()

    def add_rule(self, rule):
        """
        Add a new rule to the Data Quality Checks

        :param rule: dict to be added as a new rule
        :return: None
        """
        try:
            r = Rule.objects.create(**rule)
        except TypeError as e:
            raise TypeError("Rule data is not defined correctly: {}".format(e))

        self.rules.add(r)

    def add_result_string_error(self, row_id, rule, display_name, value):
        self.results[row_id]['data_quality_results'].append(
            {
                'field': rule.field,
                'formatted_field': display_name,
                'value': value,
                'table_name': rule.table_name,
                'message': display_name + ' does not match expected value',
                'detailed_message': display_name + ' [' + str(
                    value) + '] does not contain "' + rule.text_match + '"',
                'severity': rule.get_severity_display(),
            }
        )

    def add_result_min_error(self, row_id, rule, display_name, value, rule_min):
        self.results[row_id]['data_quality_results'].append(
            {
                'field': rule.field,
                'formatted_field': display_name,
                'value': value,
                'table_name': rule.table_name,
                'message': display_name + ' out of range',
                'detailed_message': display_name + ' [' + value + '] < ' + rule_min,
                'severity': rule.get_severity_display(),
            }
        )

    def add_result_max_error(self, row_id, rule, display_name, value, rule_max):
        self.results[row_id]['data_quality_results'].append(
            {
                'field': rule.field,
                'formatted_field': display_name,
                'value': value,
                'table_name': rule.table_name,
                'message': display_name + ' out of range',
                'detailed_message': display_name + ' [' + value + '] > ' + rule_max,
                'severity': rule.get_severity_display(),
            }
        )

    def add_result_comparison_error(self, row_id, rule, display_name, value, rule_check):
        self.results[row_id]['data_quality_results'].append(
            {
                'field': rule.field,
                'formatted_field': display_name,
                'value': value,
                'table_name': rule.table_name,
                'message': display_name + ' could not be compared numerically',
                'detailed_message': display_name + ' [' + value + '] <> ' + rule_check,
                'severity': rule.get_severity_display(),
            }
        )

    def add_result_missing_req(self, row_id, rule, display_name, value):
        self.results[row_id]['data_quality_results'].append({
            'field': rule.field,
            'formatted_field': rule.field,
            'value': value,
            'table_name': rule.table_name,
            'message': rule.field + ' is missing',
            'detailed_message': rule.field + ' is required and missing',
            'severity': rule.get_severity_display(),
        })

    def add_result_missing_and_none(self, row_id, rule, display_name, value):
        self.results[row_id]['data_quality_results'].append({
            'field': rule.field,
            'formatted_field': display_name,
            'value': value,
            'table_name': rule.table_name,
            'message': display_name + ' is missing',
            'detailed_message': display_name + ' is required and is None',
            'severity': rule.get_severity_display(),
        })

    def add_result_is_null(self, row_id, rule, display_name, value):
        self.results[row_id]['data_quality_results'].append({
            'field': rule.field,
            'formatted_field': display_name,
            'value': value,
            'table_name': rule.table_name,
            'message': display_name + ' is null',
            'detailed_message': display_name + ' is null',
            'severity': rule.get_severity_display(),
        })

    def update_status_label(self, label_class, rule, linked_id):
        """

        :param label_class: statuslabel object, either property label or taxlot label
        :param rule: rule object
        :param linked_id: id of propertystate or taxlotstate object
        :return: boolean, if labeled was applied
        """

        if rule.status_label_id is not None and linked_id is not None:
            if rule.table_name == 'PropertyState':
                label_class.objects.get_or_create(property_id=linked_id,
                                                  statuslabel_id=rule.status_label_id)
            else:
                label_class.objects.get_or_create(taxlot_id=linked_id,
                                                  statuslabel_id=rule.status_label_id)
            return True

    def remove_status_label(self, label_class, rule, linked_id):
        """
        Remove label because it did not match any of the range exceptions

        :param label_class: statuslabel object, either property label or taxlot label
        :param rule: rule object
        :param linked_id: id of propertystate or taxlotstate object
        :return: boolean, if labeled was applied
        """

        if rule.table_name == 'PropertyState':
            label_class.objects.filter(property_id=linked_id,
                                       statuslabel_id=rule.status_label_id).delete()
        else:
            label_class.objects.filter(taxlot_id=linked_id,
                                       statuslabel_id=rule.status_label_id).delete()

    def retrieve_result_by_address(self, address):
        """
        Retrieve the results of the data quality checks for a specific address.

        :param address: string, address to find the result for
        :return: dict, results of data quality check for specific building
        """

        result = [v for v in self.results.values() if v['address_line_1'] == address]
        if len(result) == 0:
            return None
        elif len(result) == 1:
            return result[0]
        else:
            raise RuntimeError("More than 1 data quality results for address '{}'".format(address))

    def retrieve_result_by_tax_lot_id(self, tax_lot_id):
        """
        Retrieve the results of the data quality checks by the jurisdiction ID.

        :param tax_lot_id: string, jurisdiction tax lot id
        :return: dict, results of data quality check for specific building
        """

        result = [v for v in self.results.values() if v['jurisdiction_tax_lot_id'] == tax_lot_id]
        if len(result) == 0:
            return None
        elif len(result) == 1:
            return result[0]
        else:
            raise RuntimeError(
                "More than 1 data quality results for tax lot id '{}'".format(tax_lot_id))

    def __unicode__(self):
        return u'DataQuality ({}:{}) - Rule Count: {}'.format(self.pk, self.name,
                                                              self.rules.count())

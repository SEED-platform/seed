# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import json
import logging
import re
from builtins import str
from datetime import date, datetime
from random import randint

import pytz
from django.apps import apps
from django.db import IntegrityError, models
from django.utils.timezone import get_current_timezone, make_aware, make_naive
from past.builtins import basestring
from pint.errors import DimensionalityError
from quantityfield.units import ureg

from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    Column,
    DerivedColumn,
    PropertyView,
    StatusLabel,
    TaxLotView,
    obj_to_dict
)
from seed.serializers.pint import pretty_units
from seed.utils.cache import get_cache_raw, set_cache_raw
from seed.utils.time import convert_datestr

_log = logging.getLogger(__name__)


class ComparisonError(Exception):
    pass


class DataQualityTypeCastError(Exception):
    pass


class UnitMismatchError(Exception):
    pass


def format_pint_violation(rule, source_value):
    """
    Format a pint min, max violation for human readability.

    :param rule
    :param source_value : Quantity - value to format into range
    :return (formatted_value, formatted_min, formatted_max) : (String, String, String)
    """

    formatted_min = formatted_max = None
    incoming_data_units = source_value.units
    rule_units = ureg(rule.units)
    if rule_units.dimensionless:
        rule_value = source_value
    else:
        rule_value = source_value.to(rule_units)

    pretty_source_units = pretty_units(source_value)
    pretty_rule_units = pretty_units(rule_value)

    if incoming_data_units != rule_units:
        formatted_value = '{:.1f} {} → {:.1f} {}'.format(
            source_value.magnitude, pretty_source_units,
            rule_value.magnitude, pretty_rule_units,
        )
    else:
        formatted_value = '{:.1f} {}'.format(source_value.magnitude, pretty_rule_units)
    if rule.min is not None:
        formatted_min = '{:.1f} {}'.format(rule.min, pretty_rule_units)
    if rule.max is not None:
        formatted_max = '{:.1f} {}'.format(rule.max, pretty_rule_units)
    return formatted_value, formatted_min, formatted_max


class Rule(models.Model):
    """
    Rules for DataQualityCheck
    """
    TYPE_NUMBER = 0
    TYPE_STRING = 1
    TYPE_DATE = 2
    TYPE_YEAR = 3
    TYPE_AREA = 4
    TYPE_EUI = 5
    DATA_TYPES = [
        (TYPE_NUMBER, 'number'),
        (TYPE_STRING, 'string'),
        (TYPE_DATE, 'date'),
        (TYPE_YEAR, 'year'),
        (TYPE_AREA, 'area'),
        (TYPE_EUI, 'eui')
    ]

    RULE_TYPE_DEFAULT = 0
    RULE_TYPE_CUSTOM = 1
    RULE_TYPE = [
        (RULE_TYPE_DEFAULT, 'default'),
        (RULE_TYPE_CUSTOM, 'custom'),
    ]

    SEVERITY_ERROR = 0
    SEVERITY_WARNING = 1
    SEVERITY_VALID = 2
    SEVERITY = [
        (SEVERITY_ERROR, 'error'),
        (SEVERITY_WARNING, 'warning'),
        (SEVERITY_VALID, 'valid'),
    ]

    RULE_REQUIRED = 'required'
    RULE_NOT_NULL = 'not_null'
    RULE_RANGE = 'range'
    RULE_INCLUDE = 'include'
    RULE_EXCLUDE = 'exclude'

    DEFAULT_RULES = [
        {
            'table_name': 'PropertyState',
            'field': 'address_line_1',
            'data_type': TYPE_STRING,
            'not_null': True,
            'rule_type': RULE_TYPE_DEFAULT,
            'severity': SEVERITY_ERROR,
            'condition': RULE_NOT_NULL,
        }, {
            'table_name': 'PropertyState',
            'field': 'pm_property_id',
            'data_type': TYPE_STRING,
            'not_null': True,
            'rule_type': RULE_TYPE_DEFAULT,
            'severity': SEVERITY_ERROR,
            'condition': RULE_NOT_NULL,
        }, {
            'table_name': 'PropertyState',
            'field': 'custom_id_1',
            'not_null': True,
            'rule_type': RULE_TYPE_DEFAULT,
            'severity': SEVERITY_ERROR,
            'condition': RULE_NOT_NULL,
        }, {
            'table_name': 'TaxLotState',
            'field': 'jurisdiction_tax_lot_id',
            'not_null': True,
            'rule_type': RULE_TYPE_DEFAULT,
            'severity': SEVERITY_ERROR,
            'condition': RULE_NOT_NULL,
        }, {
            'table_name': 'TaxLotState',
            'field': 'address_line_1',
            'data_type': TYPE_STRING,
            'not_null': True,
            'rule_type': RULE_TYPE_DEFAULT,
            'severity': SEVERITY_ERROR,
            'condition': RULE_NOT_NULL,
        }, {
            'table_name': 'PropertyState',
            'field': 'conditioned_floor_area',
            'data_type': TYPE_AREA,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 0,
            'max': 7000000,
            'severity': SEVERITY_ERROR,
            'units': 'ft**2',
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'conditioned_floor_area',
            'data_type': TYPE_AREA,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 100,
            'severity': SEVERITY_WARNING,
            'units': 'ft**2',
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'energy_score',
            'data_type': TYPE_NUMBER,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 0,
            'max': 100,
            'severity': SEVERITY_ERROR,
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'energy_score',
            'data_type': TYPE_NUMBER,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 10,
            'severity': SEVERITY_WARNING,
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'generation_date',
            'data_type': TYPE_DATE,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 18890101,
            'max': 20201231,
            'severity': SEVERITY_ERROR,
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'gross_floor_area',
            'data_type': TYPE_NUMBER,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 100,
            'max': 7000000,
            'severity': SEVERITY_ERROR,
            'units': 'ft**2',
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'occupied_floor_area',
            'data_type': TYPE_NUMBER,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 100,
            'max': 7000000,
            'severity': SEVERITY_ERROR,
            'units': 'ft**2',
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'recent_sale_date',
            'data_type': TYPE_DATE,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 18890101,
            'max': 20201231,
            'severity': SEVERITY_ERROR,
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'release_date',
            'data_type': TYPE_DATE,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 18890101,
            'max': 20201231,
            'severity': SEVERITY_ERROR,
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'site_eui',
            'data_type': TYPE_EUI,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 0,
            'max': 1000,
            'severity': SEVERITY_ERROR,
            'units': 'kBtu/ft**2/year',
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'site_eui',
            'data_type': TYPE_EUI,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 10,
            'severity': SEVERITY_WARNING,
            'units': 'kBtu/ft**2/year',
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'site_eui_weather_normalized',
            'data_type': TYPE_EUI,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 0,
            'max': 1000,
            'severity': SEVERITY_ERROR,
            'units': 'kBtu/ft**2/year',
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'source_eui',
            'data_type': TYPE_EUI,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 0,
            'max': 1000,
            'severity': SEVERITY_ERROR,
            'units': 'kBtu/ft**2/year',
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'source_eui',
            'data_type': TYPE_EUI,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 10,
            'severity': SEVERITY_WARNING,
            'units': 'kBtu/ft**2/year',
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'source_eui_weather_normalized',
            'data_type': TYPE_EUI,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 10,
            'max': 1000,
            'severity': SEVERITY_ERROR,
            'units': 'kBtu/ft**2/year',
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'year_built',
            'data_type': TYPE_YEAR,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 1700,
            'max': 2019,
            'severity': SEVERITY_ERROR,
            'condition': RULE_RANGE,
        }, {
            'table_name': 'PropertyState',
            'field': 'year_ending',
            'data_type': TYPE_DATE,
            'rule_type': RULE_TYPE_DEFAULT,
            'min': 18890101,
            'max': 20201231,
            'severity': SEVERITY_ERROR,
            'condition': RULE_RANGE,
        }
    ]

    name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=1000, blank=True)
    data_quality_check = models.ForeignKey('DataQualityCheck', on_delete=models.CASCADE,
                                           related_name='rules', null=True)
    status_label = models.ForeignKey(StatusLabel, on_delete=models.DO_NOTHING, null=True)
    table_name = models.CharField(max_length=200, default='PropertyState', blank=True)
    field = models.CharField(max_length=200)
    # If for_derived_column is True, `Rule.field` is a derived column name
    # If False, `Rule.field` is a *State field or extra_data key
    for_derived_column = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    condition = models.CharField(max_length=200, default='', blank=True)
    data_type = models.IntegerField(choices=DATA_TYPES, null=True)
    rule_type = models.IntegerField(choices=RULE_TYPE, null=True)
    required = models.BooleanField(default=False)
    not_null = models.BooleanField(default=False)
    min = models.FloatField(null=True)
    max = models.FloatField(null=True)
    text_match = models.CharField(max_length=200, null=True)
    severity = models.IntegerField(choices=SEVERITY, default=SEVERITY_ERROR)
    units = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return json.dumps(obj_to_dict(self))

    def valid_text(self, value):
        """
        Validate the rule matches the specified text. Text is matched by regex.

        :param value: Value to validate rule against
        :return: bool, True is valid, False if the value does not match
        """
        if self.data_type == self.TYPE_STRING and isinstance(value, basestring):
            if self.text_match is None or self.text_match == '':
                return True
            elif self.condition == Rule.RULE_INCLUDE:
                if not re.search(self.text_match, value, re.IGNORECASE):
                    return False
            elif self.condition == Rule.RULE_EXCLUDE:
                if re.search(self.text_match, value, re.IGNORECASE):
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
            elif isinstance(value, ureg.Quantity):
                rule_min = rule_min * ureg(self.units)
            elif isinstance(value, basestring):
                # try to convert to float
                try:
                    value = float(value)
                except ValueError:
                    raise DataQualityTypeCastError(f"Error converting {value} to number")
            else:
                # must be a float...
                value = float(value)

            try:
                if value < rule_min:
                    return False
                else:
                    # If rule_min is undefined/None or value is okay, then it is valid.
                    return True
            except DimensionalityError:
                raise UnitMismatchError("Dimensions do not match for minimum compare. (Check units.)")
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
            elif isinstance(value, ureg.Quantity):
                rule_max = rule_max * ureg(self.units)
            elif isinstance(value, basestring):
                # try to convert to float
                try:
                    value = float(value)
                except ValueError:
                    raise DataQualityTypeCastError(f"Error converting {value} to number")
            else:
                # must be a float...
                value = float(value)

            try:
                if value > rule_max:
                    return False
                else:
                    return True
            except DimensionalityError:
                raise UnitMismatchError("Dimensions do not match for maximum compare. (Check units.)")
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

        if isinstance(value, basestring):
            # check if we can type cast the value
            try:
                # strip the string of any leading/trailing spaces
                value = value.strip()
                if self.data_type == self.TYPE_NUMBER:
                    if value == '':
                        return None
                    else:
                        return float(value)
                elif self.data_type == self.TYPE_STRING:
                    return str(value)
                elif self.data_type == self.TYPE_DATE:
                    if value == '':
                        return None
                    else:
                        return convert_datestr(value, True)
                elif self.data_type == self.TYPE_YEAR:
                    if value == '':
                        return None
                    else:
                        dt = convert_datestr(value, True)
                        if dt is not None:
                            return dt.date()
            except ValueError as e:
                raise DataQualityTypeCastError("Error converting {} with {}".format(value, e))
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
        elif isinstance(value, ureg.Quantity):
            f_value, f_min, f_max = format_pint_violation(self, value)
        elif isinstance(value, basestring):
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

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, default='Default Data Quality Check')

    @classmethod
    def retrieve(cls, organization_id):
        """
        DataQualityCheck was previously a simple object but has been migrated to a django model.
        This method ensures that the data quality model will be backwards compatible.

        This is the preferred method to initialize a new object.

        :param organization: instance of Organization
        :return: obj, DataQualityCheck
        """

        if DataQualityCheck.objects.filter(organization_id=organization_id).count() > 1:
            # Ensure that only one object is returned. For an unknown reason, the production
            # database has multiple DataQualityCheck objects for an organization, but there are no
            # calls to create a DataQualityCheck other than the .retrieve method.
            first = DataQualityCheck.objects.filter(organization_id=organization_id).first()
            dqcs = DataQualityCheck.objects.filter(organization_id=organization_id).exclude(
                id__in=[first.pk])
            for dqc in dqcs:
                _log.info(
                    "More than one DataQualityCheck for organization. Deleting {}".format(dqc.name))
                dqc.delete()

        dq, _ = DataQualityCheck.objects.get_or_create(organization_id=organization_id)

        if dq.rules.count() == 0:
            # _log.debug("No rules found in DataQualityCheck, initializing default rules")
            dq.initialize_rules()

        return dq

    def __init__(self, *args, **kwargs):
        # Add member variable for temp storage of results
        self.results = {}
        self.reset_results()

        # tuple based column lookup for the display name, initialize to blank here,
        # set in check_data
        self.column_lookup = {}

        super().__init__(*args, **kwargs)

    @staticmethod
    def initialize_cache(identifier, organization_id):
        """
        Initialize the cache for storing the results. This is called before the
        celery tasks are chunked up.

        The cache_key is different than the identifier. The cache_key is where all the results are
        to be stored for the data quality checks, the identifier, is the random number (or specified
        value that is used to identifier both the progress and the data storage

        :param identifier: Identifier for cache, if None, then creates a random one
        :return: list, [cache_key and the identifier]
        """
        if identifier is None:
            identifier = randint(100, 100000)
        cache_key = DataQualityCheck.cache_key(identifier, organization_id)
        set_cache_raw(cache_key, [])
        return cache_key, identifier

    @staticmethod
    def cache_key(identifier, organization_id):
        """
        Static method to return the location of the data_quality results from redis.

        :param identifier: Import file primary key
        :return:
        """
        return f"data_quality_results__{organization_id}__{identifier}"

    def check_data(self, record_type, rows):
        """
        Send in data as a queryset from the Property/Taxlot ids.

        :param record_type: one of PropertyState | TaxLotState
        :param rows: rows of data to be checked for data quality
        :return: None
        """

        # grab the columns so we can grab the display names, create lookup tuple for display name
        for c in Column.retrieve_all(self.organization, record_type, False):
            self.column_lookup[(c['table_name'], c['column_name'])] = c['display_name']

        STATE_NAME_TO_INVENTORY_TYPE = {
            'PropertyState': DerivedColumn.PROPERTY_TYPE,
            'TaxLotState': DerivedColumn.TAXLOT_TYPE
        }
        derived_columns_by_name = {
            dc.name: dc
            for dc in DerivedColumn.objects.filter(
                organization=self.organization,
                inventory_type=STATE_NAME_TO_INVENTORY_TYPE[record_type]
            )
        }
        for derived_column_name in derived_columns_by_name.keys():
            self.column_lookup[(record_type, derived_column_name)] = derived_column_name

        # grab all the rules once, save query time
        rules = self.rules.filter(enabled=True, table_name=record_type).order_by('field',
                                                                                 'severity')

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
            self._check(rules, row, derived_columns_by_name)

        # Prune the results will remove any entries that have zero data_quality_results
        for k, v in self.results.copy().items():
            if not v['data_quality_results']:
                del self.results[k]

    def get_fieldnames(self, record_type):
        """Get fieldnames to apply to results."""
        field_names = ['id']
        field_names.extend(DataQualityCheck.REQUIRED_FIELDS[record_type])
        return field_names

    def reset_results(self):
        self.results = {}

    def _check(self, rules, row, derived_columns_by_name):
        """
        Check for errors in the min/max of the values.

        :param rules: list, rules to run from database objects
        :param row: PropertyState or TaxLotState, row of data to check
        :param derived_columns_by_name: dict{str: DerivedColumn}
        :return: None
        """
        # check if the row has any rules applied to it
        model_labels = {'linked_id': None, 'label_ids': []}
        if row.__class__.__name__ == 'PropertyState':
            label = apps.get_model('seed', 'PropertyView_labels')
            if PropertyView.objects.filter(state=row).exists():
                model_labels['linked_id'] = PropertyView.objects.get(state=row).id
                model_labels['label_ids'] = list(
                    label.objects.filter(propertyview_id=model_labels['linked_id']).values_list(
                        'statuslabel_id', flat=True)
                )
                # _log.debug("Property {} has {} labels".format(model_labels['linked_id'],
                #                                               len(model_labels['label_ids'])))
        elif row.__class__.__name__ == 'TaxLotState':
            label = apps.get_model('seed', 'TaxLotView_labels')
            if TaxLotView.objects.filter(state=row).exists():
                model_labels['linked_id'] = TaxLotView.objects.get(state=row).id
                model_labels['label_ids'] = list(
                    label.objects.filter(taxlotview_id=model_labels['linked_id']).values_list(
                        'statuslabel_id', flat=True)
                )
                # _log.debug("TaxLot {} has {} labels".format(model_labels['linked_id'],
                #                                             len(model_labels['label_ids'])))

        for rule in rules:
            value = None

            label_applied = False
            display_name = rule.field

            if rule.for_derived_column:
                derived_column = derived_columns_by_name[rule.field]
                value = derived_column.evaluate(inventory_state=row)
            else:
                if hasattr(row, rule.field):
                    value = getattr(row, rule.field)
                    # TODO cleanup after the cleaner is better able to handle fields with units on import
                    # If the rule doesn't specify units only consider the value for the purposes of numerical comparison
                    if isinstance(value, ureg.Quantity) and rule.units == '':
                        value = value.magnitude
                else:  # rule is for extra_data
                    value = row.extra_data.get(rule.field, None)

                    if ' (Invalid Footprint)' in rule.field and value is not None:
                        self.add_invalid_geometry_entry_provided(row.id, rule, display_name, value)
                        continue

                    try:
                        value = rule.str_to_data_type(value)
                    except DataQualityTypeCastError:
                        self.add_result_type_error(row.id, rule, display_name, value)
                        continue

            # get the display name of the rule
            if (rule.table_name, rule.field) in self.column_lookup:
                display_name = self.column_lookup[(rule.table_name, rule.field)]

            # get the status_labels for the linked properties and tax lots
            linked_id = model_labels['linked_id']

            if (rule.table_name, rule.field) not in self.column_lookup:
                # If the rule is not in the column lookup, then it may have been a required
                # field that wasn't mapped
                if rule.condition == Rule.RULE_REQUIRED:
                    self.add_result_missing_req(row.id, rule, display_name, value)
                    label_applied = self.update_status_label(label, rule, linked_id, row.id)
            elif value is None or value == '':
                if rule.condition == Rule.RULE_REQUIRED:
                    self.add_result_missing_and_none(row.id, rule, display_name, value)
                    label_applied = self.update_status_label(label, rule, linked_id, row.id)
                elif rule.condition == Rule.RULE_NOT_NULL:
                    self.add_result_is_null(row.id, rule, display_name, value)
                    label_applied = self.update_status_label(label, rule, linked_id, row.id)
            elif rule.condition == Rule.RULE_INCLUDE or rule.condition == Rule.RULE_EXCLUDE:
                if not rule.valid_text(value):
                    self.add_result_string_error(row.id, rule, display_name, value)
                    label_applied = self.update_status_label(label, rule, linked_id, row.id)
            elif rule.condition == Rule.RULE_RANGE:
                try:
                    if not rule.minimum_valid(value):
                        if rule.severity == Rule.SEVERITY_ERROR or rule.severity == Rule.SEVERITY_WARNING:
                            s_min, s_max, s_value = rule.format_strings(value)
                            self.add_result_min_error(row.id, rule, display_name, s_value, s_min)
                            label_applied = self.update_status_label(label, rule, linked_id, row.id)
                except ComparisonError:
                    s_min, s_max, s_value = rule.format_strings(value)
                    self.add_result_comparison_error(row.id, rule, display_name, s_value, s_min)
                    continue
                except DataQualityTypeCastError:
                    s_min, s_max, s_value = rule.format_strings(value)
                    self.add_result_type_error(row.id, rule, display_name, s_value)
                    continue
                except UnitMismatchError:
                    self.add_result_dimension_error(row.id, rule, display_name, value)
                    continue

                try:
                    if not rule.maximum_valid(value):
                        if rule.severity == Rule.SEVERITY_ERROR or rule.severity == Rule.SEVERITY_WARNING:
                            s_min, s_max, s_value = rule.format_strings(value)
                            self.add_result_max_error(row.id, rule, display_name, s_value, s_max)
                            label_applied = self.update_status_label(label, rule, linked_id, row.id)
                except ComparisonError:
                    s_min, s_max, s_value = rule.format_strings(value)
                    self.add_result_comparison_error(row.id, rule, display_name, s_value, s_max)
                    continue
                except DataQualityTypeCastError:
                    s_min, s_max, s_value = rule.format_strings(value)
                    self.add_result_type_error(row.id, rule, display_name, s_value)
                    continue
                except UnitMismatchError:
                    self.add_result_dimension_error(row.id, rule, display_name, value)
                    continue

                # Check min and max values for valid data:
                if rule.minimum_valid(value) and rule.maximum_valid(value):
                    if rule.severity == Rule.SEVERITY_VALID:
                        label_applied = self.update_status_label(label, rule, linked_id, row.id, False)

            if not label_applied and rule.status_label_id in model_labels['label_ids']:
                self.remove_status_label(label, rule, linked_id)

    def save_to_cache(self, identifier, organization_id):
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
        existing_results = get_cache_raw(DataQualityCheck.cache_key(identifier, organization_id)) or []

        results = []
        for key, value in self.results.items():
            results.append(value)

        existing_results += results

        z = sorted(existing_results, key=lambda k: k['id'])
        set_cache_raw(DataQualityCheck.cache_key(identifier, organization_id), z, 86400)  # 24 hours

    def initialize_rules(self):
        """
        Initialize the default rules for a DataQualityCheck object

        :return: None
        """
        for rule in Rule.DEFAULT_RULES:
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
        for rule in Rule.DEFAULT_RULES:
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

    def add_rule_if_new(self, rule):
        """
        Add a new rule to the Data Quality Checks only if rule does not exist

        :param rule: dict to be added as a new rule
        :return: None
        """
        rule_exists = self.rules.get_queryset().filter(**rule).exists()
        if not rule_exists:
            self.add_rule(rule)

    # TODO: missing status label for all dq reports
    def add_result_string_error(self, row_id, rule, display_name, value):
        text = ''
        if rule.condition == Rule.RULE_INCLUDE:
            text = '] does not contain "'
        elif rule.condition == Rule.RULE_EXCLUDE:
            text = '] contains "'
        self.results[row_id]['data_quality_results'].append(
            {
                'field': rule.field,
                'formatted_field': display_name,
                'value': value,
                'table_name': rule.table_name,
                'message': display_name + ' does not match expected value',
                'detailed_message': display_name + ' [' + str(
                    value) + text + rule.text_match + '"',
                'severity': rule.get_severity_display(),
                'condition': rule.condition,
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
                'condition': rule.condition,
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
                'condition': rule.condition,
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
                'condition': rule.condition,
            }
        )

    def add_result_dimension_error(self, row_id, rule, display_name, value):
        self.results[row_id]['data_quality_results'].append(
            {
                'field': rule.field,
                'formatted_field': display_name,
                'value': value.magnitude,
                'table_name': rule.table_name,
                'message': display_name + ' units mismatch with rule units',
                'detailed_message': f'Units mismatched between ["{value.units}" vs "{rule.units}"]',
                'severity': rule.get_severity_display(),
                'condition': rule.condition,
            }
        )

    def add_result_type_error(self, row_id, rule, display_name, value):
        self.results[row_id]['data_quality_results'].append(
            {
                'field': rule.field,
                'formatted_field': display_name,
                'value': value,
                'table_name': rule.table_name,
                'message': display_name + ' could not be converted to numerical value',
                'detailed_message': 'Value [' + value + '] could not be converted to number',
                'severity': rule.get_severity_display(),
                'condition': rule.condition,
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
            'condition': rule.condition,
        })

    def add_result_missing_and_none(self, row_id, rule, display_name, value):
        self.results[row_id]['data_quality_results'].append({
            'field': rule.field,
            'formatted_field': display_name,
            'value': value,
            'table_name': rule.table_name,
            'message': display_name + ' is missing',
            'detailed_message': display_name + ' is required but is None',
            'severity': rule.get_severity_display(),
            'condition': rule.condition,
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
            'condition': rule.condition,
        })

    def add_invalid_geometry_entry_provided(self, row_id, rule, display_name, value):
        detailed_message = " is not a valid geometry"
        if len(str(value)) <= 25:
            detailed_message = "'{}'".format(str(value)) + detailed_message
        else:
            detailed_message = "'{}...'".format(str(value)[0:25]) + detailed_message

        self.results[row_id]['data_quality_results'].append({
            'field': rule.field,
            'formatted_field': display_name,
            'value': value,
            'table_name': rule.table_name,
            'message': display_name + ' should be in WKT format',
            'detailed_message': detailed_message,
            'severity': rule.get_severity_display(),
            'condition': rule.condition,
        })

    def update_status_label(self, label_class, rule, linked_id, row_id, add_to_results=True):
        """

        :param label_class: statuslabel object, either propertyview label or taxlotview label
        :param rule: rule object
        :param linked_id: id of propertyview or taxlotview object
        :param row_id:
        :param add_to_results: bool
        :return: boolean, if labeled was applied
        """
        if rule.status_label_id is not None and linked_id is not None:
            label_org_id = rule.status_label.super_organization_id

            if rule.table_name == 'PropertyState':
                property_parent_org_id = PropertyView.objects.get(pk=linked_id).property.organization.get_parent().id
                if property_parent_org_id == label_org_id:
                    label_class.objects.get_or_create(propertyview_id=linked_id,
                                                      statuslabel_id=rule.status_label_id)
                else:
                    raise IntegrityError(
                        'Label with super_organization_id={} cannot be applied to a record with parent '
                        'organization_id={}.'.format(
                            label_org_id,
                            property_parent_org_id
                        )
                    )
            else:
                taxlot_parent_org_id = TaxLotView.objects.get(pk=linked_id).taxlot.organization.get_parent().id
                if taxlot_parent_org_id == label_org_id:
                    label_class.objects.get_or_create(taxlotview_id=linked_id,
                                                      statuslabel_id=rule.status_label_id)
                else:
                    raise IntegrityError(
                        'Label with super_organization_id={} cannot be applied to a record with parent '
                        'organization_id={}.'.format(
                            label_org_id,
                            taxlot_parent_org_id
                        )
                    )

            if add_to_results:
                self.results[row_id]['data_quality_results'][-1]['label'] = rule.status_label.name

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
            label_class.objects.filter(propertyview_id=linked_id,
                                       statuslabel_id=rule.status_label_id).delete()
        else:
            label_class.objects.filter(taxlotview_id=linked_id,
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

    def __str__(self):
        return 'DataQuality ({}:{}) - Rule Count: {}'.format(self.pk, self.name,
                                                             self.rules.count())

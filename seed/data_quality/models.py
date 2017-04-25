# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
from datetime import date, datetime

import pytz
from django.db import models
from django.utils.timezone import get_current_timezone, make_aware, make_naive

from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    Column,
    StatusLabel,
)
from seed.utils.cache import (
    set_cache_raw, get_cache_raw
)

_log = logging.getLogger(__name__)

CATEGORY_MISSING_MATCHING_FIELD = 0
CATEGORY_MISSING_VALUES = 1
CATEGORY_IN_RANGE_CHECKING = 2
CATEGORY_DATA_TYPE_CHECK = 3
CATEGORIES = [
    (CATEGORY_MISSING_MATCHING_FIELD, "Missing Matching Field"),
    (CATEGORY_MISSING_VALUES, "Missing Values"),
    (CATEGORY_IN_RANGE_CHECKING, "In-range Checking"),
    (CATEGORY_DATA_TYPE_CHECK, "Data Type Check")
]

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
    (TYPE_NUMBER, "number"),
    (TYPE_STRING, "string"),
    (TYPE_DATE, "date"),
    (TYPE_YEAR, "year")
]

SEVERITY_ERROR = 0
SEVERITY_WARNING = 1
SEVERITY = [
    (SEVERITY_ERROR, "error"),
    (SEVERITY_WARNING, "warning")
]

RULES_MISSING_MATCHES = [
    {
        'table_name': 'PropertyState',
        'field': 'address_line_1',
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_MISSING_MATCHING_FIELD,
    },
    {
        'table_name': 'TaxLotState',
        'field': 'address_line_1',
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_MISSING_MATCHING_FIELD,
    },
    {
        'table_name': 'PropertyState',
        'field': 'custom_id_1',
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_MISSING_MATCHING_FIELD,
    },
    {
        'table_name': 'PropertyState',
        'field': 'pm_property_id',
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_MISSING_MATCHING_FIELD,
    },
    {
        'table_name': 'TaxLotState',
        'field': 'jurisdiction_tax_lot_id',
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_MISSING_MATCHING_FIELD,
    },
]
RULES_MISSING_VALUES = [
    {
        'table_name': 'PropertyState',
        'field': 'address_line_1',
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_MISSING_VALUES,
    }, {
        'table_name': 'PropertyState',
        'field': 'pm_property_id',
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_MISSING_VALUES,
    }, {
        'table_name': 'PropertyState',
        'field': 'custom_id_1',
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_MISSING_VALUES,
    }, {
        'table_name': 'TaxLotState',
        'field': 'jurisdiction_tax_lot_id',
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_MISSING_VALUES,
    }, {
        'table_name': 'TaxLotState',
        'field': 'address_line_1',
        'rule_type': RULE_TYPE_DEFAULT,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_MISSING_VALUES,
    },
]
RULES_RANGE_CHECKS = [
    {
        'table_name': 'PropertyState',
        'field': 'year_built',
        'data_type': TYPE_YEAR,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 1700,
        'max': 2019,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'year_ending',
        'data_type': TYPE_DATE,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 18890101,
        'max': 20201231,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'conditioned_floor_area',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 0,
        'max': 7000000,
        'severity': SEVERITY_ERROR,
        'units': 'square feet',
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'conditioned_floor_area',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 100,
        'severity': SEVERITY_WARNING,
        'units': 'square feet',
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'energy_score',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 0,
        'max': 100,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'energy_score',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 10,
        'severity': SEVERITY_WARNING,
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'generation_date',
        'data_type': TYPE_DATE,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 18890101,
        'max': 20201231,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'gross_floor_area',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 100,
        'max': 7000000,
        'severity': SEVERITY_ERROR,
        'units': 'square feet',
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'occupied_floor_area',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 100,
        'max': 7000000,
        'severity': SEVERITY_ERROR,
        'units': 'square feet',
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'recent_sale_date',
        'data_type': TYPE_DATE,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 18890101,
        'max': 20201231,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'release_date',
        'data_type': TYPE_DATE,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 18890101,
        'max': 20201231,
        'severity': SEVERITY_ERROR,
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'site_eui',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 0,
        'max': 1000,
        'severity': SEVERITY_ERROR,
        'units': 'kBtu/sq. ft./year',
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'site_eui',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 10,
        'severity': SEVERITY_WARNING,
        'units': 'kBtu/sq. ft./year',
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'site_eui_weather_normalized',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 0,
        'max': 1000,
        'severity': SEVERITY_ERROR,
        'units': 'kBtu/sq. ft./year',
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'source_eui',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 0,
        'max': 1000,
        'severity': SEVERITY_ERROR,
        'units': 'kBtu/sq. ft./year',
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'source_eui',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 10,
        'severity': SEVERITY_WARNING,
        'units': 'kBtu/sq. ft./year',
        'category': CATEGORY_IN_RANGE_CHECKING,
    }, {
        'table_name': 'PropertyState',
        'field': 'source_eui_weather_normalized',
        'data_type': TYPE_NUMBER,
        'rule_type': RULE_TYPE_DEFAULT,
        'min': 10,
        'max': 1000,
        'severity': SEVERITY_ERROR,
        'units': 'kBtu/sq. ft./year',
        'category': CATEGORY_IN_RANGE_CHECKING,
    }
]


# RULES_DATA_TYPE_CHECKS = [
#     {'address_line_1': TYPE_STRING},
#     {'address_line_2': TYPE_STRING},
#     {'block_number': TYPE_NUMBER},
#     {'building_certification': TYPE_STRING},
#     {'building_count': TYPE_NUMBER},
#     {'city': TYPE_STRING},
#     {'conditioned_floor_area': TYPE_NUMBER},
#     {'custom_id_1': TYPE_STRING},
#     {'district': TYPE_STRING},
#     {'energy_alerts': TYPE_STRING},
#     {'energy_score': TYPE_NUMBER},
#     {'generation_date': TYPE_DATE},
#     {'gross_floor_area': TYPE_NUMBER},
#     {'lot_number': TYPE_NUMBER},
#     {'occupied_floor_area': TYPE_NUMBER},
#     {'owner': TYPE_STRING},
#     {'owner_address': TYPE_STRING},
#     {'owner_city_state': TYPE_STRING},
#     {'owner_email': TYPE_STRING},
#     {'owner_postal_code': TYPE_STRING},
#     {'owner_telephone': TYPE_STRING},
#     {'pm_property_id': TYPE_STRING},
#     {'postal_code': TYPE_NUMBER},
#     {'property_name': TYPE_STRING},
#     {'property_notes': TYPE_STRING},
#     {'recent_sale_date': TYPE_DATE},
#     {'release_date': TYPE_DATE},
#     {'site_eui': TYPE_NUMBER},
#     {'site_eui_weather_normalized': TYPE_NUMBER},
#     {'source_eui': TYPE_NUMBER},
#     {'source_eui_weather_normalized': TYPE_NUMBER},
#     {'space_alerts': TYPE_STRING},
#     {'state_province': TYPE_STRING},
#     {'tax_lot_id': TYPE_STRING},
#     {'use_description': TYPE_STRING},
#     {'year_built': TYPE_YEAR},
#     {'year_ending': TYPE_DATE}
# ]


class Rule(models.Model):
    """
    Rules for DataQualityCheck
    """
    name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=1000, blank=True)
    data_quality_check = models.ForeignKey('DataQualityCheck', related_name='rules',
                                           on_delete=models.CASCADE, null=True)
    status_label = models.OneToOneField(StatusLabel, null=True, on_delete=models.SET_NULL)
    table_name = models.CharField(max_length=200, default='PropertyState', blank=True)
    field = models.CharField(max_length=200)
    enabled = models.BooleanField(default=True)
    category = models.IntegerField(choices=CATEGORIES)
    data_type = models.IntegerField(choices=DATA_TYPES, null=True)
    rule_type = models.IntegerField(choices=RULE_TYPE, null=True)
    min = models.FloatField(null=True)
    max = models.FloatField(null=True)
    severity = models.IntegerField(choices=SEVERITY)
    units = models.CharField(max_length=100, blank=True)

    def delete(self, *args, **kwargs):
        if self.status_label:
            self.status_label.delete()
        return super(self.__class__, self).delete(*args, **kwargs)


class DataQualityCheck(models.Model):
    """
    Object that stores the high level configuration per organization of the DataQualityCheck
    """
    REQUIRED_FIELDS = {
        'PropertyState': ['address_line_1', 'pm_property_id'],
        'TaxLotState': ['jurisdiction_tax_lot_id', 'address_line_1'],
    }

    organization = models.ForeignKey(Organization)
    name = models.CharField(max_length=255, blank='Default Data Quality Check')

    @classmethod
    def retrieve(cls, organization):
        """
        DataQualityCheck was previously a simple object but has been migrated to a django model.
        This method ensures that the data quality model will be backwards compatible.

        This is the preferred method to initialize a new object.

        :param organization: int or instance of Organization
        :return: obj, DataQualityCheck


        """
        dq, _ = DataQualityCheck.objects.get_or_create(organization=organization)
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

        super(DataQualityCheck, self).__init__(*args, **kwargs)

    @staticmethod
    def initialize_cache(file_pk):
        """
        Initialize the cache for storing the results. This is called before the
        celery tasks are chunked up.

        :param file_pk: Import file primary key
        :return: string, cache key
        """

        k = DataQualityCheck.cache_key(file_pk)
        set_cache_raw(k, [])
        return k

    @staticmethod
    def cache_key(file_pk):
        """
        Static method to return the location of the data_quality results from redis.

        :param file_pk: Import file primary key
        :return:
        """
        return "data_quality_results__%s" % file_pk

    def check_data(self, record_type, data):
        """
        Send in data as a queryset from the Property/Taxlot ids.

        :param record_type: one of property/taxlot
        :param data: rows of data to be checked for data quality
        :return:
        """

        # grab the columns in order to grab the display names
        columns = Column.retrieve_all(self.organization, record_type)
        self.column_lookup = {}

        # create lookup tuple for the display name
        for c in columns:
            self.column_lookup[(c['table'], c['name'])] = c['displayName']

        fields = self.get_fieldnames(record_type)
        for datum in data:
            # Initialize the ID if it doesn't exist yet. Add in the other
            # fields that are of interest to the GUI
            if datum.id not in self.results:
                self.results[datum.id] = {}
                for field in fields:
                    self.results[datum.id][field] = getattr(datum, field)
                self.results[datum.id]['data_quality_results'] = []

            # self._missing_matching_field(datum)
            self._in_range_checking(datum)
            self._missing_values(datum)
            # self._data_type_check(datum)

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

    def _missing_matching_field(self, datum):
        """
        Look for fields in the database that are not matched. Missing is
        defined as a None in the database

        :param datum: Database record containing the BS version of the fields populated
        :return: None

        # TODO: NL: Should we check the extra_data field for the data?
        """

        for rule in self.rules.filter(category=CATEGORY_MISSING_MATCHING_FIELD,
                                      enabled=True).order_by('field', 'severity'):
            if hasattr(datum, rule.field):
                value = getattr(datum, rule.field)
                display_name = self.column_lookup[(rule.table_name, rule.field)]
                if value is None:
                    # Field exists but the value is None. Register a data_quality error
                    self.results[datum.id]['data_quality_results'].append({
                        'field': rule.field,
                        'formatted_field': display_name,
                        'value': value,
                        'message': display_name + ' field not found',
                        'detailed_message': display_name + ' field not found',
                        'severity': rule.get_severity_display(),
                    })

    def _missing_values(self, datum):
        """
        Look for fields in the database that are empty. Need to know the list
        of fields that are part of the data_quality section.

        The original intent of this method would be very intensive to run
        (looking at all fields except the ignored).
        This method was changed to check for required values.

        :param datum: Database record containing the BS version of the fields populated
        :return: None
        """
        for rule in self.rules.filter(category=CATEGORY_MISSING_VALUES,
                                      enabled=True).order_by('field', 'severity'):
            if hasattr(datum, rule.field):
                value = getattr(datum, rule.field)
                display_name = ''
                try:
                    display_name = self.column_lookup[(rule.table_name, rule.field)]
                except KeyError:
                    pass

                if value == '':
                    # Field exists but the value is empty. Register a data_quality error
                    self.results[datum.id]['data_quality_results'].append({
                        'field': rule.field,
                        'formatted_field': display_name,
                        'value': value,
                        'message': display_name + ' is missing',
                        'detailed_message': display_name + ' is missing',
                        'severity': rule.get_severity_display()
                    })

    def _in_range_checking(self, datum):
        """
        Check for errors in the min/max of the values.

        :param datum: Database record containing the BS version of the fields populated
        :return: None
        """

        for rule in self.rules.filter(
                category=CATEGORY_IN_RANGE_CHECKING, enabled=True).order_by('field', 'severity'):
            # check if the field exists
            if hasattr(datum, rule.field):
                value = getattr(datum, rule.field)
                display_name = self.column_lookup[(rule.table_name, rule.field)]

                # Don't check the out of range errors if the data are empty
                if value is None:
                    continue

                rule_min = rule.min
                formatted_rule_min = ''
                rule_max = rule.max
                formatted_rule_max = ''
                if rule.data_type == TYPE_YEAR:
                    rule_min = int(rule_min)
                    rule_max = int(rule_max)
                if rule.data_type == TYPE_DATE:
                    rule_min = str(int(rule_min))
                    rule_max = str(int(rule_max))

                if isinstance(value, datetime):
                    value = value.astimezone(get_current_timezone()).replace(tzinfo=pytz.UTC)
                    rule_min = make_aware(datetime.strptime(rule_min, '%Y%m%d'), pytz.UTC)
                    rule_max = make_aware(datetime.strptime(rule_max, '%Y%m%d'), pytz.UTC)

                    formatted_value = str(make_naive(value, pytz.UTC))
                    formatted_rule_min = str(make_naive(rule_min, pytz.UTC))
                    formatted_rule_max = str(make_naive(rule_max, pytz.UTC))
                elif isinstance(value, date):
                    rule_min = datetime.strptime(rule_min, '%Y%m%d').date()
                    rule_max = datetime.strptime(rule_max, '%Y%m%d').date()

                if not isinstance(value, datetime):
                    formatted_value = str(value)
                    formatted_rule_min = str(rule_min)
                    formatted_rule_max = str(rule_max)

                if rule_min is not None and value < rule_min:
                    self.results[datum.id]['data_quality_results'].append({
                        'field': rule.field,
                        'formatted_field': display_name,
                        'value': value,
                        'message': display_name + ' out of range',
                        'detailed_message': display_name + ' [' + formatted_value + '] < ' +
                        formatted_rule_min,
                        'severity': rule.get_severity_display(),
                    })

                if rule_max is not None and value > rule_max:
                    self.results[datum.id]['data_quality_results'].append({
                        'field': rule.field,
                        'formatted_field': display_name,
                        'value': value,
                        'message': display_name + ' out of range',
                        'detailed_message': display_name + ' [' + formatted_value + '] > ' +
                        formatted_rule_max,
                        'severity': rule.get_severity_display(),
                    })

    def _data_type_check(self, datum):
        """
        Check the data types of the fields. These should never be wrong as
        these are the data in the database.

        This chunk of code is currently ignored.

        :param datum: Database record containing the BS version of the fields populated
        :return: None
        """

        for rule in self.rules.filter(
                category=CATEGORY_DATA_TYPE_CHECK, enabled=True).order_by('field', 'severity'):
            # check if the field exists
            if hasattr(datum, rule.field):
                value = getattr(datum, rule.field)
                display_name = self.column_lookup[(rule.table_name, rule.field)]

                # Don't check the out of range errors if the data are empty
                if value is None:
                    continue

                if type(value).__name__ != rule.data_type:
                    self.results[datum.id]['data_quality_results'].append({
                        'field': rule.field,
                        'formatted_field': display_name,
                        'value': value,
                        'message': display_name + ' value has incorrect data type',
                        'detailed_message': display_name + ' value ' + str(
                            value) + ' is not a recognized ' + rule.data_type + ' format',
                        'severity': rule.get_severity_display(),
                    })

    def save_to_cache(self, file_pk):
        """
        Save the results to the cache database. The data in the cache are
        stored as a list of dictionaries. The data in this class are stored as
        a dict of dict. This is important to remember because the data from the
        cache cannot be simply loaded into the above structure.

        :param file_pk: Import file primary key
        :return: None
        """

        # change the format of the data in the cache. Make this a list of
        # objects instead of object of objects.
        existing_results = get_cache_raw(DataQualityCheck.cache_key(file_pk))

        l = []
        for key, value in self.results.iteritems():
            l.append(value)

        existing_results = existing_results + l

        z = sorted(existing_results, key=lambda k: k['id'])
        set_cache_raw(DataQualityCheck.cache_key(file_pk), z,
                      86400)  # save the results for 24 hours

    def initialize_rules(self):
        """
        Initialize the default rules for a DataQualityCheck object

        :return: None
        """
        for rule in RULES_MISSING_MATCHES:
            self.rules.add(Rule.objects.create(**rule))
        for rule in RULES_MISSING_VALUES:
            self.rules.add(Rule.objects.create(**rule))

        for rule in RULES_RANGE_CHECKS:
            self.rules.add(Rule.objects.create(**rule))

    def remove_all_rules(self):
        """
        Removes all the rules associated with this DataQualityCheck instance.

        :return: None
        """

        # call it this way to handle deleting status_labels
        for r in self.rules.all():
            r.delete()

    def reset_default_rules(self):
        """
        Reset the instances rules back to the default set of rules

        :return:
        """
        self.remove_all_rules()
        self.initialize_rules()

    def add_rule(self, rule):
        """

        :param rule: dict to be added as a new rule
        :return: None
        """
        try:
            r = Rule.objects.create(**rule)
        except TypeError as e:
            raise TypeError("Rule data is not defined correctly: {}".format(e))

        self.rules.add(r)

    def __unicode__(self):
        return u'DataQuality ({}:{}) - Rule Count: {}'.format(self.pk, self.name,
                                                              self.rules.count())

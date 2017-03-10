# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from datetime import (
    date,
    datetime,
)
from logging import getLogger

import pytz
from django.db import models
from django.utils.timezone import get_current_timezone, make_aware, make_naive

from seed.lib.superperms.orgs.models import Organization
from seed.utils.cache import set_cache_raw, get_cache_raw
from seed.utils.constants import ASSESSOR_FIELDS_BY_COLUMN

logger = getLogger(__name__)

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


class Rules(models.Model):
    org = models.ForeignKey(Organization)
    field = models.CharField(max_length=200)
    enabled = models.BooleanField(default=True)
    category = models.IntegerField(choices=CATEGORIES)
    type = models.IntegerField(choices=DATA_TYPES, null=True)
    min = models.FloatField(null=True)
    max = models.FloatField(null=True)
    severity = models.IntegerField(choices=SEVERITY)
    units = models.CharField(max_length=100, blank=True)

    @staticmethod
    def initialize_rules(organization):
        # Required fields
        missing_matching_field = [
            'address_line_1',
            # 'tax_lot_id',
            'custom_id_1',
            'pm_property_id'
        ]
        # Ignored fields
        missing_values = [
            'address_line_1',
            # 'tax_lot_id',
            'custom_id_1',
            'pm_property_id'
        ]
        # min/max range checks
        in_range_checking = [{
            'field': 'year_built',
            'type': TYPE_YEAR,
            'min': 1700,
            'max': 2019,
            'severity': SEVERITY_ERROR
        }, {
            'field': 'year_ending',
            'type': TYPE_DATE,
            'min': 18890101,
            'max': 20201231,
            'severity': SEVERITY_ERROR
        }, {
            'field': 'conditioned_floor_area',
            'type': TYPE_NUMBER,
            'min': 0,
            'max': 7000000,
            'severity': SEVERITY_ERROR,
            'units': 'square feet'
        }, {
            'field': 'conditioned_floor_area',
            'type': TYPE_NUMBER,
            'min': 100,
            'severity': SEVERITY_WARNING,
            'units': 'square feet'
        }, {
            'field': 'energy_score',
            'type': TYPE_NUMBER,
            'min': 0,
            'max': 100,
            'severity': SEVERITY_ERROR
        }, {
            'field': 'energy_score',
            'type': TYPE_NUMBER,
            'min': 10,
            'severity': SEVERITY_WARNING
        }, {
            'field': 'generation_date',
            'type': TYPE_DATE,
            'min': 18890101,
            'max': 20201231,
            'severity': SEVERITY_ERROR
        }, {
            'field': 'gross_floor_area',
            'type': TYPE_NUMBER,
            'min': 100,
            'max': 7000000,
            'severity': SEVERITY_ERROR,
            'units': 'square feet'
        }, {
            'field': 'occupied_floor_area',
            'type': TYPE_NUMBER,
            'min': 100,
            'max': 7000000,
            'severity': SEVERITY_ERROR,
            'units': 'square feet'
        }, {
            'field': 'recent_sale_date',
            'type': TYPE_DATE,
            'min': 18890101,
            'max': 20201231,
            'severity': SEVERITY_ERROR
        }, {
            'field': 'release_date',
            'type': TYPE_DATE,
            'min': 18890101,
            'max': 20201231,
            'severity': SEVERITY_ERROR
        }, {
            'field': 'site_eui',
            'type': TYPE_NUMBER,
            'min': 0,
            'max': 1000,
            'severity': SEVERITY_ERROR,
            'units': 'kBtu/sq. ft./year'
        }, {
            'field': 'site_eui',
            'type': TYPE_NUMBER,
            'min': 10,
            'severity': SEVERITY_WARNING,
            'units': 'kBtu/sq. ft./year'
        }, {
            'field': 'site_eui_weather_normalized',
            'type': TYPE_NUMBER,
            'min': 0,
            'max': 1000,
            'severity': SEVERITY_ERROR,
            'units': 'kBtu/sq. ft./year'
        }, {
            'field': 'source_eui',
            'type': TYPE_NUMBER,
            'min': 0,
            'max': 1000,
            'severity': SEVERITY_ERROR,
            'units': 'kBtu/sq. ft./year'
        }, {
            'field': 'source_eui',
            'type': TYPE_NUMBER,
            'min': 10,
            'severity': SEVERITY_WARNING,
            'units': 'kBtu/sq. ft./year'
        }, {
            'field': 'source_eui_weather_normalized',
            'type': TYPE_NUMBER,
            'min': 10,
            'max': 1000,
            'severity': SEVERITY_ERROR,
            'units': 'kBtu/sq. ft./year'
        }]
        # data_type_check = [
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

        for field in missing_matching_field:
            Rules.objects.create(
                org=organization,
                field=field,
                category=CATEGORY_MISSING_MATCHING_FIELD,
                severity=SEVERITY_ERROR
            )
        for ignored_field in missing_values:
            Rules.objects.create(
                org=organization,
                field=ignored_field,
                category=CATEGORY_MISSING_VALUES,
                severity=SEVERITY_ERROR
            )
        for rule in in_range_checking:
            Rules.objects.create(
                org=organization,
                field=rule['field'],
                category=CATEGORY_IN_RANGE_CHECKING,
                type=rule['type'],
                min=rule.get('min'),
                max=rule.get('max'),
                severity=rule['severity'],
                units=rule.get('units', '')
            )
            # for pair in data_type_check:
            #     Rules.objects.create(
            #         org=organization,
            #         field=pair[0],
            #         category=CATEGORY_DATA_TYPE_CHECK,
            #         type=pair[1],
            #         severity=SEVERITY_ERROR
            #     )

    @staticmethod
    def restore_defaults(organization):
        Rules.delete_rules(organization)
        Rules.initialize_rules(organization)

    @staticmethod
    def delete_rules(organization):
        Rules.objects.filter(org=organization).delete()


class Cleansing(object):

    def __init__(self, organization, *args, **kwargs):
        """
        Initialize the Cleansing class.

        :param args:
        :param kwargs:
        :return:
        """
        self.required_fields = {
            'property': ['address_line_1', 'pm_property_id', 'jurisdiction_property_id'],
            'taxlot': ['jurisdiction_tax_lot_id', 'address_line_1'],
        }
        self.org = organization
        super(Cleansing, self).__init__(*args, **kwargs)

        # Create rules if none exist
        if not Rules.objects.filter(org=organization).exists():
            Rules.initialize_rules(organization)

        self.reset_results()

    @staticmethod
    def initialize_cache(file_pk):
        """
        Initialize the cache for storing the results. This is called before the
        celery tasks are chunked up.

        :param file_pk: Import file primary key
        :return:
        """
        set_cache_raw(Cleansing.cache_key(file_pk), [])

    @staticmethod
    def cache_key(file_pk):
        """
        Static method to return the location of the cleansing results from redis.

        :param file_pk: Import file primary key
        :return:
        """
        return "cleansing_results__%s" % file_pk

    def cleanse(self, record_type, data):
        """
        Send in data as a queryset from the BuildingSnapshot ids.
        :param record_type: one of property/taxlot
        :param data: rows of data to be cleansed
        :return:
        """
        fields = self.get_fieldnames(record_type)
        for datum in data:
            # Initialize the ID if it doesn't exist yet. Add in the other
            # fields that are of interest to the GUI
            if datum.id not in self.results:
                self.results[datum.id] = {}
                for field in fields:
                    self.results[datum.id][field] = getattr(datum, field)
                self.results[datum.id]['cleansing_results'] = []

            # self.missing_matching_field(datum)
            self.in_range_checking(datum)
            self.missing_values(datum)
            # self.data_type_check(datum)

        self.prune_data()

    def get_fieldnames(self, record_type):
        """Get fieldnames to apply to results."""
        field_names = ['id']
        field_names.extend(self.required_fields[record_type])
        return field_names

    def prune_data(self):
        """
        Prune the results will remove any entries that have zero cleansing_results

        :return: None
        """

        for k, v in self.results.items():
            if not v['cleansing_results']:
                del self.results[k]

    def reset_results(self):
        self.results = {}

    def missing_matching_field(self, datum):
        """
        Look for fields in the database that are not matched. Missing is
        defined as a None in the database

        :param datum: Database record containing the BS version of the fields populated
        :return: None

        # TODO: NL: Should we check the extra_data field for the data?
        """

        for rule in Rules.objects.filter(
                org=self.org,
                category=CATEGORY_MISSING_MATCHING_FIELD,
                enabled=True
        ).order_by('field', 'severity'):
            if hasattr(datum, rule.field):
                value = getattr(datum, rule.field)
                formatted_field = ASSESSOR_FIELDS_BY_COLUMN[rule.field]['title']
                if value is None:
                    # Field exists but the value is None. Register a cleansing error
                    self.results[datum.id]['cleansing_results'].append({
                        'field': rule.field,
                        'formatted_field': formatted_field,
                        'value': value,
                        'message': formatted_field + ' field not found',
                        'detailed_message': formatted_field + ' field not found',
                        'severity': dict(SEVERITY)[rule.severity]
                    })

    def missing_values(self, datum):
        """
        Look for fields in the database that are empty. Need to know the list
        of fields that are part of the cleansing section.

        The original intent of this method would be very intensive to run
        (looking at all fields except the ignored).
        This method was changed to check for required values.

        :param datum: Database record containing the BS version of the fields populated
        :return: None

        # TODO: Check the extra_data field for the data?
        """

        for rule in Rules.objects.filter(
                org=self.org,
                category=CATEGORY_MISSING_VALUES,
                enabled=True
        ).order_by('field', 'severity'):
            if hasattr(datum, rule.field):
                value = getattr(datum, rule.field)
                formatted_field = ASSESSOR_FIELDS_BY_COLUMN[rule.field]['title']

                if value == '':
                    # TODO: check if the value is zero?
                    # Field exists but the value is empty. Register a cleansing error
                    self.results[datum.id]['cleansing_results'].append({
                        'field': rule.field,
                        'formatted_field': formatted_field,
                        'value': value,
                        'message': formatted_field + ' is missing',
                        'detailed_message': formatted_field + ' is missing',
                        'severity': dict(SEVERITY)[rule.severity]
                    })

    def in_range_checking(self, datum):
        """
        Check for errors in the min/max of the values.

        :param datum: Database record containing the BS version of the fields populated
        :return: None
        """
        for rule in Rules.objects.filter(org=self.org, category=CATEGORY_IN_RANGE_CHECKING,
                                         enabled=True) \
                .order_by('field', 'severity'):

            # check if the field exists
            if hasattr(datum, rule.field):
                value = getattr(datum, rule.field)
                formatted_field = ASSESSOR_FIELDS_BY_COLUMN[rule.field]['title']

                # Don't check the out of range errors if the data are empty
                if value is None:
                    continue

                rule_min = rule.min
                rule_max = rule.max
                if rule.type == TYPE_YEAR:
                    rule_min = int(rule_min)
                    rule_max = int(rule_max)
                if rule.type == TYPE_DATE:
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
                    self.results[datum.id]['cleansing_results'].append({
                        'field': rule.field,
                        'formatted_field': formatted_field,
                        'value': value,
                        'message': formatted_field + ' out of range',
                        'detailed_message': formatted_field + ' [' + formatted_value + '] < ' + formatted_rule_min,
                        'severity': dict(SEVERITY)[rule.severity]
                    })

                if rule_max is not None and value > rule_max:
                    self.results[datum.id]['cleansing_results'].append({
                        'field': rule.field,
                        'formatted_field': formatted_field,
                        'value': value,
                        'message': formatted_field + ' out of range',
                        'detailed_message': formatted_field + ' [' + formatted_value + '] > ' + formatted_rule_max,
                        'severity': dict(SEVERITY)[rule.severity]
                    })

    def data_type_check(self, datum):
        """
        Check the data types of the fields. These should never be wrong as
        these are the data in the database.

        This chunk of code is currently ignored.

        :param datum: Database record containing the BS version of the fields populated
        :return: None
        """

        for rule in Rules.objects.filter(org=self.org, category=CATEGORY_DATA_TYPE_CHECK,
                                         enabled=True) \
                .order_by('field', 'severity'):
            # check if the field exists
            if hasattr(datum, rule.field):
                value = getattr(datum, rule.field)
                formatted_field = ASSESSOR_FIELDS_BY_COLUMN[rule.field]['title']

                # Don't check the out of range errors if the data are empty
                if value is None:
                    continue

                if type(value).__name__ != rule.type:
                    self.results[datum.id]['cleansing_results'].append({
                        'field': rule.field,
                        'formatted_field': formatted_field,
                        'value': value,
                        'message': formatted_field + ' value has incorrect data type',
                        'detailed_message': formatted_field + ' value ' + str(
                            value) + ' is not a recognized ' + rule.type + ' format',
                        'severity': dict(SEVERITY)[rule.severity]
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
        existing_results = get_cache_raw(Cleansing.cache_key(file_pk))

        l = []
        for key, value in self.results.iteritems():
            l.append(value)

        existing_results = existing_results + l

        z = sorted(existing_results, key=lambda k: k['id'])
        set_cache_raw(Cleansing.cache_key(file_pk), z, 3600)  # save the results for 1 hour

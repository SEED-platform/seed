# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import os
import json

from django.db import models
from logging import getLogger
from seed.lib.superperms.orgs.models import Organization
from seed.utils.cache import set_cache_raw, get_cache_raw
from datetime import (
    date,
    datetime,
)

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
            'tax_lot_id',
            'custom_id_1',
            'pm_property_id'
        ]
        # Ignored fields
        missing_values = [
            'address_line_1',
            'tax_lot_id',
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
        data_type_check = [
            {'address_line_1': TYPE_STRING},
            {'address_line_2': TYPE_STRING},
            {'block_number': TYPE_NUMBER},
            {'building_certification': TYPE_STRING},
            {'building_count': TYPE_NUMBER},
            {'city': TYPE_STRING},
            {'conditioned_floor_area': TYPE_NUMBER},
            {'custom_id_1': TYPE_STRING},
            {'district': TYPE_STRING},
            {'energy_alerts': TYPE_STRING},
            {'energy_score': TYPE_NUMBER},
            {'generation_date': TYPE_DATE},
            {'gross_floor_area': TYPE_NUMBER},
            {'lot_number': TYPE_NUMBER},
            {'occupied_floor_area': TYPE_NUMBER},
            {'owner': TYPE_STRING},
            {'owner_address': TYPE_STRING},
            {'owner_city_state': TYPE_STRING},
            {'owner_email': TYPE_STRING},
            {'owner_postal_code': TYPE_STRING},
            {'owner_telephone': TYPE_STRING},
            {'pm_property_id': TYPE_STRING},
            {'postal_code': TYPE_NUMBER},
            {'property_name': TYPE_STRING},
            {'property_notes': TYPE_STRING},
            {'recent_sale_date': TYPE_DATE},
            {'release_date': TYPE_DATE},
            {'site_eui': TYPE_NUMBER},
            {'site_eui_weather_normalized': TYPE_NUMBER},
            {'source_eui': TYPE_NUMBER},
            {'source_eui_weather_normalized': TYPE_NUMBER},
            {'space_alerts': TYPE_STRING},
            {'state_province': TYPE_STRING},
            {'tax_lot_id': TYPE_STRING},
            {'use_description': TYPE_STRING},
            {'year_built': TYPE_YEAR},
            {'year_ending': TYPE_DATE}
        ]

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


class Cleansing:
    def __init__(self, *args, **kwargs):
        """
        Initialize the Cleansing class. Right now this class will not need to
        save anything to the database. It is simply loading the rules from the
        JSON file upon initialization.

        :param args:
        :param kwargs:
        :return:
        """

        # Uncomment this line if this becomes a django model.
        # super(Cleansing, self).__init__(*args, **kwargs)

        # load in the configuration file
        cleansing_file = os.path.dirname(os.path.realpath(__file__)) + '/lib/cleansing.json'

        if not os.path.isfile(cleansing_file):
            raise Exception('Could not find cleansing JSON file on server %s' % cleansing_file)

        self.rules = None
        self.reset_results()
        with open(cleansing_file) as data_file:
            self.rules = json.load(data_file)
            # TODO: validate this file and load into it's own data object

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

    def cleanse(self, data):
        """
        Send in data as a queryset from the BuildingSnapshot ids.

        :param data: row of data to be cleansed
        :return:
        """

        for datum in data:
            # Initialize the ID if it doesn't exist yet. Add in the other
            # fields that are of interest to the GUI
            if datum.id not in self.results:
                self.results[datum.id] = {}
                self.results[datum.id]['id'] = datum.id
                self.results[datum.id]['address_line_1'] = datum.address_line_1
                self.results[datum.id]['pm_property_id'] = datum.pm_property_id
                self.results[datum.id]['tax_lot_id'] = datum.tax_lot_id
                self.results[datum.id]['custom_id_1'] = datum.custom_id_1
                self.results[datum.id]['cleansing_results'] = []

            # self.missing_matching_field(datum)
            self.in_range_checking(datum)
            self.missing_values(datum)
            # self.data_type_check(datum)

        self.prune_data()

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

        fields = [v for v in self.rules['modules'] if v['name'] == 'Missing Matching Field']
        if len(fields) == 1:
            fields = fields[0]['fields']
        else:
            raise RuntimeError('Could not find Missing Matching Field rules')

        for field in fields:
            if hasattr(datum, field):
                value = getattr(datum, field)
                formatted_field = self.ASSESSOR_FIELDS_BY_COLUMN[field]['title']
                if value is None:
                    # Field exists but the value is None. Register a cleansing error
                    self.results[datum.id]['cleansing_results'].append(
                        {
                            'field': field,
                            'formatted_field': formatted_field,
                            'value': value,
                            'message': formatted_field + ' field not found',
                            'detailed_message': formatted_field + ' field not found',
                            'severity': 'error'

                        }
                    )

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

        fields = [v for v in self.rules['modules'] if v['name'] == 'Missing Matching Field']
        if len(fields) == 1:
            fields = fields[0]['fields']
        else:
            raise RuntimeError('Could not find Missing Matching Field rules')

        for field in fields:
            if hasattr(datum, field):
                value = getattr(datum, field)
                formatted_field = self.ASSESSOR_FIELDS_BY_COLUMN[field]['title']

                if value == '':
                    # TODO: check if the value is zero?
                    # Field exists but the value is empty. Register a cleansing error
                    self.results[datum.id]['cleansing_results'].append(
                        {
                            'field': field,
                            'formatted_field': formatted_field,
                            'value': value,
                            'message': formatted_field + ' is missing',
                            'detailed_message': formatted_field + ' is missing',
                            'severity': 'error'
                        }
                    )

    def in_range_checking(self, datum):
        """
        Check for errors in the min/max of the values.

        :param datum: Database record containing the BS version of the fields populated
        :return: None
        """

        fields = [v for v in self.rules['modules'] if v['name'] == 'In-range Checking']
        if len(fields) == 1:
            fields = fields[0]['fields']
        else:
            raise RuntimeError('Could not find in-range checking rules')

        for field in fields:
            rules = self.rules['modules'][2]['fields'][field]

            # check if the field exists
            if hasattr(datum, field):
                value = getattr(datum, field)
                formatted_field = self.ASSESSOR_FIELDS_BY_COLUMN[field]['title']

                # Don't check the out of range errors if the data are empty
                if value is None:
                    continue

                for rule in rules:
                    rule_min = rule['min']
                    rule_max = rule['max']
                    # need to compare against a data time in the rule - this should be moved to
                    # a preprocessing method of the cleansing rules as this is run every time
                    if isinstance(value, datetime):
                        rule_min = datetime.strptime(rule_min, '%m/%d/%Y')
                        rule_max = datetime.strptime(rule_max, '%m/%d/%Y')
                    elif isinstance(value, date):
                        rule_min = datetime.strptime(rule_min, '%m/%d/%Y').date()
                        rule_max = datetime.strptime(rule_max, '%m/%d/%Y').date()

                    if rule_min is not None and value < rule_min:
                        self.results[datum.id]['cleansing_results'].append(
                            {
                                'field': field,
                                'formatted_field': formatted_field,
                                'value': value,
                                'message': formatted_field + ' out of range',
                                'detailed_message': formatted_field + ' [' + str(value) + '] < ' + str(rule_min),
                                'severity': rule['severity']
                            }
                        )

                    if rule_max is not None and value > rule_max:
                        self.results[datum.id]['cleansing_results'].append(
                            {
                                'field': field,
                                'formatted_field': formatted_field,
                                'value': value,
                                'message': formatted_field + ' out of range',
                                'detailed_message': formatted_field + ' [' + str(value) + '] > ' + str(rule_max),
                                'severity': rule['severity']
                            }
                        )

    def data_type_check(self, datum):
        """
        Check the data types of the fields. These should never be wrong as
        these are the data in the database.

        This chunk of code is currently ignored.

        :param datum: Database record containing the BS version of the fields populated
        :return: None
        """

        fields = self.rules['modules'][3]['fields']

        for field, field_data_type in fields.iteritems():
            # check if the field exists
            if hasattr(datum, field):
                value = getattr(datum, field)
                formatted_field = self.ASSESSOR_FIELDS_BY_COLUMN[field]['title']

                # Don't check the out of range errors if the data are empty
                if value is None:
                    continue

                if type(value).__name__ != field_data_type:
                    self.results[datum.id]['cleansing_results'].append(
                        {
                            'field': field,
                            'formatted_field': formatted_field,
                            'value': value,
                            'message': formatted_field + ' value has incorrect data type',
                            'detailed_message': formatted_field + ' value ' + str(value) + ' is not a recognized ' + field_data_type + ' format',  # NOQA
                            'severity': 'error'
                        }
                    )

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

    ASSESSOR_FIELDS = [
        {
            "title": "PM Property ID",
            "sort_column": "pm_property_id",
        },
        {
            "title": "Tax Lot ID",
            "sort_column": "tax_lot_id",
        },
        {
            "title": "Custom ID 1",
            "sort_column": "custom_id_1",
        },
        {
            "title": "Property Name",
            "sort_column": "property_name",
        },
        {
            "title": "Address Line 1",
            "sort_column": "address_line_1",
        },
        {
            "title": "Address Line 2",
            "sort_column": "address_line_2",
        },
        {
            "title": "County/District/Ward/Borough",
            "sort_column": "district",
        },
        {
            "title": "Lot Number",
            "sort_column": "lot_number",
        },
        {
            "title": "Block Number",
            "sort_column": "block_number",
        },
        {
            "title": "City",
            "sort_column": "city",
        },
        {
            "title": "State Province",
            "sort_column": "state_province",
        },
        {
            "title": "Postal Code",
            "sort_column": "postal_code",
        },
        {
            "title": "Year Built",
            "sort_column": "year_built",
        },
        {
            "title": "Use Description",
            "sort_column": "use_description",
        },
        {
            "title": "Building Count",
            "sort_column": "building_count",
        },
        {
            "title": "Property Notes",
            "sort_column": "property_notes",
        },
        {
            "title": "Recent Sale Date",
            "sort_column": "recent_sale_date",
        },
        {
            "title": "Owner",
            "sort_column": "owner",
        },
        {
            "title": "Owner Address",
            "sort_column": "owner_address",
        },
        {
            "title": "Owner City",
            "sort_column": "owner_city_state",
        },
        {
            "title": "Owner Postal Code",
            "sort_column": "owner_postal_code",
        },
        {
            "title": "Owner Email",
            "sort_column": "owner_email",
        },
        {
            "title": "Owner Telephone",
            "sort_column": "owner_telephone",
        },
        {
            "title": "Gross Floor Area",
            "sort_column": "gross_floor_area",
        },
        {
            "title": "Energy Star Score",
            "sort_column": "energy_score",
        },
        {
            "title": "Site EUI",
            "sort_column": "site_eui",
        },
        {
            "title": "Generation Date",
            "sort_column": "generation_date",
        },
        {
            "title": "Release Date",
            "sort_column": "release_date",
        },
        {
            "title": "Year Ending",
            "sort_column": "year_ending",
        },
        {
            "title": "Creation Date",
            "sort_column": "created",
        },
        {
            "title": "Modified Date",
            "sort_column": "modified",
        },
        {
            "title": "Conditioned Floor Area",
            "sort_column": "conditioned_floor_area",
        },
        {
            "title": "Occupied Floor Area",
            "sort_column": "occupied_floor_area",
        },
        {
            "title": "Site EUI Weather Normalized",
            "sort_column": "site_eui_weather_normalized",
        },
        {
            "title": "Source EUI",
            "sort_column": "source_eui",
        },
        {
            "title": "Source EUI Weather Normalized",
            "sort_column": "source_eui_weather_normalized",
        },
        {
            "title": "Building Certification",
            "sort_column": "building_certification",
        },
        {
            "title": "Energy Alerts",
            "sort_column": "energy_alerts",
        },
        {
            "title": "Space Alerts",
            "sort_column": "space_alerts",
        }]

    ASSESSOR_FIELDS_BY_COLUMN = {
        field['sort_column']: field for field in ASSESSOR_FIELDS
    }

import os
import json
import datetime

from logging import getLogger
from django.db import models
from django.core.cache import cache

logger = getLogger(__name__)


class Cleansing(models.Model):
    def __init__(self, *args, **kwargs):
        """
        Initialize the Cleansing class. Right now this class will not need to save anything to the database. It is
        simply loading the rules from the JSON file upon initialization.

        :param args:
        :param kwargs:
        :return:
        """
        # load in the configuration file
        super(Cleansing, self).__init__(*args, **kwargs)

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
        Initialize the cache for storing the results. This is called before the celery tasks are chunked up.

        :param file_pk: Import file primary key
        :return:
        """
        cache.set(Cleansing.cache_key(file_pk), [])

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
            # Initialize the ID if it doesn't exist yet. Add in the other fields that are of interest to the GUI
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
        Look for fields in the database that are not matched. Missing is defined as a None in the database

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
                if value is None:
                    # Field exists but the value is None. Register a cleansing error
                    self.results[datum.id]['cleansing_results'].append(
                        {
                            'field': field,
                            'message': 'Matching field not found',
                            'severity': 'error'

                        }
                    )

    def missing_values(self, datum):
        """
        Look for fields in the database that are empty. Need to know the list of fields that are part of the
        cleansing section.

        The original intent of this method would be very intensive to run (looking at all fields except the ignored).
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

                if value == '':
                    # TODO: check if the value is zero?
                    # Field exists but the value is empty. Register a cleansing error
                    self.results[datum.id]['cleansing_results'].append(
                        {
                            'field': field,
                            'message': 'Value is missing',
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

                # Don't check the out of range errors if the data are empty
                if value is None:
                    continue

                if isinstance(value, datetime.datetime):
                    value = value.toordinal()
                elif isinstance(value, datetime.date):
                    value = value.toordinal()

                for rule in rules:
                    if rule['min'] is not None and value < rule['min']:
                        self.results[datum.id]['cleansing_results'].append(
                            {
                                'field': field,
                                'message': 'Value [' + str(value) + '] < ' + str(rule['min']),
                                'severity': rule['severity']
                            }
                        )

                    if rule['max'] is not None and value > rule['max']:
                        self.results[datum.id]['cleansing_results'].append(
                            {
                                'field': field,
                                'message': 'Value [' + str(value) + '] > ' + str(rule['max']),
                                'severity': rule['severity']
                            }
                        )

    def data_type_check(self, datum):
        """
        Check the data types of the fields. These should never be wrong as these are the data in the database.
        This chunk of code is currently ignored.

        :param datum: Database record containing the BS version of the fields populated
        :return: None
        """

        fields = self.rules['modules'][3]['fields']

        for field, field_data_type in fields.iteritems():
            # check if the field exists
            if hasattr(datum, field):
                value = getattr(datum, field)

                # Don't check the out of range errors if the data are empty
                if value is None:
                    continue

                if type(value).__name__ != field_data_type:
                    self.results[datum.id]['cleansing_results'].append(
                        {
                            'field': field,
                            'message': 'Value ' + str(value) + ' is not a recognized ' + field_data_type + ' format',
                            'severity': 'error'
                        }
                    )

    def save_to_cache(self, file_pk):
        """
        Save the results to the cache database. The data in the cache are stored as a list of dictionaries. The data in
        this class are stored as a dict of dict. This is important to remember because the data from the cache cannot
        be simply loaded into the above structure.

        :param file_pk: Import file primary key
        :return: None
        """

        # change the format of the data in the cache. Make this a list of objects instead of object of objects.
        existing_results = cache.get(Cleansing.cache_key(file_pk))

        l = []
        for key, value in self.results.iteritems():
            l.append(value)

        existing_results = existing_results + l

        z = sorted(existing_results, key=lambda k: k['id'])
        cache.set(Cleansing.cache_key(file_pk), z, 3600)  # save the results for 1 hour

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

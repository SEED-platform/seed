import os
import json

from logging import getLogger
from django.db import models
from django.core.cache import cache

errors = []
warnings = []

logger = getLogger(__name__)


class Cleansing(models.Model):
    def __init__(self, *args, **kwargs):
        """
        Initialize the Cleansing class. Right now this class will not need to save anything to the database. It is simply
        loading the rules from the JSON file upon initialization.

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
        self.reset_errors_and_warnings()
        with open(cleansing_file) as data_file:
            self.rules = json.load(data_file)

    @staticmethod
    def initialize_cache(file_pk):
        # initialize cache
        cache.set(Cleansing.cache_key(file_pk), {'warnings': [], 'errors': []})

    @staticmethod
    def cache_key(file_pk):
        return "cleansing_results__%s" % file_pk

    def cleanse(self, data):
        """
        Send in data as an Array of objects or directly read from the databases
        :param data: row of data to be cleansed
        :return:
        """

        for index in range(0, len(data) - 1):
            self.missing_matching_field(data[index])
            self.missing_values(data[index])
            self.in_range_checking(data[index])
            self.data_type_check(data[index])

    def reset_errors_and_warnings(self):
        self.errors = []
        self.warnings = []

    def missing_matching_field(self, obj):
        fields = self.rules['modules'][0]['fields']

        for k in fields:
            if k in obj.keys():
                try:
                    if obj[k] == '':
                        # print 'Error in missing_matching_field: Value is empty'
                        string = k + ' = \'' + obj[k] + '\' and is empty.'
                        # print string
                        self.errors.append(string)
                    if obj[k] is None:
                        # print 'Error in missing_matching_field: Value is None'
                        string = k + ' ' + obj[k] + ' is None.'
                        # print string
                        self.errors.append(string)
                except ValueError, e:
                    # print 'Exception in missing_matching_field'
                    string = 'Error ' + str(e) + 'with ' + k
                    # print string
                    self.errors.append(string)
            else:
                # print 'Error in missing_matching_field'
                string = k + ' is missing.'
                # print string
                self.errors.append(string)

    def missing_values(self, obj):
        ignored_fields = self.rules['modules'][1]['ignoredFields']

        for k in obj.keys():
            if k not in ignored_fields:
                try:
                    if obj[k] == '':
                        # print 'Error in missing_values: Value is empty'
                        string = k + ' = \'' + obj[k] + '\' and is empty.'
                        # print string
                        errors.append(string)
                    if obj[k] is None:
                        # print 'Error in missing_values: Value is None'
                        string = k + ' ' + obj[k] + ' is None.'
                        # print string
                        errors.append(string)
                except ValueError, e:
                    # print 'Exception in in_range_checking'
                    string = 'Error ' + str(e) + 'with ' + k
                    # print string
                    errors.append(string)

    def in_range_checking(self, obj):
        in_range_dict = self.rules['modules'][2]['fields']

        for k in obj.keys():
            if k in in_range_dict:
                try:
                    if int(float(obj[k])) < int(float(in_range_dict[k][0]['min'])):
                        # print 'Error in in_range_checking'
                        string = str(obj[k]) + ' < ' + str(in_range_dict[k][0]['min'])
                        # print string
                        if in_range_dict[k][0]['severity'] == 'error':
                            self.errors.append(string)
                        else:
                            self.warnings.append(string)
                    if int(float(obj[k])) > int(float(in_range_dict[k][0]['max'])):
                        # print 'Error in in_range_checking'
                        string = str(obj[k]) + ' > ' + str(in_range_dict[k][0]['max'])
                        # print string
                        if in_range_dict[k][0]['severity'] == 'error':
                            self.errors.append(string)
                        else:
                            self.warnings.append(string)
                except ValueError, e:
                    # print 'Exception in in_range_checking'
                    string = 'Error ' + str(e) + 'with ' + k
                    # print string
                    self.errors.append(string)

    def data_type_check(self, obj):
        data_type_dict = self.rules['modules'][3]['fields']

        for k in obj.keys():
            if k in data_type_dict:
                try:
                    if type(obj[k]).__name__ != data_type_dict[k]:
                        # print 'Error in data_type_check'
                        string = k + ' ' + str(obj[k]) + ' is of type ' + type(obj[k]).__name__ + ', not of type ' + \
                                 str(data_type_dict[k])
                        # print string
                        self.errors.append(string)
                except ValueError, e:
                    # print 'Exception in data_type_check'
                    string = 'Error ' + str(e) + 'with ' + k
                    # print string
                    self.errors.append(string)

    def save_to_cache(self, file_pk):
        existing_results = cache.get(Cleansing.cache_key(file_pk))
        existing_results['warnings'] = existing_results['warnings'] + self.warnings
        existing_results['errors'] = existing_results['errors'] + self.errors
        cache.set(Cleansing.cache_key(file_pk), existing_results, 3600) # save the results for 1 hour

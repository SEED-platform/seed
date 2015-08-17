import os
import json

from logging import getLogger
from django.db import models

cleansing = []
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

        cleansing_file = os.path.relpath('/home/bldadmin/seed/seed/cleansing/lib/cleansing.json')

        if not os.path.isfile(cleansing_file):
            raise Exception('Could not find cleansing JSON file on server %s' % cleansing_file)

        self.rules = None
        with open(cleansing_file) as data_file:
            self.rules = json.load(data_file)

    def cleanse(self, data):
        """
        Send in data as an Array of objects or directly read from the databases
        :param data:
        :return:
        """

        for index in range(0, len(data) - 1):
            Cleansing.missing_matching_field(self, data[index])
            Cleansing.missing_values(self, data[index])
            Cleansing.in_range_checking(self, data[index])
            Cleansing.data_type_check(self, data[index])

    def get_errors(self):
        global errors
        return errors

    def get_warnings(self):
        global warnings
        return warnings

    def reset_errors_and_warnings(self):
        global errors
        global warnings
        errors = []
        warnings = []

    def missing_matching_field(self, obj):
        global errors

        fields = self.rules['modules'][0]['fields']

        for k in obj.keys():
            if k in fields:
                try:
                    if obj[k] == '':
                        print "Error in missing_matching_field: Value is empty"
                        string = k + " = \'" + obj[k] + "\' and is empty."
                        print string
                        errors.append(string)
                    if obj[k] is None:
                        print "Error in missing_matching_field: Value is None"
                        string = k + " " + obj[k] + " is None."
                        print string
                        errors.append(string)
                except ValueError, e:
                    print "Exception in missing_matching_field"
                    string = "Error " + str(e) + "with " + k
                    print string
                    errors.append(string)

    def missing_values(self, obj):
        global errors

        ignored_fields = self.rules['modules'][1]['ignoredFields']

        for k in obj.keys():
            if k not in ignored_fields:
                try:
                    if obj[k] == '':
                        print "Error in missing_values: Value is empty"
                        string = k + " = \'" + obj[k] + "\' and is empty."
                        print string
                        errors.append(string)
                    if obj[k] is None:
                        print "Error in missing_values: Value is None"
                        string = k + " " + obj[k] + " is None."
                        print string
                        errors.append(string)
                except ValueError, e:
                    print "Exception in in_range_checking"
                    string = "Error " + str(e) + "with " + k
                    print string
                    errors.append(string)

    def in_range_checking(self, obj):
        global errors
        global warnings

        in_range_dict = self.rules['modules'][2]['fields']

        for k in obj.keys():
            if k in in_range_dict:
                try:
                    if int(float(obj[k])) < int(float(in_range_dict[k][0]['min'])):
                        # print "Error in in_range_checking"
                        string = str(obj[k]) + " < " + str(in_range_dict[k][0]['min'])
                        # print string
                        if in_range_dict[k][0]['severity'] == "error":
                            errors.append(string)
                        else:
                            warnings.append(string)
                    if int(float(obj[k])) > int(float(in_range_dict[k][0]['max'])):
                        # print "Error in in_range_checking"
                        string = str(obj[k]) + " > " + str(in_range_dict[k][0]['max'])
                        # print string
                        if in_range_dict[k][0]['severity'] == "error":
                            errors.append(string)
                        else:
                            warnings.append(string)
                except ValueError, e:
                    # print "Exception in in_range_checking"
                    string = "Error " + str(e) + "with " + k
                    # print string
                    errors.append(string)

    def data_type_check(self, obj):
        global errors

        data_type_dict = self.rules['modules'][3]['fields']

        for k in obj.keys():
            if k in data_type_dict:
                try:
                    if type(obj[k]).__name__ != data_type_dict[k]:
                        # print "Error in data_type_check"
                        string = k + " " + str(obj[k]) + " is of type " + type(obj[k]).__name__ + ", not of type " + str(data_type_dict[k])
                        # print string
                        errors.append(string)
                except ValueError, e:
                    # print "Exception in data_type_check"
                    string = "Error " + str(e) + "with " + k
                    # print string
                    errors.append(string)


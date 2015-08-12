from django.db import models

import os
import json
import time
from celery.task import task, chord

class Cleansing(models.Model):
    def __init__(self, *args, **kwargs):
        '''
        Initialize the Cleansing class. Right now this class will not need to save anything to the database. It is simply
        loading the rules from the JSON file upon initialization.

        :param args:
        :param kwargs:
        :return:
        '''
        # load in the configuration file
        super(Cleansing, self).__init__(*args, **kwargs)

        cleansing_file = os.path.relpath('seed/cleansing/lib/cleansing.json')

        if not os.path.isfile(cleansing_file):
            raise Exception('Could not find cleaning JSON file on server %s' % (cleansing_file))

        self.rules_data = None
        with open(cleansing_file) as data_file:
            self.rules_data = json.load(data_file)


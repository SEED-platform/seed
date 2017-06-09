# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import json
import re
import string

from django.db import models

BUILDINGSYNC_MEASURES = [
    {
        "name": "RetrofitWithCFLs",
        "display_name": "Retrofit with CFLs",
        "category": "LightingImprovements",
        "category_name": "Lighting Improvements",
    }
]


def _snake_case(display_name):
    """
    Convert the BuildingSync measure display names into reasonable snake_case for storing into
    database.

    :param display_name: BuidingSync measure displayname
    :return: string
    """
    str_re = re.compile('[{0}]'.format(re.escape(string.punctuation)))
    str = str_re.sub(' ', display_name)
    str = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', str)
    str = re.sub('([a-z0-9])([A-Z])', r'\1_\2', str).lower()
    return re.sub(' +', '_', str)


class Measure(models.Model):
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    category_display_name = models.CharField(max_length=255)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'Measure - %s.%s' % (self.category, self.name)

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'

    @classmethod
    def populate_measures(cls):
        """
        Populate the list of measures from the BuildingSync
        :return:
        """
        filename = "seed/lib/buildingsync/enumerations.json"
        with open(filename) as f:
            data = json.load(f)

            for datum in data:
                # "name": "MeasureName",
                # "sub_name": "AdvancedMeteringSystems",
                # "documentation": "Advanced Metering Systems",
                # "enumerations": [
                #                     "Install advanced metering systems",
                #                     "Clean and/or repair",
                #                     "Implement training and/or documentation",
                #                     "Upgrade operating protocols, calibration, and/or sequencing",
                #                     "Other"
                #                 ],
                if datum["name"] == "MeasureName":
                    for enum in datum["enumerations"]:
                        Measure.objects.get_or_create(
                            category=_snake_case(datum["sub_name"]),
                            category_display_name=datum["documentation"],
                            name=_snake_case(enum),
                            display_name=enum,
                        )

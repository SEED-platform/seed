# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.db import models

BUILDINGSYNC_MEASURES = [
    {
        "name": "RetrofitWithCFLs",
        "display_name": "Retrofit with CFLs",
        "category": "LightingImprovements",
        "category_name": "Lighting Improvements",
    }
]


class Measure(models.Model):
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    display_category = models.CharField(max_length=255)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'Measure - %s' % self.name

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'

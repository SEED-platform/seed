# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
"""
Helper function to take an uploaded file and save new buildings from it.

Bypasses celery, for timing purposes.
"""
from django.core.management.base import BaseCommand
from django.test.utils import override_settings

from seed.tasks import save_raw_data


class Command(BaseCommand):

    help = 'Runs an import job sans celery'

    @override_settings(CELERY_ALWAYS_EAGER=True)
    def handle(self, *args, **options):
        pk = int(args[0])
        print "Importing file %s" % pk
        print save_raw_data(pk)

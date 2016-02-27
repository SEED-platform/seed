"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
"""Runs CircleCI harvest tests in parallel
"""
import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    args = ''

    def handle(self, *args, **options):
        kwargs = {}
        if "settings" in options:
            kwargs["settings"] = options["settings"]

        apps = settings.SEED_CORE_APPS
        CIRCLE_NODE_INDEX = int(os.environ["CIRCLE_NODE_INDEX"])
        CIRCLE_NODE_TOTAL = int(os.environ["CIRCLE_NODE_TOTAL"])

        my_apps = []
        counter = 0
        for a in apps:
            if counter % CIRCLE_NODE_TOTAL == CIRCLE_NODE_INDEX:
                my_apps.append(a)
            counter += 1

        call_command("test", *my_apps, **kwargs)

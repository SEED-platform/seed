"""
:copyright: (c) 2014 Building Energy Inc
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

        apps = settings.BE_CORE_APPS
        CIRCLE_NODE_INDEX = int(os.environ["CIRCLE_NODE_INDEX"])
        CIRCLE_NODE_TOTAL = int(os.environ["CIRCLE_NODE_TOTAL"])

        my_apps = []
        counter = 0
        for a in apps:
            if counter % CIRCLE_NODE_TOTAL == CIRCLE_NODE_INDEX:
                my_apps.append(a)
            counter += 1

        call_command("test", *my_apps, **kwargs)

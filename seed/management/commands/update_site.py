"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = "Updates the django site"

    def add_arguments(self, parser):
        parser.add_argument("-n", "--name", help="Sets the site name")
        parser.add_argument(
            "-d",
            "--domain",
            help="Sets the site domain",
        )

    def handle(self, *_, **options):
        site = Site.objects.first()
        if options["name"] is not None:
            site.name = options["name"]
        if options["domain"] is not None:
            site.domain = options["domain"]
        site.save()

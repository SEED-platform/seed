from __future__ import unicode_literals

from django.db import models, migrations
from django.core.management.base import BaseCommand
from django.apps import apps


class Command(BaseCommand):
    def handle(self, *args, **options):
        print "Destroying Blue Sky Data"

        apps.get_model("bluesky", "Cycle").objects.all().delete()
        apps.get_model("bluesky", "PropertyState").objects.all().delete()
        apps.get_model("bluesky", "PropertyView").objects.all().delete()
        apps.get_model("bluesky", "Property").objects.all().delete()
        apps.get_model("bluesky", "TaxLotState").objects.all().delete()
        apps.get_model("bluesky", "TaxLotView").objects.all().delete()
        apps.get_model("bluesky", "TaxLot").objects.all().delete()
        apps.get_model("bluesky", "TaxLotProperty").objects.all().delete()

        return

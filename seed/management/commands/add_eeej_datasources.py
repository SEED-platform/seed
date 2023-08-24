from django.core.management.base import BaseCommand

from seed.lib.geospatial.eeej import add_eeej_data


class Command(BaseCommand):
    help = 'Add EEEJ Data: HUD and CEJST'

    def handle(self, *args, **options):

        add_eeej_data()
        print("done!")

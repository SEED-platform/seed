from destroy_bluesky_data import Command as DestroyDataCommand
from migrate_organization import Command as MigrateOrganizationCommand
from create_campus_relationships_organization import Command as CreateCampusCommand
from create_m2m_relationships_organization import Command as CreateM2MCommand
from django.core.management.base import BaseCommand
from seed.models import CanonicalBuilding


class Command(BaseCommand):
    def add_arguments(self, parser):
        # Global parameters for controlling script behavior
        parser.add_argument('--destroy', dest='destroy', default=False, action="store_true")
        parser.add_argument('--migrate', dest='migrate', default=False, action="store_true")
        parser.add_argument('--campus', dest='campus', default=False, action="store_true")
        parser.add_argument('--m2m', dest='m2m', default=False, action="store_true")

        # Global search parameters
        parser.add_argument('--pm', dest='pm', default=False)

        parser.add_argument('--org', dest='organization', default=False)

        # Migration Arguments
        parser.add_argument('--limit', dest='limit', default=0, type=int)
        parser.add_argument('--starting_on_canonical', dest='starting_on_canonical', default=0, type=int)
        parser.add_argument('--starting_following_canonical', dest='starting_following_canonical', default=0, type=int)
        parser.add_argument('--no_metadata', dest='add_metadata', default=True, action='store_false')
        parser.add_argument('--cb', dest='cb_whitelist_string', default=False,)

        parser.add_argument('--stats', dest='stats', default=False, action="store_true")

        return


    def handle(self, *args, **options):



        if options['pm']:
            pm_property_ids = options['pm']

            pms = map(lambda x: x.strip(), pm_property_ids.split(","))
            cbs = ",".join(map(lambda x: str(x.pk), CanonicalBuilding.objects.filter(buildingsnapshot__pm_property_id__in=pms, active=True).all()))

            if not options['cb_whitelist_string']:
                options['cb_whitelist_string'] = cbs
            else:
                options['cb_whitelist_string'] = options['cb_whitelist_string'] + "," + cbs

        destroy, migrate, campus, m2m = map(lambda x: options[x], ("destroy", "migrate", "campus", "m2m"))

        if not destroy and not migrate and not campus and not m2m:
            destroy, migrate, campus, m2m = [True] * 4

        if destroy:
            ddc = DestroyDataCommand()
            ddc.handle(*args, **options)

        if migrate:
            mdc = MigrateOrganizationCommand()
            mdc.handle(*args, **options)

        if campus:
            create_campus_command = CreateCampusCommand()
            create_campus_command.handle(*args, **options)

        if m2m:
            create_m2m_command = CreateM2MCommand()
            create_m2m_command.handle(*args, **options)

        return

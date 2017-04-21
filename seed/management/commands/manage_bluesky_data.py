from destroy_bluesky_data import Command as DestroyDataCommand
from migrate_organization import Command as MigrateOrganizationCommand
from create_campus_relationships_organization import Command as CreateCampusCommand
from create_m2m_relationships_organization import Command as CreateM2MCommand
from create_primarysecondary_taxlots import Command as CreatePrimarySecondaryCommand
from migrate_extradata_columns import Command as MigrateColumnsCommand
from migrate_labels import Command as MigrateLabelsCommand
from single_org_commands import Command as SingleOrgCommand
from django.core.management.base import BaseCommand
from seed.models import CanonicalBuilding


class Command(BaseCommand):
    def add_arguments(self, parser):
        # Global parameters for controlling script behavior
        parser.add_argument('--destroy', dest='destroy', default=False, action="store_true")
        parser.add_argument('--migrate', dest='migrate', default=False, action="store_true")
        parser.add_argument('--campus', dest='campus', default=False, action="store_true")
        parser.add_argument('--m2m', dest='m2m', default=False, action="store_true")
        parser.add_argument('--primarysecondary', dest='primarysecondary', default=False, action="store_true")
        parser.add_argument('--columns', dest='migrate_columns', default=False, action="store_true")
        parser.add_argument('--labels', dest='migrate_labels', default=False, action="store_true")

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

        # Column migration arguments
        parser.add_argument('--no-update-columns', dest='update_columns', default=True, action="store_false")
        parser.add_argument('--update-columns',    dest='update_columns', default=True, action="store_true")

        parser.add_argument('--no-add-unmapped-columns', dest='add_unmapped_columns', default=True, action="store_false")
        parser.add_argument('--add-unmapped-columns',    dest='add_unmapped_columns', default=True, action="store_true")

        parser.add_argument('--no-create-missing-columns', dest='create_missing_columns', default=True, action="store_false")
        parser.add_argument('--create-missing-columns',    dest='create_missing_columns', default=True, action="store_true")

        # Labels arguments

        parser.add_argument('--clear-bluesky-labels', dest='clear_bluesky_labels', default=False, action="store_true",
                            help="Delete all labels associated with all View objects")

        parser.add_argument('--labels-add-property-labels', dest='add_property_labels', default=True, action="store_true",
                            help="Create labels for PropertyView Objects")
        parser.add_argument('--labels-no-add-property-labels', dest='add_property_labels', default=True, action="store_false",
                            help="Do not create Labels to Property View Objects")

        parser.add_argument('--labels-add-taxlot-labels', dest='add_taxlot_labels', default=True, action="store_true",
                            help="Create labels on TaxLotView objects")

        parser.add_argument('--labels-no-add-taxlot-labels', dest='add_taxlot_labels', default=True, action="store_false",
                            help="Do not create labels on TaxLotView objects")


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

        options['clear_bluesky_labels'] = False

        destroy, migrate, campus, m2m, primarysecondary, migrate_columns, migrate_labels = map(lambda x: options[x], ("destroy", "migrate", "campus", "m2m", "primarysecondary", "migrate_columns", "migrate_labels"))

        if not destroy and not migrate and not campus and not m2m and not primarysecondary and not migrate_columns and not migrate_labels:
            destroy, migrate, campus, m2m, primarysecondary, migrate_columns, migrate_labels = [True] * 7

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

        if primarysecondary:
            create_primarysecondary_command = CreatePrimarySecondaryCommand()
            create_primarysecondary_command.handle(*args, **options)

        if migrate_columns:
            migrate_columns_command = MigrateColumnsCommand()
            migrate_columns_command.handle(*args, **options)


        if migrate_labels:
            migrate_labels_command = MigrateLabelsCommand()
            migrate_labels_command.handle(*args, **options)

        single_org_command = SingleOrgCommand()
        single_org_command.handle(*args, **options)

        return

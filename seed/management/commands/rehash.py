# -*- coding: utf-8 -*-
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from seed.models import PropertyState, TaxLotState


class Command(BaseCommand):
    help = 'Rehashes all Property and Tax Lot states, and reports how many were modified'

    def handle(self, *args, **options):
        properties_updated = 0
        taxlots_updated = 0

        with transaction.atomic():
            property_states = PropertyState.objects.all()
            self.stdout.write("Re-hashing %s Property States" % len(property_states))

            for state in property_states:
                old_hash = state.hash_object
                state.save(update_fields=['hash_object'])
                if state.hash_object != old_hash:
                    properties_updated += 1

            self.stdout.write("  %s Property States updated" % properties_updated)

            taxlot_states = TaxLotState.objects.all()
            self.stdout.write("Re-hashing %s Tax Lot States" % len(taxlot_states))

            for state in taxlot_states:
                old_hash = state.hash_object
                state.save(update_fields=['hash_object'])
                if state.hash_object != old_hash:
                    taxlots_updated += 1

            self.stdout.write("  %s Tax Lot States updated" % taxlots_updated)

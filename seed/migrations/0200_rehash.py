# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-01-19 21:18
from __future__ import unicode_literals

from django.db import migrations, transaction

from seed.data_importer.tasks import hash_state_object


def rehash(apps, schema_editor):
    PropertyState = apps.get_model('seed', 'PropertyState')
    TaxLotState = apps.get_model('seed', 'TaxLotState')

    with transaction.atomic():
        properties_updated = 0
        taxlots_updated = 0

        property_states = PropertyState.objects.all()
        print("Re-hashing %s Property States" % len(property_states))

        for state in property_states:
            old_hash = state.hash_object
            state.hash_object = hash_state_object(state)
            state.save(update_fields=['hash_object'])
            if state.hash_object != old_hash:
                properties_updated += 1

        print("  %s Property State hashes updated" % properties_updated)

        taxlot_states = TaxLotState.objects.all()
        print("Re-hashing %s Tax Lot States" % len(taxlot_states))

        for state in taxlot_states:
            old_hash = state.hash_object
            state.hash_object = hash_state_object(state)
            state.save(update_fields=['hash_object'])
            if state.hash_object != old_hash:
                taxlots_updated += 1

        print("  %s TaxLot State hashes updated" % taxlots_updated)


class Migration(migrations.Migration):
    dependencies = [
        ('seed', '0199_rename_ulid_taxlotstate_ubid'),
    ]

    operations = [
        migrations.RunPython(rehash),
    ]
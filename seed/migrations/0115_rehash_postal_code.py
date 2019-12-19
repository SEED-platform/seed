# -*- coding: utf-8 -*-

# This rehashing file should be used in the future if needed as it has been optimized. Rehashing takes
# awhile and should be avoided if possible.
from __future__ import unicode_literals

import re

from django.db import migrations, transaction
from django.db.models import Q


def zero_fill(postal):
    if postal:
        if bool(re.compile(r'(\b\d{1,5}-\d{1,4}\b)').match(postal)):
            return postal.split('-')[0].zfill(5) + '-' + postal.split('-')[1].zfill(4)
        elif bool(re.compile(r'(\b\d{1,5}\b)').match(postal)):
            return postal.zfill(5)


# Go through every property and tax lot and simply save it to create the hash_object
def update_postal_codes(apps, schema_editor):
    PropertyState = apps.get_model('seed', 'PropertyState')
    TaxLotState = apps.get_model('seed', 'TaxLotState')

    with transaction.atomic():
        print('Checking for short postal codes in property states')
        objs = PropertyState.objects.filter(
            Q(postal_code__iregex=r'^\d{4}-\d{3,4}$') | Q(postal_code__iregex=r'^\d{4}$') |
            Q(owner_postal_code__iregex=r'^\d{4}-\d{3,4}$') | Q(owner_postal_code__iregex=r'^\d{4}$')
        )
        for obj in objs:
            # print(
            #     f'fixing zip for {obj} -- postal_code | owner_postal_code = {obj.postal_code} | {obj.owner_postal_code}')
            obj.postal_code = zero_fill(obj.postal_code)
            obj.owner_postal_code = zero_fill(obj.owner_postal_code)
            obj.save()

        print('Checking for short postal codes in tax lot states')
        objs = TaxLotState.objects.filter(
            Q(postal_code__iregex=r'^\d{4}-\d{3,4}$') | Q(postal_code__iregex=r'^\d{4}$')
        )
        for obj in objs:
            # print(
            #     f'fixing zip for {obj} -- postal_code | owner_postal_code = {obj.postal_code} | {obj.owner_postal_code}')
            obj.postal_code = zero_fill(obj.postal_code)
            obj.save()


class Migration(migrations.Migration):
    dependencies = [
        ('seed', '0114_auto_20191211_0958'),
    ]

    operations = [
        migrations.RunPython(update_postal_codes),
    ]

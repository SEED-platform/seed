# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0012_auto_20151222_1031'),
    ]

    operations = [
        migrations.AlterField(
            model_name='buildingsnapshot',
            name='building_count',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='buildingsnapshot',
            name='children',
            field=models.ManyToManyField(related_name='parents', to='seed.BuildingSnapshot', blank=True),
        ),
        migrations.AlterField(
            model_name='columnmapping',
            name='column_mapped',
            field=models.ManyToManyField(related_name='mapped_mappings', to='seed.Column', blank=True),
        ),
        migrations.AlterField(
            model_name='columnmapping',
            name='column_raw',
            field=models.ManyToManyField(related_name='raw_mappings', to='seed.Column', blank=True),
        ),
        migrations.AlterField(
            model_name='enum',
            name='enum_values',
            field=models.ManyToManyField(related_name='values', to='seed.EnumValue', blank=True),
        ),
        migrations.AlterField(
            model_name='meter',
            name='building_snapshot',
            field=models.ManyToManyField(related_name='meters', to='seed.BuildingSnapshot', blank=True),
        ),
        migrations.AlterField(
            model_name='meter',
            name='energy_type',
            field=models.IntegerField(choices=[(1, b'Natural Gas'), (2, b'Electricity'), (3, b'Fuel Oil'), (4, b'Fuel Oil No. 1'), (5, b'Fuel Oil No. 2'), (6, b'Fuel Oil No. 4'), (7, b'Fuel Oil No. 5 and No. 6'), (8, b'District Steam'), (9, b'District Hot Water'), (10, b'District Chilled Water'), (11, b'Propane'), (12, b'Liquid Propane'), (13, b'Kerosene'), (14, b'Diesel'), (15, b'Coal'), (16, b'Coal Anthracite'), (17, b'Coal Bituminous'), (18, b'Coke'), (19, b'Wood'), (20, b'Other')]),
        ),
        migrations.AlterField(
            model_name='meter',
            name='energy_units',
            field=models.IntegerField(choices=[(1, b'kWh'), (2, b'Therms'), (3, b'Wh')]),
        ),
        migrations.AlterField(
            model_name='project',
            name='building_snapshots',
            field=models.ManyToManyField(to='seed.BuildingSnapshot', through='seed.ProjectBuilding', blank=True),
        ),
    ]

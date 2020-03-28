# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.jsonb
import django_extensions.db.fields
import autoslug.fields
import django.utils.timezone
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('data_importer', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orgs', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttributeOption',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(max_length=255)),
                ('value_source', models.IntegerField(choices=[(0, b'Assessed Raw'), (2, b'Assessed'), (1, b'Portfolio Raw'), (3, b'Portfolio'), (4, b'BuildingSnapshot'), (5, b'Green Button Raw')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BuildingAttributeVariant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field_name', models.CharField(max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BuildingSnapshot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False, blank=True)),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False, blank=True)),
                ('tax_lot_id', models.CharField(db_index=True, max_length=128, null=True, blank=True)),
                ('pm_property_id', models.CharField(db_index=True, max_length=128, null=True, blank=True)),
                ('custom_id_1', models.CharField(db_index=True, max_length=128, null=True, blank=True)),
                ('lot_number', models.CharField(max_length=128, null=True, blank=True)),
                ('block_number', models.CharField(max_length=128, null=True, blank=True)),
                ('property_notes', models.TextField(null=True, blank=True)),
                ('year_ending', models.DateField(null=True, blank=True)),
                ('district', models.CharField(max_length=128, null=True, blank=True)),
                ('owner', models.CharField(max_length=128, null=True, blank=True)),
                ('owner_email', models.CharField(max_length=128, null=True, blank=True)),
                ('owner_telephone', models.CharField(max_length=128, null=True, blank=True)),
                ('owner_address', models.CharField(max_length=128, null=True, blank=True)),
                ('owner_city_state', models.CharField(max_length=128, null=True, blank=True)),
                ('owner_postal_code', models.CharField(max_length=128, null=True, blank=True)),
                ('property_name', models.CharField(max_length=255, null=True, blank=True)),
                ('building_count', models.IntegerField(max_length=3, null=True, blank=True)),
                ('gross_floor_area', models.FloatField(null=True, blank=True)),
                ('address_line_1', models.CharField(db_index=True, max_length=255, null=True, blank=True)),
                ('address_line_2', models.CharField(db_index=True, max_length=255, null=True, blank=True)),
                ('city', models.CharField(max_length=255, null=True, blank=True)),
                ('postal_code', models.CharField(max_length=255, null=True, blank=True)),
                ('year_built', models.IntegerField(null=True, blank=True)),
                ('recent_sale_date', models.DateTimeField(null=True, blank=True)),
                ('energy_score', models.IntegerField(null=True, blank=True)),
                ('site_eui', models.FloatField(null=True, blank=True)),
                ('generation_date', models.DateTimeField(null=True, blank=True)),
                ('release_date', models.DateTimeField(null=True, blank=True)),
                ('state_province', models.CharField(max_length=255, null=True, blank=True)),
                ('site_eui_weather_normalized', models.FloatField(null=True, blank=True)),
                ('source_eui', models.FloatField(null=True, blank=True)),
                ('source_eui_weather_normalized', models.FloatField(null=True, blank=True)),
                ('energy_alerts', models.TextField(null=True, blank=True)),
                ('space_alerts', models.TextField(null=True, blank=True)),
                ('building_certification', models.CharField(max_length=255, null=True, blank=True)),
                ('conditioned_floor_area', models.FloatField(null=True, blank=True)),
                ('occupied_floor_area', models.FloatField(null=True, blank=True)),
                ('use_description', models.TextField(null=True, blank=True)),
                ('best_guess_confidence', models.FloatField(null=True, blank=True)),
                ('match_type', models.IntegerField(blank=True, null=True, db_index=True, choices=[(1, b'System Match'), (2, b'User Match'), (3, b'Possible Match')])),
                ('confidence', models.FloatField(db_index=True, null=True, blank=True)),
                ('source_type', models.IntegerField(blank=True, null=True, db_index=True, choices=[(0, b'Assessed Raw'), (2, b'Assessed'), (1, b'Portfolio Raw'), (3, b'Portfolio'), (4, b'BuildingSnapshot'), (5, b'Green Button Raw')])),
                ('extra_data', django.contrib.postgres.fields.jsonb.JSONField(default={}, null=True, blank=True)),
                ('extra_data_sources', django.contrib.postgres.fields.jsonb.JSONField(default={}, null=True, blank=True)),
                ('address_line_1_source', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True)),
                ('address_line_2_source', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True)),
            ],
            options={
                'ordering': ('-modified', '-created'),
                'abstract': False,
                'get_latest_by': 'modified',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CanonicalBuilding',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('active', models.BooleanField(default=True)),
                ('canonical_snapshot', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='seed.BuildingSnapshot', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Column',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('column_name', models.CharField(max_length=512, db_index=True)),
                ('is_extra_data', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ColumnMapping',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('source_type', models.IntegerField(blank=True, null=True, choices=[(0, b'Assessed Raw'), (2, b'Assessed'), (1, b'Portfolio Raw'), (3, b'Portfolio'), (4, b'BuildingSnapshot'), (5, b'Green Button Raw')])),
                ('column_mapped', models.ManyToManyField(related_name='mapped_mappings', null=True, to='seed.Column', blank=True)),
                ('column_raw', models.ManyToManyField(related_name='raw_mappings', null=True, to='seed.Column', blank=True)),
                ('super_organization', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='column_mappings', verbose_name='SeedOrg', blank=True, to='orgs.Organization', null=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Compliance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False, blank=True)),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False, blank=True)),
                ('compliance_type', models.CharField(default=b'Benchmarking', max_length=30, verbose_name='compliance_type', choices=[(b'Benchmarking', 'Benchmarking'), (b'Auditing', 'Auditing'), (b'Retro Commissioning', 'Retro Commissioning')])),
                ('start_date', models.DateField(null=True, verbose_name='start_date', blank=True)),
                ('end_date', models.DateField(null=True, verbose_name='end_date', blank=True)),
                ('deadline_date', models.DateField(null=True, verbose_name='deadline_date', blank=True)),
            ],
            options={
                'ordering': ('-modified', '-created'),
                'abstract': False,
                'get_latest_by': 'modified',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CustomBuildingHeaders',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('building_headers', django.contrib.postgres.fields.jsonb.JSONField(default={}, null=True, blank=True)),
                ('super_organization', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='custom_headers', verbose_name='SeedOrg', blank=True, to='orgs.Organization', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Enum',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('enum_name', models.CharField(max_length=255, db_index=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EnumValue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value_name', models.CharField(max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Meter',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('energy_type', models.IntegerField(max_length=3, choices=[(1, b'Natural Gas'), (2, b'Electricity'), (3, b'Fuel Oil'), (4, b'Fuel Oil No. 1'), (5, b'Fuel Oil No. 2'), (6, b'Fuel Oil No. 4'), (7, b'Fuel Oil No. 5 and No. 6'), (8, b'District Steam'), (9, b'District Hot Water'), (10, b'District Chilled Water'), (11, b'Propane'), (12, b'Liquid Propane'), (13, b'Kerosene'), (14, b'Diesel'), (15, b'Coal'), (16, b'Coal Anthracite'), (17, b'Coal Bituminous'), (18, b'Coke'), (19, b'Wood'), (20, b'Other')])),
                ('energy_units', models.IntegerField(max_length=3, choices=[(1, b'kWh'), (2, b'Therms'), (3, b'Wh')])),
                ('building_snapshot', models.ManyToManyField(related_name='meters', null=True, to='seed.BuildingSnapshot', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False, blank=True)),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False, blank=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'name', editable=True, unique=True, verbose_name='slug')),
                ('description', models.TextField(null=True, verbose_name='description', blank=True)),
                ('status', models.IntegerField(default=1, verbose_name='status', choices=[(0, 'Inactive'), (1, 'Active')])),
            ],
            options={
                'ordering': ('-modified', '-created'),
                'abstract': False,
                'get_latest_by': 'modified',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectBuilding',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False, blank=True)),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False, blank=True)),
                ('compliant', models.NullBooleanField()),
                ('approved_date', models.DateField(null=True, verbose_name='approved_date', blank=True)),
                ('approver', models.ForeignKey(on_delete=models.deletion.CASCADE, verbose_name='User', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('building_snapshot', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='project_building_snapshots', to='seed.BuildingSnapshot')),
                ('project', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='project_building_snapshots', to='seed.Project')),
            ],
            options={
                'ordering': ['project', 'building_snapshot'],
                'verbose_name': 'project building',
                'verbose_name_plural': 'project buildings',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Schema',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50, db_index=True)),
                ('columns', models.ManyToManyField(related_name='schemas', to='seed.Column')),
                ('organization', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='schemas', blank=True, to='orgs.Organization', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StatusLabel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False, blank=True)),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False, blank=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('color', models.CharField(default=b'green', max_length=30, verbose_name='compliance_type', choices=[(b'red', 'red'), (b'blue', 'blue'), (b'light blue', 'light blue'), (b'green', 'green'), (b'white', 'white'), (b'orange', 'orange')])),
                ('super_organization', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='status_labels', verbose_name='SeedOrg', blank=True, to='orgs.Organization', null=True)),
            ],
            options={
                'ordering': ['-name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TimeSeries',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('begin_time', models.DateTimeField(null=True, blank=True)),
                ('end_time', models.DateTimeField(null=True, blank=True)),
                ('reading', models.FloatField(null=True)),
                ('cost', models.DecimalField(null=True, max_digits=11, decimal_places=4)),
                ('meter', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='timeseries_data', blank=True, to='seed.Meter', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Unit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('unit_name', models.CharField(max_length=255)),
                ('unit_type', models.IntegerField(default=1, choices=[(1, b'String'), (2, b'Decimal'), (3, b'Float'), (4, b'Date'), (5, b'Datetime')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='statuslabel',
            unique_together=set([('name', 'super_organization')]),
        ),
        migrations.AddField(
            model_name='projectbuilding',
            name='status_label',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, blank=True, to='seed.StatusLabel', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='projectbuilding',
            unique_together=set([('building_snapshot', 'project')]),
        ),
        migrations.AddField(
            model_name='project',
            name='building_snapshots',
            field=models.ManyToManyField(to='seed.BuildingSnapshot', null=True, through='seed.ProjectBuilding', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='last_modified_by',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='last_modified_user', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='owner',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, verbose_name='User', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='super_organization',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='projects', verbose_name='SeedOrg', blank=True, to='orgs.Organization', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='enum',
            name='enum_values',
            field=models.ManyToManyField(related_name='values', null=True, to='seed.EnumValue', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='compliance',
            name='project',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, verbose_name='Project', to='seed.Project'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='column',
            name='enum',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, blank=True, to='seed.Enum', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='column',
            name='organization',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, blank=True, to='orgs.Organization', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='column',
            name='unit',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, blank=True, to='seed.Unit', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='column',
            unique_together=set([('organization', 'column_name', 'is_extra_data')]),
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='best_guess_canonical_building',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='best_guess', blank=True, to='seed.CanonicalBuilding', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='block_number_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='building_certification_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='building_count_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='canonical_building',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='seed.CanonicalBuilding', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='canonical_for_ds',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='data_importer.ImportRecord', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='children',
            field=models.ManyToManyField(related_name='parents', null=True, to='seed.BuildingSnapshot', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='city_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='conditioned_floor_area_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='custom_id_1_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='district_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='energy_alerts_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='energy_score_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='generation_date_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='gross_floor_area_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='import_file',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, blank=True, to='data_importer.ImportFile', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='last_modified_by',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='lot_number_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='occupied_floor_area_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='owner_address_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='owner_city_state_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='owner_email_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='owner_postal_code_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='owner_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='owner_telephone_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='pm_property_id_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='postal_code_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='property_name_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='property_notes_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='recent_sale_date_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='release_date_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='site_eui_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='site_eui_weather_normalized_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='source_eui_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='source_eui_weather_normalized_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='space_alerts_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='state_province_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='super_organization',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='building_snapshots', blank=True, to='orgs.Organization', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='tax_lot_id_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='use_description_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='year_built_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingsnapshot',
            name='year_ending_source',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='+', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingattributevariant',
            name='building_snapshot',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='variants', blank=True, to='seed.BuildingSnapshot', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='buildingattributevariant',
            unique_together=set([('field_name', 'building_snapshot')]),
        ),
        migrations.AddField(
            model_name='attributeoption',
            name='building_variant',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='options', blank=True, to='seed.BuildingAttributeVariant', null=True),
            preserve_default=True,
        ),
    ]

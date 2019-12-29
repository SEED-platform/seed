# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
        ('orgs', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='BuildingImportRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('building_pk', models.CharField(max_length=40, null=True, blank=True)),
                ('was_in_database', models.BooleanField(default=False)),
                ('is_missing_from_import', models.BooleanField(default=False)),
                ('building_model_content_type', models.ForeignKey(on_delete=models.deletion.CASCADE, blank=True, to='contenttypes.ContentType', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DataCoercionMapping',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('source_string', models.TextField()),
                ('source_type', models.CharField(max_length=50)),
                ('destination_value', models.CharField(max_length=255, null=True, blank=True)),
                ('destination_type', models.CharField(max_length=255, null=True, blank=True)),
                ('is_mapped', models.BooleanField(default=False)),
                ('confidence', models.FloatField(default=0)),
                ('was_a_human_decision', models.BooleanField(default=False)),
                ('valid_destination_value', models.BooleanField(default=False)),
                ('active', models.BooleanField(default=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ImportFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('deleted', models.BooleanField(default=False)),
                ('file', models.FileField(max_length=500, null=True, upload_to=b'data_imports', blank=True)),
                ('export_file', models.FileField(null=True, upload_to=b'data_imports/exports', blank=True)),
                ('file_size_in_bytes', models.IntegerField(null=True, blank=True)),
                ('cached_first_row', models.TextField(null=True, blank=True)),
                ('cached_second_to_fifth_row', models.TextField(null=True, blank=True)),
                ('num_columns', models.IntegerField(null=True, blank=True)),
                ('num_rows', models.IntegerField(null=True, blank=True)),
                ('num_mapping_warnings', models.IntegerField(default=0)),
                ('num_mapping_errors', models.IntegerField(default=0)),
                ('mapping_error_messages', models.TextField(null=True, blank=True)),
                ('num_validation_errors', models.IntegerField(null=True, blank=True)),
                ('num_tasks_total', models.IntegerField(null=True, blank=True)),
                ('num_tasks_complete', models.IntegerField(null=True, blank=True)),
                ('num_coercion_errors', models.IntegerField(default=0, null=True, blank=True)),
                ('num_coercions_total', models.IntegerField(default=0, null=True, blank=True)),
                ('has_header_row', models.BooleanField(default=True)),
                ('raw_save_done', models.BooleanField(default=False)),
                ('raw_save_completion', models.IntegerField(null=True, blank=True)),
                ('mapping_done', models.BooleanField(default=False)),
                ('mapping_completion', models.IntegerField(null=True, blank=True)),
                ('matching_done', models.BooleanField(default=False)),
                ('matching_completion', models.IntegerField(null=True, blank=True)),
                ('source_type', models.CharField(max_length=63, null=True, blank=True)),
                ('source_program', models.CharField(max_length=80, blank=True)),
                ('source_program_version', models.CharField(max_length=40, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ImportRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('deleted', models.BooleanField(default=False)),
                ('name', models.CharField(default=b'Unnamed Dataset', max_length=255, null=True, verbose_name=b'Name Your Dataset', blank=True)),
                ('app', models.CharField(default=b'seed', help_text=b'The application (e.g. BPD or SEED) for this dataset', max_length=64, verbose_name=b'Destination App')),
                ('start_time', models.DateTimeField(null=True, blank=True)),
                ('finish_time', models.DateTimeField(null=True, blank=True)),
                ('created_at', models.DateTimeField(null=True, blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('notes', models.TextField(null=True, blank=True)),
                ('merge_analysis_done', models.BooleanField(default=False)),
                ('merge_analysis_active', models.BooleanField(default=False)),
                ('merge_analysis_queued', models.BooleanField(default=False)),
                ('premerge_analysis_done', models.BooleanField(default=False)),
                ('premerge_analysis_active', models.BooleanField(default=False)),
                ('premerge_analysis_queued', models.BooleanField(default=False)),
                ('matching_active', models.BooleanField(default=False)),
                ('matching_done', models.BooleanField(default=False)),
                ('is_imported_live', models.BooleanField(default=False)),
                ('keep_missing_buildings', models.BooleanField(default=True)),
                ('status', models.IntegerField(default=0, choices=[(0, b'Uploading'), (1, b'Machine Mapping'), (2, b'Needs Mapping'), (3, b'Machine Cleaning'), (4, b'Needs Cleaning'), (5, b'Ready to Merge'), (6, b'Merging'), (7, b'Merge Complete'), (8, b'Importing'), (9, b'Live'), (10, b'Unknown'), (11, b'Matching')])),
                ('import_completed_at', models.DateTimeField(null=True, blank=True)),
                ('merge_completed_at', models.DateTimeField(null=True, blank=True)),
                ('mcm_version', models.IntegerField(max_length=10, null=True, blank=True)),
                ('last_modified_by', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='modified_import_records', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('owner', models.ForeignKey(on_delete=models.deletion.CASCADE, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('super_organization', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='import_records', blank=True, to='orgs.Organization', null=True)),
            ],
            options={
                'ordering': ('-updated_at',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TableColumnMapping',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('app', models.CharField(default=b'', max_length=64)),
                ('source_string', models.TextField()),
                ('destination_model', models.CharField(max_length=255, null=True, blank=True)),
                ('destination_field', models.CharField(max_length=255, null=True, blank=True)),
                ('order', models.IntegerField(null=True, blank=True)),
                ('confidence', models.FloatField(default=0)),
                ('ignored', models.BooleanField(default=False)),
                ('was_a_human_decision', models.BooleanField(default=False)),
                ('error_message_text', models.TextField(null=True, blank=True)),
                ('active', models.BooleanField(default=True)),
                ('import_file', models.ForeignKey(on_delete=models.deletion.CASCADE, to='data_importer.ImportFile')),
            ],
            options={
                'ordering': ('order',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ValidationOutlier',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ValidationRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('passes', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RangeValidationRule',
            fields=[
                ('validationrule_ptr', models.OneToOneField(on_delete=models.deletion.CASCADE, parent_link=True, auto_created=True, primary_key=True, serialize=False, to='data_importer.ValidationRule')),
                ('max_value', models.FloatField(null=True, blank=True)),
                ('min_value', models.FloatField(null=True, blank=True)),
                ('limit_min', models.BooleanField(default=False)),
                ('limit_max', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=('data_importer.validationrule',),
        ),
        migrations.AddField(
            model_name='validationrule',
            name='table_column_mapping',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, to='data_importer.TableColumnMapping'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='validationoutlier',
            name='rule',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, to='data_importer.ValidationRule'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='importfile',
            name='import_record',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, to='data_importer.ImportRecord'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='datacoercionmapping',
            name='table_column_mapping',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, to='data_importer.TableColumnMapping'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingimportrecord',
            name='import_record',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, to='data_importer.ImportRecord'),
            preserve_default=True,
        ),
    ]

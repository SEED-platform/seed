"""
:copyright: (c) 2014 Building Energy Inc
"""
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ImportRecord'
        db.create_table(u'data_importer_importrecord', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('deleted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('name', self.gf('django.db.models.fields.CharField')(default='Unnamed Dataset', max_length=255, null=True, blank=True)),
            ('app', self.gf('django.db.models.fields.CharField')(default='seed', max_length=64)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['landing.SEEDUser'], null=True, blank=True)),
            ('start_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('finish_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('last_modified_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='modified_import_records', null=True, to=orm['landing.SEEDUser'])),
            ('notes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('merge_analysis_done', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('merge_analysis_active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('merge_analysis_queued', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('premerge_analysis_done', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('premerge_analysis_active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('premerge_analysis_queued', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('matching_active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('matching_done', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_imported_live', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('keep_missing_buildings', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('import_completed_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('merge_completed_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('mcm_version', self.gf('django.db.models.fields.IntegerField')(max_length=10, null=True, blank=True)),
        ))
        db.send_create_signal(u'data_importer', ['ImportRecord'])

        # Adding M2M table for field organization on 'ImportRecord'
        m2m_table_name = db.shorten_name(u'data_importer_importrecord_organization')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('importrecord', models.ForeignKey(orm[u'data_importer.importrecord'], null=False)),
            ('organization', models.ForeignKey(orm[u'organizations.organization'], null=False))
        ))
        db.create_unique(m2m_table_name, ['importrecord_id', 'organization_id'])

        # Adding model 'ImportFile'
        db.create_table(u'data_importer_importfile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('deleted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('import_record', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['data_importer.ImportRecord'])),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True)),
            ('export_file', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True)),
            ('file_size_in_bytes', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('cached_first_row', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('cached_second_to_fifth_row', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('num_columns', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('num_rows', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('num_mapping_warnings', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('num_mapping_errors', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('has_source_id', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('mapping_error_messages', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('num_validation_errors', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('num_tasks_total', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('num_tasks_complete', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('mapping_confidence', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('num_coercion_errors', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('num_coercions_total', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('has_header_row', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('mapping_active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('initial_mapping_done', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('coercion_mapping_done', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_espm', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'data_importer', ['ImportFile'])

        # Adding model 'TableColumnMapping'
        db.create_table(u'data_importer_tablecolumnmapping', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('app', self.gf('django.db.models.fields.CharField')(default='', max_length=64)),
            ('source_string', self.gf('django.db.models.fields.TextField')()),
            ('import_file', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['data_importer.ImportFile'])),
            ('destination_model', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('destination_field', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('order', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('confidence', self.gf('django.db.models.fields.FloatField')(default=0)),
            ('ignored', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('was_a_human_decision', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('error_message_text', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'data_importer', ['TableColumnMapping'])

        # Adding model 'DataCoercionMapping'
        db.create_table(u'data_importer_datacoercionmapping', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('table_column_mapping', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['data_importer.TableColumnMapping'])),
            ('source_string', self.gf('django.db.models.fields.TextField')()),
            ('source_type', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('destination_value', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('destination_type', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('is_mapped', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('confidence', self.gf('django.db.models.fields.FloatField')(default=0)),
            ('was_a_human_decision', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('valid_destination_value', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'data_importer', ['DataCoercionMapping'])

        # Adding model 'ValidationRule'
        db.create_table(u'data_importer_validationrule', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('table_column_mapping', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['data_importer.TableColumnMapping'])),
            ('passes', self.gf('django.db.models.fields.BooleanField')()),
        ))
        db.send_create_signal(u'data_importer', ['ValidationRule'])

        # Adding model 'RangeValidationRule'
        db.create_table(u'data_importer_rangevalidationrule', (
            (u'validationrule_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['data_importer.ValidationRule'], unique=True, primary_key=True)),
            ('max_value', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('min_value', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('limit_min', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('limit_max', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'data_importer', ['RangeValidationRule'])

        # Adding model 'ValidationOutlier'
        db.create_table(u'data_importer_validationoutlier', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('rule', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['data_importer.ValidationRule'])),
            ('value', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'data_importer', ['ValidationOutlier'])

        # Adding model 'BuildingImportRecord'
        db.create_table(u'data_importer_buildingimportrecord', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('import_record', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['data_importer.ImportRecord'])),
            ('building_model_content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True)),
            ('building_pk', self.gf('django.db.models.fields.CharField')(max_length=40, null=True, blank=True)),
            ('was_in_database', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_missing_from_import', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'data_importer', ['BuildingImportRecord'])


    def backwards(self, orm):
        # Deleting model 'ImportRecord'
        db.delete_table(u'data_importer_importrecord')

        # Removing M2M table for field organization on 'ImportRecord'
        db.delete_table(db.shorten_name(u'data_importer_importrecord_organization'))

        # Deleting model 'ImportFile'
        db.delete_table(u'data_importer_importfile')

        # Deleting model 'TableColumnMapping'
        db.delete_table(u'data_importer_tablecolumnmapping')

        # Deleting model 'DataCoercionMapping'
        db.delete_table(u'data_importer_datacoercionmapping')

        # Deleting model 'ValidationRule'
        db.delete_table(u'data_importer_validationrule')

        # Deleting model 'RangeValidationRule'
        db.delete_table(u'data_importer_rangevalidationrule')

        # Deleting model 'ValidationOutlier'
        db.delete_table(u'data_importer_validationoutlier')

        # Deleting model 'BuildingImportRecord'
        db.delete_table(u'data_importer_buildingimportrecord')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'data_importer.buildingimportrecord': {
            'Meta': {'object_name': 'BuildingImportRecord'},
            'building_model_content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'building_pk': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_record': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_importer.ImportRecord']"}),
            'is_missing_from_import': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'was_in_database': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'data_importer.datacoercionmapping': {
            'Meta': {'object_name': 'DataCoercionMapping'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'confidence': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'destination_type': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'destination_value': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_mapped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'source_string': ('django.db.models.fields.TextField', [], {}),
            'source_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'table_column_mapping': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_importer.TableColumnMapping']"}),
            'valid_destination_value': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'was_a_human_decision': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'data_importer.importfile': {
            'Meta': {'object_name': 'ImportFile'},
            'cached_first_row': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'cached_second_to_fifth_row': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'coercion_mapping_done': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'export_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'file_size_in_bytes': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'has_header_row': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'has_source_id': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_record': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_importer.ImportRecord']"}),
            'initial_mapping_done': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_espm': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'mapping_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'mapping_confidence': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'mapping_error_messages': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'num_coercion_errors': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'num_coercions_total': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'num_columns': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'num_mapping_errors': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_mapping_warnings': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_rows': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'num_tasks_complete': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'num_tasks_total': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'num_validation_errors': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'data_importer.importrecord': {
            'Meta': {'ordering': "('-updated_at',)", 'object_name': 'ImportRecord'},
            'app': ('django.db.models.fields.CharField', [], {'default': "'seed'", 'max_length': '64'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'finish_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_completed_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'is_imported_live': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'keep_missing_buildings': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modified_import_records'", 'null': 'True', 'to': u"orm['landing.SEEDUser']"}),
            'matching_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'matching_done': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'mcm_version': ('django.db.models.fields.IntegerField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'merge_analysis_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'merge_analysis_done': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'merge_analysis_queued': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'merge_completed_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'Unnamed Dataset'", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'organization': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['organizations.Organization']", 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['landing.SEEDUser']", 'null': 'True', 'blank': 'True'}),
            'premerge_analysis_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'premerge_analysis_done': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'premerge_analysis_queued': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'data_importer.rangevalidationrule': {
            'Meta': {'object_name': 'RangeValidationRule', '_ormbases': [u'data_importer.ValidationRule']},
            'limit_max': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'limit_min': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'max_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'min_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            u'validationrule_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['data_importer.ValidationRule']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'data_importer.tablecolumnmapping': {
            'Meta': {'ordering': "('order',)", 'object_name': 'TableColumnMapping'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'app': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '64'}),
            'confidence': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'destination_field': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'destination_model': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'error_message_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ignored': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'import_file': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_importer.ImportFile']"}),
            'order': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'source_string': ('django.db.models.fields.TextField', [], {}),
            'was_a_human_decision': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'data_importer.validationoutlier': {
            'Meta': {'object_name': 'ValidationOutlier'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_importer.ValidationRule']"}),
            'value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'data_importer.validationrule': {
            'Meta': {'object_name': 'ValidationRule'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passes': ('django.db.models.fields.BooleanField', [], {}),
            'table_column_mapping': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_importer.TableColumnMapping']"})
        },
        u'landing.seeduser': {
            'Meta': {'object_name': 'SEEDUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'default_custom_columns': ('djorm_pgjson.fields.JSONField', [], {'default': '{}'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'organizations.organization': {
            'Meta': {'ordering': "['name']", 'object_name': 'Organization'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'slug': ('django_extensions.db.fields.AutoSlugField', [], {'allow_duplicates': 'False', 'max_length': '200', 'separator': "u'-'", 'unique': 'True', 'populate_from': "'name'", 'overwrite': 'False'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['landing.SEEDUser']", 'through': u"orm['organizations.OrganizationUser']", 'symmetrical': 'False'})
        },
        u'organizations.organizationuser': {
            'Meta': {'ordering': "['organization', 'user']", 'unique_together': "(('user', 'organization'),)", 'object_name': 'OrganizationUser'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'organization_users'", 'to': u"orm['organizations.Organization']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'organization_users'", 'to': u"orm['landing.SEEDUser']"})
        }
    }

    complete_apps = ['data_importer']

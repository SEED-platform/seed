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
        # Adding field 'BuildingSnapshot.lot_number'
        db.add_column(u'seed_buildingsnapshot', 'lot_number',
                      self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True),
                      keep_default=False)

        # Adding field 'BuildingSnapshot.lot_number_source'
        db.add_column(u'seed_buildingsnapshot', 'lot_number_source',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['seed.BuildingSnapshot']),
                      keep_default=False)

        # Adding field 'BuildingSnapshot.block_number'
        db.add_column(u'seed_buildingsnapshot', 'block_number',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['seed.BuildingSnapshot']),
                      keep_default=False)

        # Adding field 'BuildingSnapshot.owner_address'
        db.add_column(u'seed_buildingsnapshot', 'owner_address',
                      self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True),
                      keep_default=False)

        # Adding field 'BuildingSnapshot.owner_address_source'
        db.add_column(u'seed_buildingsnapshot', 'owner_address_source',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['seed.BuildingSnapshot']),
                      keep_default=False)

        # Adding field 'BuildingSnapshot.owner_city_state'
        db.add_column(u'seed_buildingsnapshot', 'owner_city_state',
                      self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True),
                      keep_default=False)

        # Adding field 'BuildingSnapshot.owner_city_state_source'
        db.add_column(u'seed_buildingsnapshot', 'owner_city_state_source',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['seed.BuildingSnapshot']),
                      keep_default=False)

        # Adding field 'BuildingSnapshot.owner_postal_code'
        db.add_column(u'seed_buildingsnapshot', 'owner_postal_code',
                      self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True),
                      keep_default=False)

        # Adding field 'BuildingSnapshot.owner_postal_code_source'
        db.add_column(u'seed_buildingsnapshot', 'owner_postal_code_source',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['seed.BuildingSnapshot']),
                      keep_default=False)

        # Adding field 'BuildingSnapshot.use_description'
        db.add_column(u'seed_buildingsnapshot', 'use_description',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'BuildingSnapshot.use_description_source'
        db.add_column(u'seed_buildingsnapshot', 'use_description_source',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['seed.BuildingSnapshot']),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'BuildingSnapshot.lot_number'
        db.delete_column(u'seed_buildingsnapshot', 'lot_number')

        # Deleting field 'BuildingSnapshot.lot_number_source'
        db.delete_column(u'seed_buildingsnapshot', 'lot_number_source_id')

        # Deleting field 'BuildingSnapshot.block_number'
        db.delete_column(u'seed_buildingsnapshot', 'block_number_id')

        # Deleting field 'BuildingSnapshot.owner_address'
        db.delete_column(u'seed_buildingsnapshot', 'owner_address')

        # Deleting field 'BuildingSnapshot.owner_address_source'
        db.delete_column(u'seed_buildingsnapshot', 'owner_address_source_id')

        # Deleting field 'BuildingSnapshot.owner_city_state'
        db.delete_column(u'seed_buildingsnapshot', 'owner_city_state')

        # Deleting field 'BuildingSnapshot.owner_city_state_source'
        db.delete_column(u'seed_buildingsnapshot', 'owner_city_state_source_id')

        # Deleting field 'BuildingSnapshot.owner_postal_code'
        db.delete_column(u'seed_buildingsnapshot', 'owner_postal_code')

        # Deleting field 'BuildingSnapshot.owner_postal_code_source'
        db.delete_column(u'seed_buildingsnapshot', 'owner_postal_code_source_id')

        # Deleting field 'BuildingSnapshot.use_description'
        db.delete_column(u'seed_buildingsnapshot', 'use_description')

        # Deleting field 'BuildingSnapshot.use_description_source'
        db.delete_column(u'seed_buildingsnapshot', 'use_description_source_id')


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
            'num_validation_errors': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'source_type': ('django.db.models.fields.CharField', [], {'max_length': '63', 'null': 'True', 'blank': 'True'})
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
        },
        u'seed.attributeoption': {
            'Meta': {'object_name': 'AttributeOption'},
            'building_variant': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'options'", 'null': 'True', 'to': u"orm['seed.BuildingAttributeVariant']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'value_source': ('django.db.models.fields.IntegerField', [], {})
        },
        u'seed.buildingattributevariant': {
            'Meta': {'unique_together': "(('field_name', 'building_snapshot'),)", 'object_name': 'BuildingAttributeVariant'},
            'building_snapshot': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'variants'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'field_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'seed.buildingsnapshot': {
            'Meta': {'ordering': "('-modified', '-created')", 'object_name': 'BuildingSnapshot'},
            'address_line_1': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'address_line_1_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'address_line_2': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'address_line_2_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'best_guess_canonical_building': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'best_guess'", 'null': 'True', 'to': u"orm['seed.CanonicalBuilding']"}),
            'best_guess_confidence': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'block_number': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'building_certification': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'building_certification_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'building_count': ('django.db.models.fields.IntegerField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'building_count_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'canonical_building': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['seed.CanonicalBuilding']", 'null': 'True', 'blank': 'True'}),
            'canonical_for_ds': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['data_importer.ImportRecord']"}),
            'children': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'parents'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['seed.BuildingSnapshot']"}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'city_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'conditioned_floor_area': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'conditioned_floor_area_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'confidence': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'custom_id_1': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'custom_id_1_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'district': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'district_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'energy_alerts': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'energy_alerts_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'energy_score': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'energy_score_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'extra_data': ('djorm_pgjson.fields.JSONField', [], {'default': '{}'}),
            'extra_data_sources': ('djorm_pgjson.fields.JSONField', [], {'default': '{}'}),
            'generation_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'generation_date_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'gross_floor_area': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'gross_floor_area_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_file': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_importer.ImportFile']", 'null': 'True', 'blank': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['landing.SEEDUser']", 'null': 'True', 'blank': 'True'}),
            'lot_number': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'lot_number_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'match_type': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'occupied_floor_area': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'occupied_floor_area_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'owner': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'owner_address': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'owner_address_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'owner_city_state': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'owner_city_state_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'owner_email': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'owner_email_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'owner_postal_code': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'owner_postal_code_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'owner_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'owner_telephone': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'owner_telephone_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'pm_property_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'pm_property_id_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'postal_code': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'postal_code_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'property_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'property_name_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'property_notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'property_notes_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'recent_sale_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'recent_sale_date_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'release_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'release_date_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'seed_org': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['organizations.Organization']", 'null': 'True', 'blank': 'True'}),
            'site_eui': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'site_eui_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'site_eui_weather_normalized': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'site_eui_weather_normalized_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'source_eui': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'source_eui_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'source_eui_weather_normalized': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'source_eui_weather_normalized_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'source_type': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'space_alerts': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'space_alerts_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'state_province': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'state_province_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'tax_lot_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'tax_lot_id_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'use_description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'use_description_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'year_built': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'year_built_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'year_ending': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'year_ending_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"})
        },
        u'seed.canonicalbuilding': {
            'Meta': {'object_name': 'CanonicalBuilding'},
            'canonical_snapshot': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['seed.BuildingSnapshot']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'seed.columnmapping': {
            'Meta': {'unique_together': "(('organization', 'column_raw'),)", 'object_name': 'ColumnMapping'},
            'column_mapped': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'column_raw': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['organizations.Organization']", 'null': 'True', 'blank': 'True'}),
            'source_type': ('django.db.models.fields.IntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['landing.SEEDUser']", 'null': 'True', 'blank': 'True'})
        },
        u'seed.compliance': {
            'Meta': {'ordering': "('-modified', '-created')", 'object_name': 'Compliance'},
            'compliance_type': ('django.db.models.fields.CharField', [], {'default': "'Benchmarking'", 'max_length': '30'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'deadline_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['seed.Project']"}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'})
        },
        u'seed.custombuildingheaders': {
            'Meta': {'object_name': 'CustomBuildingHeaders'},
            'building_headers': ('djorm_pgjson.fields.JSONField', [], {'default': '{}'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['organizations.Organization']"})
        },
        u'seed.project': {
            'Meta': {'ordering': "('-modified', '-created')", 'object_name': 'Project'},
            'building_snapshots': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['seed.BuildingSnapshot']", 'null': 'True', 'through': u"orm['seed.ProjectBuilding']", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_modified_user'", 'null': 'True', 'to': u"orm['landing.SEEDUser']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['organizations.Organization']", 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['landing.SEEDUser']", 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': "'name'", 'unique_with': '()'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        u'seed.projectbuilding': {
            'Meta': {'ordering': "['project', 'building_snapshot']", 'unique_together': "(('building_snapshot', 'project'),)", 'object_name': 'ProjectBuilding'},
            'approved_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'approver': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['landing.SEEDUser']", 'null': 'True', 'blank': 'True'}),
            'building_snapshot': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project_building_snapshots'", 'to': u"orm['seed.BuildingSnapshot']"}),
            'compliant': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project_building_snapshots'", 'to': u"orm['seed.Project']"}),
            'status_label': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['seed.StatusLabel']", 'null': 'True', 'blank': 'True'})
        },
        u'seed.statuslabel': {
            'Meta': {'ordering': "['-name']", 'unique_together': "(('name', 'organization'),)", 'object_name': 'StatusLabel'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'green'", 'max_length': '30'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['organizations.Organization']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['seed']

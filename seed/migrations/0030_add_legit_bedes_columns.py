# -*- coding: utf-8 -*-
import re

from south.v2 import DataMigration
from seed.data import bedes
from seed.utils import mapping as m_utils
from seed.models import (
    STRING,
    DECIMAL,
    FLOAT,
    DATE,
    DATETIME
)

def unit_enum(s):

    dispatch_table = {
        'float': FLOAT,
        'string': STRING,
        'data': DATE,
        'datetime': DATETIME,
        'decimal': DECIMAL,
    }

    s = s.lower()

    return dispatch_table.get(s, STRING)


def name_and_unit_desc(col_str):
    """
    Pulls the human readable description of the units out of
    the column name string. Returns the column name without
    the unit information and a string describing the units.
    """

    regex = r'\(([^\)\(]*)\)\s?$'
    match = re.search(regex, col_str)

    if match:
        unit_desc = match.groups()[0]
        col_name = re.sub(regex, '', col_str).rstrip()
        return (col_name, unit_desc)

    else:
        return (col_str, '')


class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Don't use "from appname.models import ModelName".
        # Use orm.ModelName to refer to models in this application,
        # and orm['appname.ModelName'] for models in other applications.

        schema, _ = orm['seed.schema'].objects.get_or_create(
            name='BEDES',
        )

        mappable_columns = m_utils.get_mappable_columns()

        for raw_name, unit_type_str in bedes.schema.iteritems():
            unit = None

            col_name, unit_desc = name_and_unit_desc(raw_name)
            unit_type = unit_enum(unit_type_str)

            unit, _ = orm['seed.unit'].objects.get_or_create(
                unit_name=unit_desc,
                unit_type=unit_type,
            )

            is_extra_data = col_name not in mappable_columns

            new_col = orm['seed.column'].objects.create(
                column_name=col_name,
                unit=unit,
                is_extra_data=is_extra_data
            )

            schema.columns.add(new_col)


    def backwards(self, orm):
        "Write your backwards methods here."

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
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'export_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'file_size_in_bytes': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'has_header_row': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_record': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_importer.ImportRecord']"}),
            'mapping_completion': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mapping_done': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'mapping_error_messages': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'matching_completion': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'matching_done': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'num_coercion_errors': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'num_coercions_total': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'num_columns': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'num_mapping_errors': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_mapping_warnings': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_rows': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'num_tasks_complete': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'num_tasks_total': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'num_validation_errors': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'raw_save_completion': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'raw_save_done': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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
            'super_organization': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'import_records'", 'null': 'True', 'to': u"orm['orgs.Organization']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'landing.seeduser': {
            'Meta': {'object_name': 'SEEDUser'},
            'api_key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128', 'db_index': 'True', 'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'default_custom_columns': ('djorm_pgjson.fields.JSONField', [], {'default': '{}'}),
            'default_organization': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'default_users'", 'null': 'True', 'to': u"orm['orgs.Organization']"}),
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
            'show_shared_buildings': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75'})
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
        u'orgs.organization': {
            'Meta': {'ordering': "['name']", 'object_name': 'Organization'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'parent_org': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'child_orgs'", 'null': 'True', 'to': u"orm['orgs.Organization']"}),
            'query_threshold': ('django.db.models.fields.IntegerField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'orgs'", 'symmetrical': 'False', 'through': u"orm['orgs.OrganizationUser']", 'to': u"orm['landing.SEEDUser']"})
        },
        u'orgs.organizationuser': {
            'Meta': {'ordering': "['organization', '-role_level']", 'object_name': 'OrganizationUser'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['orgs.Organization']"}),
            'role_level': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '12'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['landing.SEEDUser']"})
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
            'address_line_1': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'address_line_1_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'address_line_2': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'address_line_2_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'best_guess_canonical_building': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'best_guess'", 'null': 'True', 'to': u"orm['seed.CanonicalBuilding']"}),
            'best_guess_confidence': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'block_number': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'block_number_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'building_certification': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'building_certification_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'building_count': ('django.db.models.fields.IntegerField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'building_count_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'canonical_building': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['seed.CanonicalBuilding']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'canonical_for_ds': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['data_importer.ImportRecord']"}),
            'children': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'parents'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['seed.BuildingSnapshot']"}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'city_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'conditioned_floor_area': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'conditioned_floor_area_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'confidence': ('django.db.models.fields.FloatField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'custom_id_1': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
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
            'match_type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
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
            'pm_property_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
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
            'site_eui': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'site_eui_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'site_eui_weather_normalized': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'site_eui_weather_normalized_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'source_eui': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'source_eui_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'source_eui_weather_normalized': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'source_eui_weather_normalized_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'source_type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'space_alerts': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'space_alerts_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'state_province': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'state_province_source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['seed.BuildingSnapshot']"}),
            'super_organization': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'building_snapshots'", 'null': 'True', 'to': u"orm['orgs.Organization']"}),
            'tax_lot_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
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
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'canonical_snapshot': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['seed.BuildingSnapshot']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'seed.column': {
            'Meta': {'unique_together': "(('organization', 'column_name', 'is_extra_data'),)", 'object_name': 'Column'},
            'column_name': ('django.db.models.fields.CharField', [], {'max_length': '512', 'db_index': 'True'}),
            'enum': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['seed.Enum']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_extra_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['orgs.Organization']", 'null': 'True', 'blank': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['seed.Unit']", 'null': 'True', 'blank': 'True'})
        },
        u'seed.columnmapping': {
            'Meta': {'object_name': 'ColumnMapping'},
            'column_mapped': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'mapped_mappings'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['seed.Column']"}),
            'column_raw': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'raw_mappings'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['seed.Column']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'source_type': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'super_organization': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'column_mappings'", 'null': 'True', 'to': u"orm['orgs.Organization']"}),
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
            'super_organization': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'custom_headers'", 'null': 'True', 'to': u"orm['orgs.Organization']"})
        },
        u'seed.enum': {
            'Meta': {'object_name': 'Enum'},
            'enum_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'enum_values': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'values'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['seed.EnumValue']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'seed.enumvalue': {
            'Meta': {'object_name': 'EnumValue'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value_name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'seed.meter': {
            'Meta': {'object_name': 'Meter'},
            'building_snapshot': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'meters'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['seed.BuildingSnapshot']"}),
            'energy_type': ('django.db.models.fields.IntegerField', [], {'max_length': '3'}),
            'energy_units': ('django.db.models.fields.IntegerField', [], {'max_length': '3'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
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
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['landing.SEEDUser']", 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': "'name'", 'unique_with': '()'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'super_organization': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'projects'", 'null': 'True', 'to': u"orm['orgs.Organization']"})
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
        u'seed.schema': {
            'Meta': {'object_name': 'Schema'},
            'columns': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'schemas'", 'symmetrical': 'False', 'to': u"orm['seed.Column']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'schemas'", 'null': 'True', 'to': u"orm['orgs.Organization']"})
        },
        u'seed.statuslabel': {
            'Meta': {'ordering': "['-name']", 'unique_together': "(('name', 'super_organization'),)", 'object_name': 'StatusLabel'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'green'", 'max_length': '30'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'super_organization': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'status_labels'", 'null': 'True', 'to': u"orm['orgs.Organization']"})
        },
        u'seed.timeseries': {
            'Meta': {'object_name': 'TimeSeries'},
            'begin_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'cost': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '11', 'decimal_places': '4'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meter': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'timeseries_data'", 'null': 'True', 'to': u"orm['seed.Meter']"}),
            'reading': ('django.db.models.fields.FloatField', [], {'null': 'True'})
        },
        u'seed.unit': {
            'Meta': {'object_name': 'Unit'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'unit_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unit_type': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        }
    }

    complete_apps = ['seed']
    symmetrical = True

# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'AuditLog'
        db.create_table(u'audit_logs_auditlog', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['landing.SEEDUser'])),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True)),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('audit_type', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('action', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=128, null=True, blank=True)),
            ('action_response', self.gf('djorm_pgjson.fields.JSONField')(default={})),
            ('action_note', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('organization', self.gf('django.db.models.fields.related.ForeignKey')(related_name='audit_logs', to=orm['orgs.Organization'])),
        ))
        db.send_create_signal(u'audit_logs', ['AuditLog'])


    def backwards(self, orm):
        # Deleting model 'AuditLog'
        db.delete_table(u'audit_logs_auditlog')


    models = {
        u'audit_logs.auditlog': {
            'Meta': {'ordering': "('-modified', '-created')", 'object_name': 'AuditLog'},
            'action': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'action_note': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'action_response': ('djorm_pgjson.fields.JSONField', [], {'default': '{}'}),
            'audit_type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'audit_logs'", 'to': u"orm['orgs.Organization']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['landing.SEEDUser']"})
        },
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
        }
    }

    complete_apps = ['audit_logs']

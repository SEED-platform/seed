# !/usr/bin/env python
# encoding: utf-8
from rest_framework.schemas import AutoSchema
import coreapi


class AutoSchemaHelper(AutoSchema):
    def __init__(self):
        super().__init__()

    def base_field(self, name, location, required, type, description):
        """
        Created to avoid needing to directly access coreapi within ViewSets.
        Ideally, the cases below will be used instead of this one.
        """
        return coreapi.Field(
            name,
            location=location,
            required=required,
            type=type,
            description=description
        )

    def org_id_field(self, location='query', required=True, type='integer', description='Organization ID'):
        return coreapi.Field(
            'organization_id',
            location=location,
            required=required,
            type=type,
            description=description
        )

    def path_id_field(self, description):
        return coreapi.Field(
            "id",  # matches reference name in uri path
            location='path',
            required=True,
            type='integer',
            description=description
        )

    def body_field(self, required, description):
        return coreapi.Field(
            'body',
            location='body',
            required=required,
            type='object',
            description=description
        )

    def form_field(self, name, required, description):
        return coreapi.Field(
            name,
            location='form',
            required=required,
            type='object',
            description=description
        )

    def test_field_options(self):
        return [
            coreapi.Field('remove_label_ids', location='form', required=False, type='array'),
            coreapi.Field('inventory_ids', location='form', required=False, type='array', description="This is what the description looks like for an 'array'."),
            coreapi.Field('string test', location='form', required=False, type='string'),
            coreapi.Field('integer test', location='form', required=False, type='integer'),
            coreapi.Field('boolean test', location='form', required=False, type='boolean'),
            coreapi.Field('json test', location='form', required=False, type='json'),
            coreapi.Field('list test', location='form', required=False, type='list'),
            coreapi.Field('dict test', location='form', required=False, type='dict'),
            coreapi.Field('object test', location='form', required=False, type='object'),
            coreapi.Field('integers test', location='form', required=False, type='integers'),
            coreapi.Field('strings test', location='form', required=False, type='strings'),
            coreapi.Field('objects test', location='form', required=False, type='objects'),
            coreapi.Field('organization_id', location='query', required=True, type='integer'),
            coreapi.Field('string query test', location='query', required=True, type='string', description="Here's a query description"),
            coreapi.Field('boolean query test', location='query', required=True, type='boolean'),
            coreapi.Field('json query test', location='query', required=True, type='json'),
            coreapi.Field('object query test', location='query', required=True, type='object'),
            coreapi.Field('array query test', location='query', required=True, type='array'),
        ]

    def get_path_fields(self, path, method):
        default_fields = AutoSchema.get_path_fields(self, path, method)
        return self.path_fields.get((method, self.view.action), default_fields)

    def get_manual_fields(self, path, method):
        default_fields = AutoSchema.get_manual_fields(self, path, method)
        return self.manual_fields.get((method, self.view.action), default_fields)

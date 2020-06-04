# !/usr/bin/env python
# encoding: utf-8
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg import openapi


class AutoSchemaHelper(SwaggerAutoSchema):
    # overrides the serialization of existing endpoints
    overwrite_params = []

    # Used to easily build out example values displayed on Swagger page.
    body_parameter_formats = {
        'integer_array': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_INTEGER)
        ),
        'string': openapi.Schema(type=openapi.TYPE_STRING),
        'boolean': openapi.Schema(type=openapi.TYPE_BOOLEAN),
        'string_array': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING)
        )
    }

    @staticmethod
    def base_field(name, location_attr, description, required, type):
        """
        Created to avoid needing to directly access openapi within ViewSets.
        Ideally, the cases below will be used instead of this one.
        """
        return openapi.Parameter(
            name,
            getattr(openapi, location_attr),
            description=description,
            required=required,
            type=type
        )

    @staticmethod
    def org_id_field(required=True):
        return openapi.Parameter(
            'organization_id',
            openapi.IN_QUERY,
            description='Organization ID',
            required=required,
            type=openapi.TYPE_INTEGER
        )

    @staticmethod
    def query_integer_field(name, required, description):
        return openapi.Parameter(
            name,
            openapi.IN_QUERY,
            description=description,
            required=True,
            type=openapi.TYPE_INTEGER
        )

    @staticmethod
    def query_string_field(name, required, description):
        return openapi.Parameter(
            name,
            openapi.IN_QUERY,
            description=description,
            required=required,
            type=openapi.TYPE_STRING
        )

    @staticmethod
    def query_boolean_field(name, required, description):
        return openapi.Parameter(
            name,
            openapi.IN_QUERY,
            description=description,
            required=required,
            type=openapi.TYPE_BOOLEAN
        )

    @staticmethod
    def path_id_field(description):
        return openapi.Parameter(
            'id',
            openapi.IN_PATH,
            description=description,
            required=True,
            type=openapi.TYPE_INTEGER
        )

    @classmethod
    def body_field(cls, required, description, name='body', params_to_formats={}):
        return openapi.Parameter(
            name,
            openapi.IN_BODY,
            description=description,
            required=required,
            schema=cls._build_body_schema(params_to_formats)
        )

    @classmethod
    def _build_body_schema(cls, params_to_formats):
        return openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                k: cls.body_parameter_formats.get(format_name, "")
                for k, format_name
                in params_to_formats.items()
            }
        )

    def add_manual_parameters(self, parameters):
        manual_params = self.manual_fields.get((self.method, self.view.action), [])

        if (self.method, self.view.action) in self.overwrite_params:
            return manual_params
        # I think this should add to existing parameters, but haven't been able to confirm.
        return parameters + manual_params

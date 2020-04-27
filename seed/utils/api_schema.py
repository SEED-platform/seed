# !/usr/bin/env python
# encoding: utf-8
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg import openapi


class AutoSchemaHelper(SwaggerAutoSchema):

    # Used to easily build out example values displayed on Swagger page.
    body_parameter_formats = {
        'interger_list': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_INTEGER)
        )
    }

    def base_field(self, name, location_attr, description, required, type):
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

    def org_id_field(self):
        return openapi.Parameter(
            'organization_id',
            openapi.IN_QUERY,
            description='Organization ID',
            required=True,
            type=openapi.TYPE_INTEGER
        )

    def query_integer_field(self, name, required, description):
        return openapi.Parameter(
            name,
            openapi.IN_QUERY,
            description=description,
            required=True,
            type=openapi.TYPE_INTEGER
        )

    def path_id_field(self, description):
        return openapi.Parameter(
            'id',
            openapi.IN_PATH,
            description=description,
            required=True,
            type=openapi.TYPE_INTEGER
        )

    def body_field(self, required, description, name='body', params_to_formats={}):
        return openapi.Parameter(
            name,
            openapi.IN_BODY,
            description=description,
            required=required,
            schema=self._build_body_schema(params_to_formats)
        )

    def _build_body_schema(self, params_to_formats):
        return openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                k: self.body_parameter_formats.get(format_name, "")
                for k, format_name
                in params_to_formats.items()
            }
        )

    def add_manual_parameters(self, parameters):
        manual_params = self.manual_fields.get((self.method, self.view.action), [])

        # I think this should add to existing parameters, but haven't been able to confirm.
        return parameters + manual_params

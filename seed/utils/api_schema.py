# !/usr/bin/env python
# encoding: utf-8
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


class AutoSchemaHelper(SwaggerAutoSchema):
    # overrides the serialization of existing endpoints
    overwrite_params = []

    # Used to easily build out example values displayed on Swagger page.
    openapi_types = {
        'string': openapi.TYPE_STRING,
        'boolean': openapi.TYPE_BOOLEAN,
        'integer': openapi.TYPE_INTEGER,
    }

    @classmethod
    def _openapi_type(cls, type_name):
        """returns an openapi type

        :param type_name: str (e.g. 'string', 'boolean', 'integer')
        :return: openapi.TYPE_*
        """
        if type_name not in cls.openapi_types:
            raise Exception(f'Invalid type "{type_name}"; expected one of {cls.openapi_types.keys()}')
        return cls.openapi_types[type_name]

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
            type=getattr(openapi, type)
        )

    @staticmethod
    def query_org_id_field(required=True, description="Organization ID"):
        return openapi.Parameter(
            'organization_id',
            openapi.IN_QUERY,
            description=description,
            required=required,
            type=openapi.TYPE_INTEGER
        )

    @staticmethod
    def query_integer_field(name, required, description):
        return openapi.Parameter(
            name,
            openapi.IN_QUERY,
            description=description,
            required=required,
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
    def form_string_field(name, required, description):
        return openapi.Parameter(
            name,
            openapi.IN_FORM,
            description=description,
            required=required,
            type=openapi.TYPE_STRING
        )

    @staticmethod
    def form_integer_field(name, required, description):
        return openapi.Parameter(
            name,
            openapi.IN_FORM,
            description=description,
            required=required,
            type=openapi.TYPE_INTEGER
        )

    @staticmethod
    def upload_file_field(name, required, description):
        return openapi.Parameter(
            name,
            openapi.IN_FORM,
            description=description,
            required=required,
            type=openapi.TYPE_FILE
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
            schema=cls.schema_factory(params_to_formats)
        )

    @classmethod
    def schema_factory(cls, obj, **kwargs):
        """Translates an object into an openapi Schema

        This can handle nested objects (lists, dicts), and "types" defined as strings
        For example:
        {
            'hello': ['string'],
            'world': 'integer',
            'fruits': {
                'orange': 'boolean',
                'apple': 'boolean'
            }
        }

        :param obj: str, list, dict[str, obj]
        :return: drf_yasg.openapi.Schema
        """
        if type(obj) is str:
            openapi_type = cls._openapi_type(obj)
            return openapi.Schema(
                type=openapi_type,
                **kwargs
            )

        if type(obj) is list:
            if len(obj) != 1:
                raise Exception('List types must have exactly one element to specify the schema of `items`')
            return openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=cls.schema_factory(obj[0]),
                **kwargs
            )

        if type(obj) is dict:
            return openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    k: cls.schema_factory(sub_obj)
                    for k, sub_obj
                    in obj.items()
                },
                **kwargs
            )

        raise Exception(f'Unhandled type "{type(obj)}" for {obj}')

    def add_manual_parameters(self, parameters):
        manual_params = self.manual_fields.get((self.method, self.view.action), [])

        if (self.method, self.view.action) in self.overwrite_params:
            return manual_params
        # I think this should add to existing parameters, but haven't been able to confirm.
        return parameters + manual_params


# this is a commonly used swagger decorator so moved here for DRYness
swagger_auto_schema_org_query_param = swagger_auto_schema(
    manual_parameters=[AutoSchemaHelper.query_org_id_field()]
)

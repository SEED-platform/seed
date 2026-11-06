"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

OpenAPI (drf-spectacular) helpers shared by the SEED API views.
"""

import copy

from django.contrib.gis.db.models import GeometryField
from drf_spectacular.authentication import SessionScheme
from drf_spectacular.extensions import OpenApiAuthenticationExtension, OpenApiSerializerFieldExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import force_instance, get_lib_doc_excludes, get_override, is_serializer
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers

from seed.renderers import SEEDJSONRenderer


class EmptySerializer(serializers.Serializer):
    pass


class AutoSchemaHelper:
    """Shorthand builders for the parameters and raw schemas passed to ``@extend_schema``."""

    # Raw OpenAPI schemas for the type names accepted by `schema_factory`
    openapi_types = {
        "string": {"type": "string"},
        "boolean": {"type": "boolean"},
        "integer": {"type": "integer"},
        "number": {"type": "number"},
        "object": {"type": "object"},
        "date": {"type": "string", "format": "date"},
        "datetime": {"type": "string", "format": "date-time"},
        "file": {"type": "string", "format": "binary"},
    }

    @staticmethod
    def query_org_id_field(required=True, description="Organization ID"):
        return OpenApiParameter("organization_id", OpenApiTypes.INT, OpenApiParameter.QUERY, required=required, description=description)

    @staticmethod
    def query_integer_field(name, required, description):
        return OpenApiParameter(name, OpenApiTypes.INT, OpenApiParameter.QUERY, required=required, description=description)

    @staticmethod
    def query_number_field(name, required, description):
        return OpenApiParameter(name, OpenApiTypes.NUMBER, OpenApiParameter.QUERY, required=required, description=description)

    @staticmethod
    def query_string_field(name, required, description):
        return OpenApiParameter(name, OpenApiTypes.STR, OpenApiParameter.QUERY, required=required, description=description)

    @staticmethod
    def query_boolean_field(name, required, description):
        return OpenApiParameter(name, OpenApiTypes.BOOL, OpenApiParameter.QUERY, required=required, description=description)

    @staticmethod
    def query_datetime_field(name, required, description):
        return OpenApiParameter(name, OpenApiTypes.DATETIME, OpenApiParameter.QUERY, required=required, description=description)

    @staticmethod
    def query_enum_field(name, description, enum, required=True):
        return OpenApiParameter(name, OpenApiTypes.STR, OpenApiParameter.QUERY, required=required, description=description, enum=enum)

    @classmethod
    def query_array_field(cls, name, required, description, item_type="integer"):
        """A repeated query parameter (e.g., `?id=1&id=2`) of `schema_factory` type `item_type`"""
        return OpenApiParameter(name, cls.schema_factory([item_type]), OpenApiParameter.QUERY, required=required, description=description)

    @staticmethod
    def path_id_field(description, name="id"):
        return OpenApiParameter(name, OpenApiTypes.INT, OpenApiParameter.PATH, description=description)

    @staticmethod
    def path_string_field(name, description):
        return OpenApiParameter(name, OpenApiTypes.STR, OpenApiParameter.PATH, description=description)

    @staticmethod
    def path_enum_field(name, description, enum):
        return OpenApiParameter(name, OpenApiTypes.STR, OpenApiParameter.PATH, description=description, enum=enum)

    @classmethod
    def schema_factory(cls, obj, **kwargs):
        """Translates an object into a raw OpenAPI schema

        This can handle nested objects (lists, dicts, enum tuples), and "types" defined as strings
        (see `openapi_types`). Any kwargs (e.g., `required`, `description`, `example`) are added
        to the outermost schema. For example:
        {
            'hello': ['string'],
            'world': 'integer',
            'fruits': {
                'orange': 'boolean',
                'apple': 'boolean'
            }
        }

        :param obj: str, list, tuple, dict[str, obj]
        :return: dict, an OpenAPI schema object
        """
        if isinstance(obj, tuple):
            schema = {"type": "string", "enum": list(dict.fromkeys(t[1] for t in obj))}
        elif isinstance(obj, str):
            if obj not in cls.openapi_types:
                raise ValueError(f'Invalid type "{obj}"; expected one of {cls.openapi_types.keys()}')
            schema = copy.deepcopy(cls.openapi_types[obj])
        elif isinstance(obj, list):
            if len(obj) != 1:
                raise ValueError("List types must have exactly one element to specify the schema of `items`")
            schema = {"type": "array", "items": cls.schema_factory(obj[0])}
        elif isinstance(obj, dict):
            schema = {"type": "object", "properties": {k: cls.schema_factory(sub_obj) for k, sub_obj in obj.items()}}
        else:
            raise TypeError(f'Unhandled type "{type(obj)}" for {obj}')

        return {**schema, **kwargs}

    @classmethod
    def json_body(cls, obj, **kwargs):
        """A JSON request body described by `schema_factory`, for `@extend_schema(request=...)`"""
        return {"application/json": cls.schema_factory(obj, **kwargs)}

    @classmethod
    def multipart_body(cls, fields, required=None, description=None):
        """A multipart/form-data request body (e.g., file uploads), for `@extend_schema(request=...)`

        :param fields: dict[str, obj], form field names to `schema_factory` types (use 'file' for uploads)
        :param required: list[str], names of the required form fields
        """
        schema = cls.schema_factory(fields)
        if required:
            schema["required"] = list(required)
        if description:
            schema["description"] = description
        return {"multipart/form-data": schema}


# Commonly used decorator for endpoints that take the organization ID as a query parameter
extend_schema_org_query_param = extend_schema(parameters=[AutoSchemaHelper.query_org_id_field()])

# The state of a background task (see `seed.lib.progress_data.ProgressData`)
PROGRESS_DATA_SCHEMA = AutoSchemaHelper.schema_factory(
    {
        "status": "string",
        "status_message": "string",
        "progress": "number",
        "progress_key": "string",
        "unique_id": "string",
        "func_name": "string",
        "total": "integer",
        "message": "string",
        "stacktrace": "string",
        "summary": "object",
    },
    description="Background task progress, which can be polled with `GET /api/v3/progress/{progress_key}/`",
)


class UnenvelopedResponse(OpenApiResponse):
    """A serializer response returned directly (e.g., `JsonResponse(serializer.data)`), bypassing the
    `SEEDJSONRenderer` envelope that `SEEDAutoSchema` otherwise adds"""


def get_seed_lib_doc_excludes():
    """Base classes whose docstrings are not used as operation descriptions"""
    from seed.utils import viewsets

    return [
        *get_lib_doc_excludes(),
        *(cls for cls in vars(viewsets).values() if isinstance(cls, type) and cls.__module__ == viewsets.__name__),
    ]


def _seed_envelope(schema, data_name):
    """Describe a response body as `SEEDJSONRenderer` renders it (pagination metadata is moved out of the body)"""
    properties = schema.get("properties", {}) if schema.get("type") == "object" else {}
    envelope = {"status": {"type": "string", "enum": ["success"]}}
    if "results" in properties:
        envelope[data_name] = properties["results"]
        envelope["pagination"] = {"type": "object", "properties": {k: v for k, v in properties.items() if k != "results"}}
    else:
        envelope[data_name] = schema
    return {"type": "object", "properties": envelope, "required": list(envelope)}


class _SEEDEnvelopePaginator:
    """Proxies a paginator so that its paginated response schema includes the SEED response envelope"""

    def __init__(self, paginator, data_name):
        self._paginator = paginator
        self._data_name = data_name

    def __getattr__(self, name):
        return getattr(self._paginator, name)

    def get_paginated_response_schema(self, schema):
        return _seed_envelope(self._paginator.get_paginated_response_schema(schema), self._data_name)


class SEEDAutoSchema(AutoSchema):
    """SEED's default schema class

    - Tags operations by resource (e.g., `properties`) rather than by API version.
    - Successful serializer-based responses of views rendered by `SEEDJSONRenderer` are described
      inside its `{"status": "success", "<data_name>": ...}` envelope. Raw schema responses (dicts)
      are documented exactly as given, since custom actions often return their own `JsonResponse`.
    """

    def get_tags(self):
        tokenized_path = self._tokenize_path()
        if tokenized_path and tokenized_path[0] in {"v3", "v4"}:
            tokenized_path = tokenized_path[1:]
        return tokenized_path[:1] or ["api"]

    def get_auth(self):
        # Several authentication classes can map to the same scheme (e.g., JWTs via `SEEDAuthentication`)
        auths = []
        for auth in super().get_auth():
            if auth not in auths:
                auths.append(auth)
        return auths

    def _process_override_parameters(self, direction="request"):
        # Drop path parameters that are not in this route, so that views mounted on several routes can
        # describe all of their path parameters in one place
        parameters = super()._process_override_parameters(direction)
        return {key: p for key, p in parameters.items() if key[1] != OpenApiParameter.PATH or f"{{{key[0]}}}" in self.path}

    def _get_request_body(self, direction="request"):
        # drf-spectacular only documents request bodies for PUT, PATCH, and POST, but some SEED DELETE
        # endpoints read one; document it when it is explicitly declared (as a media type mapping)
        if self.method == "DELETE" and isinstance(self._get_request_override(), dict):
            self.method = "POST"
            try:
                return super()._get_request_body(direction)
            finally:
                self.method = "DELETE"
        return super()._get_request_body(direction)

    def _get_request_override(self):
        """The `@extend_schema(request=...)` override, if any (without falling back to the view's serializer)"""
        self._probing_request_override = True
        try:
            return self.get_request_serializer()
        finally:
            self._probing_request_override = False

    def _get_serializer(self):
        if getattr(self, "_probing_request_override", False):
            return None
        return super()._get_serializer()

    def _is_list_view(self, serializer=None):
        # Raw schema responses are documented exactly as given (see `_get_response_for_code`)
        if getattr(self, "_documenting_raw_response", False):
            return False
        return super()._is_list_view(serializer)

    def _seed_data_name(self):
        renderer_classes = getattr(self.view, "renderer_classes", None)
        if renderer_classes and issubclass(renderer_classes[0], SEEDJSONRenderer):
            return getattr(self.view, "data_name", "data")
        return None

    def _get_paginator(self):
        paginator = super()._get_paginator()
        data_name = self._seed_data_name()
        if paginator is not None and data_name:
            return _SEEDEnvelopePaginator(paginator, data_name)
        return paginator

    def get_paginated_name(self, serializer_name):
        name = super().get_paginated_name(serializer_name)
        data_name = self._seed_data_name()
        if data_name:
            name = f"{name}Envelope" if data_name == "data" else f"{name}{data_name.title().replace('_', '')}Envelope"
        return name

    def _get_response_for_code(self, serializer, status_code, media_types=None, direction="response"):
        body_serializer = force_instance(serializer.response if isinstance(serializer, OpenApiResponse) else serializer)
        # Prevent drf-spectacular from wrapping raw schemas in arrays/pagination on `list` actions
        self._documenting_raw_response = isinstance(body_serializer, dict)
        try:
            response = super()._get_response_for_code(serializer, status_code, media_types, direction)
        finally:
            self._documenting_raw_response = False

        data_name = self._seed_data_name()
        if not data_name or not ("200" <= status_code < "300") or isinstance(serializer, UnenvelopedResponse):
            return response
        if not is_serializer(body_serializer):
            return response
        # paginated list responses are already enveloped by `_SEEDEnvelopePaginator`
        if self._is_list_view(body_serializer) and get_override(body_serializer, "many") is not False and self._get_paginator():
            return response

        for content in response.get("content", {}).values():
            content["schema"] = _seed_envelope(content["schema"], data_name)
        return response


class SEEDAuthenticationScheme(OpenApiAuthenticationExtension):
    """`SEEDAuthentication` accepts either `Basic <base64(username:api_key)>` or a JWT `Bearer` token

    The `jwtAuth` scheme itself is registered by drf-spectacular's extension for simplejwt's
    `JWTAuthentication` (see `SPECTACULAR_SETTINGS["APPEND_COMPONENTS"]`).
    """

    target_class = "seed.authentication.SEEDAuthentication"
    name = "basicAuth"

    def get_security_requirement(self, auto_schema):
        # Either scheme is sufficient
        return [{"basicAuth": []}, {"jwtAuth": []}]

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "basic", "description": "Your SEED username and API key"}


class SEEDSessionScheme(SessionScheme):
    """`SEEDSessionAuthentication` is session authentication that also rejects an invalid `Authorization` header

    drf-spectacular's `SessionScheme` only matches `SessionAuthentication` itself, not subclasses.
    """

    target_class = "seed.authentication.SEEDSessionAuthentication"


class DisplayChoiceFieldExtension(OpenApiSerializerFieldExtension):
    """SEED's choice fields read and write the display values of their choices, not the stored keys"""

    target_class = "seed.serializers.base.ChoiceField"

    def map_serializer_field(self, auto_schema, direction):
        return {"type": "string", "enum": list(dict.fromkeys(self.target._choices.values()))}


class CustomChoicesFieldExtension(DisplayChoiceFieldExtension):
    target_class = "seed.serializers.utils.CustomChoicesField"

    def map_serializer_field(self, auto_schema, direction):
        schema = super().map_serializer_field(auto_schema, direction)
        if self.target.allow_blank:
            schema["enum"].append("")
        return schema


class PintQuantityFieldExtension(OpenApiSerializerFieldExtension):
    """Quantities are read and written as numbers in the organization's display units"""

    target_class = "seed.serializers.pint.PintQuantitySerializerField"

    def map_serializer_field(self, auto_schema, direction):
        return {"type": "number", "description": "In the organization's display units"}


class ModelFieldExtension(OpenApiSerializerFieldExtension):
    """DRF serializes GeoDjango geometries (which drf-spectacular cannot map) as EWKT strings via `ModelField`"""

    target_class = "rest_framework.fields.ModelField"

    def map_serializer_field(self, auto_schema, direction):
        if isinstance(self.target.model_field, GeometryField):
            return {"type": "string", "description": "EWKT geometry, e.g., `SRID=4326;POINT (-105.2 39.7)`"}
        return auto_schema._map_model_field(self.target.model_field, direction)

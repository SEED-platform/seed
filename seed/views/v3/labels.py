# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author 'Piper Merriam <pmerriam@quickleft.com>'
"""
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.decorators import DecoratorMixin
from seed.filters import LabelFilterBackend
from seed.models import StatusLabel as Label
from seed.serializers.labels import LabelSerializer
from seed.utils.api import drf_api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.labels import filter_labels_for_inv_type
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


@method_decorator(
    name='retrieve',
    decorator=swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(
            required=False,
            description="Optional org id which overrides the users (default) current org id")]
    ),
)
@method_decorator(
    name='list',
    decorator=swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(
            required=False,
            description="Optional org id which overrides the users (default) current org id")]
    ),
)
@method_decorator(
    name='create',
    decorator=swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(
            required=False,
            description="Optional org id which overrides the users (default) current org id")],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'name': 'string',
                'color': 'string',
            },
            required=['name'],
            description='An object containing meta data for a new label'
        )
    ),
)
@method_decorator(
    name='destroy',
    decorator=swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(
            required=False,
            description="Optional org id which overrides the users (default) current org id")]
    ),
)
@method_decorator(
    name='update',
    decorator=swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(
            required=False,
            description="Optional org id which overrides the users (default) current org id")],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'name': 'string',
                'color': 'string',
            },
            required=['name'],
            description='An object containing meta data for updating a label'
        )
    ),
)
class LabelViewSet(DecoratorMixin(drf_api_endpoint), SEEDOrgNoPatchOrOrgCreateModelViewSet):  # type: ignore[misc]
    """
    retrieve:
        Return a label instance by pk if it is within user`s specified org.

    list:
        Return all labels available to user through user`s specified org.

    create:
        Create a new label within user`s specified org.

    delete:
        Remove an existing label.

    update:
        Update a label record.
    """
    serializer_class = LabelSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser, FormParser)
    queryset = Label.objects.none()
    filter_backends = (LabelFilterBackend,)
    pagination_class = None
    _organization = None

    def get_queryset(self):
        labels = Label.objects.filter(
            super_organization=self.get_parent_org(self.request)
        ).order_by("name").distinct()
        return labels

    def get_serializer(self, *args, **kwargs):
        kwargs['super_organization'] = self.get_organization(self.request)
        inventory = filter_labels_for_inv_type(
            request=self.request
        )
        kwargs['inventory'] = inventory
        return super().get_serializer(*args, **kwargs)

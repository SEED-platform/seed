"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.viewsets import ReadOnlyModelViewSet

from seed.decorators import DRFEndpointMixin
from seed.lib.uniformat.uniformat import uniformat_codes
from seed.models import Uniformat
from seed.serializers.uniformat import UniformatChildSerializer, UniformatSerializer
from seed.utils.api_schema import AutoSchemaHelper


# This read-only endpoint doesn't require any org or AH restrictions
@method_decorator(
    name="list",
    decorator=[
        swagger_auto_schema(
            responses={200: UniformatSerializer(many=True)},
        )
    ],
)
@method_decorator(
    name="retrieve",
    decorator=[
        swagger_auto_schema(
            manual_parameters=[
                AutoSchemaHelper.path_enum_field(
                    name="code", description=Uniformat._meta.get_field("code").help_text, enum=uniformat_codes
                ),
                AutoSchemaHelper.query_boolean_field(
                    name="include_children",
                    required=False,
                    description="If true, includes all Uniformat specifications that inherit from the specified code. Defaults to false.",
                ),
            ],
            responses={200: UniformatSerializer()},
        ),
    ],
)
class UniformatViewSet(DRFEndpointMixin, ReadOnlyModelViewSet):
    """Uniformat API Endpoint

    list:
        Returns all Uniformat specifications, following the Naval Facilities Engineering Command (NAVFAC) UNIFORMAT II classification for building elements to divide a building into systems and components

    retrieve:
        Returns a Uniformat instance by code, optionally including all children of the specified code
    """

    lookup_field = "code"
    model = Uniformat
    pagination_class = None
    queryset = model.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve" and self.request.query_params.get("include_children", "false").lower() in ["", "true"]:
            return UniformatChildSerializer
        return UniformatSerializer

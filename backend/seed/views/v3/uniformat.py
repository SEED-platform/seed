"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema, extend_schema_view
from rest_framework.viewsets import ReadOnlyModelViewSet

from seed.decorators import DRFEndpointMixin
from seed.lib.uniformat.uniformat import uniformat_codes
from seed.models import Uniformat
from seed.serializers.uniformat import UniformatChildSerializer, UniformatSerializer
from seed.utils.api_schema import AutoSchemaHelper


# This read-only endpoint doesn't require any org or AH restrictions
@extend_schema_view(
    list=extend_schema(
        description="Returns all Uniformat specifications, following the Naval Facilities Engineering Command (NAVFAC) UNIFORMAT II "
        "classification for building elements to divide a building into systems and components",
    ),
    retrieve=extend_schema(
        description="Returns a Uniformat instance by code, optionally including all children of the specified code",
        parameters=[
            AutoSchemaHelper.path_enum_field(name="code", description=Uniformat._meta.get_field("code").help_text, enum=uniformat_codes),
            AutoSchemaHelper.query_boolean_field(
                name="include_children",
                required=False,
                description="If true, includes all Uniformat specifications that inherit from the specified code. Defaults to false.",
            ),
        ],
        responses={
            200: PolymorphicProxySerializer(
                component_name="UniformatDetail",
                serializers=[UniformatSerializer, UniformatChildSerializer],
                resource_type_field_name=None,
            )
        },
    ),
)
class UniformatViewSet(DRFEndpointMixin, ReadOnlyModelViewSet):
    """Uniformat API Endpoint"""

    lookup_field = "code"
    model = Uniformat
    pagination_class = None
    queryset = model.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve" and self.request.query_params.get("include_children", "false").lower() in ["", "true"]:
            return UniformatChildSerializer
        return UniformatSerializer

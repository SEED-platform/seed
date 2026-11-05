"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

OpenAPI schema and Swagger UI views
"""

from drf_spectacular.renderers import OpenApiJsonRenderer2
from drf_spectacular.views import SpectacularJSONAPIView, SpectacularSwaggerView


class LegacyOpenApiJsonRenderer(OpenApiJsonRenderer2):
    # Selected by `?format=openapi`, the schema URL previously served by drf-yasg
    format = "openapi"


class SwaggerView(SpectacularSwaggerView):
    """Swagger UI, which also serves the JSON schema at `?format=openapi` for existing clients"""

    template_name = "seed/swagger_ui.html"
    schema_view = staticmethod(SpectacularJSONAPIView.as_view(renderer_classes=[LegacyOpenApiJsonRenderer]))

    def dispatch(self, request, *args, **kwargs):
        if request.GET.get("format") == "openapi":
            return self.schema_view(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)

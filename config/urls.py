"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from two_factor.urls import urlpatterns as two_factor_urls

from config.views import robots_txt
from ng_seed.views import seed_angular
from seed.api.base.urls import urlpatterns as api
from seed.landing.views import CustomLoginView, password_reset_complete, password_reset_confirm, password_reset_done
from seed.views.main import angular_js_tests, config, health_check, version

schema_view = get_schema_view(
    openapi.Info(
        title="SEED API",
        default_version="v3",
        description="SEED Platform API Documentation",
        # terms_of_service="https://www.google.com/policies/terms/",
        # contact=openapi.Contact(email="contact@snippets.local"),
        # license=openapi.License(name="BSD License"),
    ),
    public=False,
    permission_classes=(permissions.AllowAny,),
)


def trigger_error(request):
    """Endpoint for testing sentry with a divide by zero"""
    1 / 0


urlpatterns = [
    path("accounts/password/reset/done/", password_reset_done, name="password_reset_done"),
    path(
        "accounts/password/reset/complete/",
        password_reset_complete,
        name="password_reset_complete",
    ),
    path("accounts/password/reset/confirm/<uidb64>/<token>/", password_reset_confirm, name="password_reset_confirm"),
    # Application
    path("", include(("seed.landing.urls", "seed.landing"), namespace="landing")),
    path("app/", include(("seed.urls", "seed"), namespace="seed")),
    path("ng-app/", seed_angular, name="seed-angular"),
    path("documentation/", include(("seed.docs.urls", "seed.docs"), namespace="docs")),
    # root configuration items
    path("i18n/", include("django.conf.urls.i18n")),
    path("robots.txt", robots_txt, name="robots_txt"),
    # API (explicit no-auth)
    path("api/config/", config, name="config"),
    path("api/health_check/", health_check, name="health_check"),
    # API
    path("api/swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/version/", version, name="version"),
    path("api/", include((api, "seed"), namespace="api")),
    path("account/login", CustomLoginView.as_view(), name="login"),
    path("", include(two_factor_urls)),
    # test sentry error
    path("sentry-debug/", trigger_error),
]

handler404 = "seed.views.main.error404"
handler410 = "seed.views.main.error410"
handler500 = "seed.views.main.error500"


if settings.DEBUG:
    from django.contrib import admin

    admin.autodiscover()
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        # test URLs
        path("angular_js_tests/", angular_js_tests, name="angular_js_tests"),
        # admin
        path("admin/", admin.site.urls),
    ]

# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.conf import settings
from django.conf.urls import include, re_path
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from config.views import robots_txt
from seed.api.base.urls import urlpatterns as api
from seed.landing.views import (
    password_reset_complete,
    password_reset_confirm,
    password_reset_done
)
from seed.views.main import angular_js_tests, version

schema_view = get_schema_view(
    openapi.Info(
        title="SEED API",
        default_version='v3',
        description="Test description",
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
    re_path(r'^accounts/password/reset/done/$', password_reset_done, name='password_reset_done'),
    re_path(
        r'^accounts/password/reset/complete/$',
        password_reset_complete,
        name='password_reset_complete',
    ),
    path(
        'accounts/password/reset/confirm/<uidb64>/<token>/',
        password_reset_confirm,
        name='password_reset_confirm'
    ),

    # Application
    re_path(r'^', include(('seed.landing.urls', "seed.landing"), namespace="landing")),
    re_path(r'^app/', include(('seed.urls', "seed"), namespace="seed")),
    re_path(r'^documentation/', include(('seed.docs.urls', 'seed.docs'), namespace='docs')),

    # root configuration items
    re_path(r'^i18n/', include('django.conf.urls.i18n')),
    re_path(r'^robots\.txt', robots_txt, name='robots_txt'),

    # API
    re_path(r'^api/swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^api/version/$', version, name='version'),
    re_path(r'^api/', include((api, "seed"), namespace='api')),
    re_path(r'^oauth/', include(('oauth2_jwt_provider.urls', 'oauth2_jwt_provider'), namespace='oauth2_provider')),

    # test sentry error
    path('sentry-debug/', trigger_error)
]

handler404 = 'seed.views.main.error404'
handler500 = 'seed.views.main.error500'


if settings.DEBUG:
    from django.contrib import admin

    admin.autodiscover()
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        # test URLs
        re_path(r'^angular_js_tests/$', angular_js_tests, name='angular_js_tests'),

        # admin
        re_path(r'^admin/', admin.site.urls),
    ]

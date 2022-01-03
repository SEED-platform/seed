# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf import settings
from django.conf.urls import include, url
from django.urls import path
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from config.views import robots_txt
from seed.api.base.urls import urlpatterns as api
from seed.landing.views import password_reset_complete, password_reset_confirm, password_reset_done
from seed.views.main import angular_js_tests, version

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

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

urlpatterns = [
    url(r'^accounts/password/reset/done/$', password_reset_done, name='password_reset_done'),
    url(
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
    url(r'^', include(('seed.landing.urls', "seed.landing"), namespace="landing")),
    url(r'^app/', include(('seed.urls', "seed"), namespace="seed")),
    url(r'^documentation/', include(('seed.docs.urls', 'seed.docs'), namespace='docs')),

    # root configuration items
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^robots\.txt', robots_txt, name='robots_txt'),

    # API
    url(r'^api/swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    url(r'^api/version/$', version, name='version'),
    url(r'^api/', include((api, "seed"), namespace='api')),
    url(r'^oauth/', include(('oauth2_jwt_provider.urls', 'oauth2_jwt_provider'), namespace='oauth2_provider'))
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
        url(r'^angular_js_tests/$', angular_js_tests, name='angular_js_tests'),

        # admin
        url(r'^admin/', admin.site.urls),
    ]

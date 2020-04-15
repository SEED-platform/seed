# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from rest_framework_swagger.views import get_swagger_view

from config.views import robots_txt
from seed.api.base.urls import urlpatterns as api
from seed.landing.views import password_reset_complete, password_reset_confirm, password_reset_done
from seed.views.main import angular_js_tests

from rest_framework.schemas import get_schema_view
schema_view = get_schema_view(title='SEED API Schema')

urlpatterns = [
    url(r'^accounts/password/reset/done/$', password_reset_done, name='password_reset_done'),
    url(
        r'^accounts/password/reset/complete/$',
        password_reset_complete,
        name='password_reset_complete',
    ),
    url(
        (
            r'^accounts/password/reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/'
            '(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$'
        ),
        password_reset_confirm,
        name='password_reset_confirm'
    ),
    # Application
    url(r'^', include(('seed.landing.urls', "seed.landing"), namespace="landing")),
    url(r'^app/', include(('seed.urls', "seed"), namespace="seed")),

    # root configuration items
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^robots\.txt', robots_txt, name='robots_txt'),

    # API
    url(r'^api/schema/$', schema_view),
    url(r'^api/swagger/', get_swagger_view(title='SEED API'), name='swagger'),
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

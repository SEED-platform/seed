# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from rest_framework_swagger.views import get_swagger_view

from config.views import robots_txt
from seed.api.base.urls import urlpatterns as api
from seed.views.main import angular_js_tests, pm_integration, pm_integration_worker, pm_integration_get_templates

urlpatterns = [
    # Application
    url(r'^', include('seed.landing.urls', namespace="landing", app_name="landing")),
    url(r'^audit_logs/',
        include('seed.audit_logs.urls', namespace="audit_logs", app_name="audit_logs")),
    url(r'^app/', include('seed.urls', namespace="seed", app_name="seed")),

    # root configuration items
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^robots\.txt', robots_txt, name='robots_txt'),

    # API
    url(r'^api/swagger/', get_swagger_view(title='SEED API'), name='swagger'),
    url(r'^api/', include(api, namespace='api')),

    # Temporary
    url(r'^pm_integration/', pm_integration, name='pm_integration'),
    url(r'^pm_integration_worker/', pm_integration_worker, name='pm_integration_worker'),
    url(r'^pm_integration_get_templates', pm_integration_get_templates, name='pm_integration_get_templates'),
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
        url(r'^admin/', include(admin.site.urls)),
    ]

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf import settings
from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.static import serve

from api.v2.urls import urlpatterns as apiv2
from config.views import robots_txt
from seed.views.main import angular_js_tests

urlpatterns = [
    # landing page
    url(r'^', include('seed.landing.urls', namespace="landing", app_name="landing")),

    # audit_logs AJAX
    url(r'^audit_logs/',
        include('seed.audit_logs.urls', namespace="audit_logs", app_name="audit_logs")),

    url(r'^app/', include('seed.urls.main', namespace="seed", app_name="seed")),

    url(
        r'^api/swagger/',
        include('rest_framework_swagger.urls'),
        name='swagger'
    ),
    url(r'^eula/', include('tos.urls', namespace='tos', app_name='tos')),

    # i18n setlang
    url(r'^i18n/', include('django.conf.urls.i18n')),

    url(r'^robots\.txt', robots_txt, name='robots_txt'),

    url(r'^api/v2/', include(apiv2, namespace="apiv2")),
]

# TODO: 8/8/17 fix media root for docker deployments
if settings.DEBUG:
    from django.contrib import admin

    admin.autodiscover()
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += [
        # test URLs
        url(r'^angular_js_tests/$', angular_js_tests, name='angular_js_tests'),

        # admin
        url(r'^admin/', include(admin.site.urls)),
        url(
            r'^media/(?P<path>.*)$',
            serve,
            {
                'document_root': settings.MEDIA_ROOT,
            }
        ),
    ]

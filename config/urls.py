
# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf.urls import include, url
from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.static import serve

from config.views import robots_txt


admin.autodiscover()


urlpatterns = [
    # landing page
    url(r'^', include('seed.landing.urls', namespace="landing", app_name="landing")),

    # audit_logs AJAX
    url(r'^audit_logs/', include('seed.audit_logs.urls', namespace="audit_logs", app_name="audit_logs")),

    # app section
    url(r'^app/', include('seed.urls.main', namespace="seed", app_name="seed")),

    # api section
    url(r'^app/api/', include('seed.urls.api', namespace="api", app_name="api")),

    url(r'^eula/', include('tos.urls', namespace='tos', app_name='tos')),

    # i18n setlang
    url(r'^i18n/', include('django.conf.urls.i18n')),

    url(r'^robots\.txt', robots_txt, name='robots_txt'),

    url(r'^api/v2/', include('api.urls', namespace="apiv2")),
    url(r'^app/', include('seed.urls.properties', namespace="app", app_name='properties')),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += [
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

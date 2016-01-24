"""
:copyright: (c) 2014 Building Energy Inc
"""
# !/usr/bin/env python
# encoding: utf-8
"""
urls/base.py

Copyright (c) 2012 Building Energy. All rights reserved.
"""
from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

import ajaxuploader.urls

admin.autodiscover()

urlpatterns = patterns(
    '',
    # landing page
    url(r'^', include('seed.landing.urls', namespace="landing", app_name="landing")),

    # accounts/orgs AJAX
    url(r'^app/accounts/', include('seed.urls.accounts', namespace="accounts", app_name="accounts")),

    # projects AJAX
    url(r'^app/projects/', include('seed.urls.projects', namespace="projects", app_name="projects")),

    # audit_logs AJAX
    url(r'^audit_logs/', include('seed.audit_logs.urls', namespace="audit_logs", app_name="audit_logs")),

    # app section
    url(r'^app/', include('seed.urls.main', namespace="seed", app_name="seed")),

    # api section
    url(r'^app/api/', include('seed.urls.api', namespace="api", app_name="api")),

    # labels section
    url(r'^app/labels', include('seed.urls.labels', namespace="labels", app_name="labels")),

    # dataset section
    url(r'^data/', include('seed.data_importer.urls', namespace="data_importer", app_name="data_importer")),

    url(r'^cleansing/', include('seed.cleansing.urls', namespace="cleansing", app_name="cleansing")),

    url(r'^ajax-uploader/', include(ajaxuploader.urls, namespace='ajaxuploader', app_name='ajaxuploader')),

    url(r'^eula/', include('tos.urls', app_name='tos')),

    # i18n setlang # TODO: remove i18n support per Nick Serra?
    url(r'^i18n/', include('django.conf.urls.i18n')),

    url(r'^robots.txt', 'config.views.robots_txt', name='robots_txt'),

)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += patterns(
        '',
        # admin
        url(r'^admin/', include(admin.site.urls)),
        url(
            r'^media/(?P<path>.*)$',
            'django.views.static.serve',
            {
                'document_root': settings.MEDIA_ROOT,
            }
        ),
    )
    urlpatterns += patterns('', url(r'^__debug__/', include(debug_toolbar.urls)), )

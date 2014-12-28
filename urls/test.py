"""
:copyright: (c) 2014 Building Energy Inc
"""
from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    '',
    url(r'^main/', include('urls.main')),
)

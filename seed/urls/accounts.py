# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'seed.views.accounts',
    url(
        r'^get_organization/$',
        'get_organization',
        name='get_organization'
    ),
    url(
        r'^get_organizations/$',
        'get_organizations',
        name='get_organizations'
    ),
    url(
        r'^get_organizations_users/$',
        'get_organizations_users',
        name='get_organizations_users'
    ),
    url(
        r'^remove_user_from_org/$',
        'remove_user_from_org',
        name='remove_user_from_org'
    ),
    url(r'^add_org/$', 'add_org', name='add_org'),
    url(r'^add_user/$', 'add_user', name='add_user'),
    url(
        r'^add_user_to_organization/$',
        'add_user_to_organization',
        name='add_user_to_organization'
    ),
    url(
        r'^update_role/$',
        'update_role',
        name='update_role'
    ),
    url(
        r'^save_org_settings/$',
        'save_org_settings',
        name='save_org_settings'
    ),
    url(
        r'^get_query_threshold/$',
        'get_query_threshold',
        name='get_query_threshold'
    ),
    url(
        r'^get_shared_fields/$',
        'get_shared_fields',
        name='get_shared_fields'
    ),
    url(
        r'^create_sub_org/$',
        'create_sub_org',
        name='create_sub_org'
    ),
    url(
        r'^is_authorized/$',
        'is_authorized',
        name='is_authorized'
    ),
    url(
        r'^get_actions/$',
        'get_actions',
        name='get_actions'
    ),
    url(
        r'^get_shared_buildings/$',
        'get_shared_buildings',
        name='get_shared_buildings'
    ),
    url(
        r'^set_default_organization/$',
        'set_default_organization',
        name='set_default_organization'
    ),
    url(
        r'^get_user_profile/$',
        'get_user_profile',
        name='get_user_profile'
    ),
    url(
        r'^generate_api_key/$',
        'generate_api_key',
        name='generate_api_key'
    ),
    url(
        r'^update_user/$',
        'update_user',
        name='update_user'
    ),
    url(
        r'^set_password/$',
        'set_password',
        name='set_password'
    ),
    url(r'^get_users/$', 'get_users', name='get_users'),
)

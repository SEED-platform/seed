"""
:copyright: (c) 2014 Building Energy Inc
"""
#!/usr/bin/env python
# encoding: utf-8
"""
urls.py

Copyright (c) 2013 Building Energy. All rights reserved.
"""

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'seed.data_importer.views',
    url(
        r's3_upload_complete/$',
        'handle_s3_upload_complete',
        name='s3_upload_complete'
    ),
    url(r'get_upload_details/$',
        'get_upload_details',
        name='get_upload_details'
    ),
    url(r'sign_policy_document/$',
        'sign_policy_document',
        name='sign_policy_document'
    ),
    url(
        r'upload/$',
        'local_uploader',
        name='local_uploader'
    ),
)

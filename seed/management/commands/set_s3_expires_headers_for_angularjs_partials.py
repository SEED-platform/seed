# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
"""
This should be executed after S3 bucket and CORS are set as last step and called in post_compile script.
"""
# stdlib
from datetime import datetime
import mimetypes
from optparse import make_option

# Django
from django.conf import settings
from django.core.management.base import BaseCommand

# vendor
from boto.s3.connection import S3Connection



class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--prefix',
                    action='store_true',
                    default='seed/partials',
                    help='Sets the prefix directory to set the expires header.'),
        )
    help = "Sets S3 Expires headers for AngularJS partials to prevent browser caching old html partials. ./manage.py set_s3_expires_headers_for_angularjs_partials.py --prefix='seed/partials'"

    def handle(self, *args, **options):
        verbosity = int(options.get('verbosity', 1))
        prefix = options.get('prefix', 'seed/partials')

        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        bucket = conn.get_bucket(settings.AWS_STORAGE_BUCKET_NAME)
        # get list of all files recursively in the directory (prefix), i.e. all the AngularJS partials
        key_list = bucket.get_all_keys(prefix=prefix)
        for key in key_list:
            content_type, unused = mimetypes.guess_type(key.name)
            if not content_type:
                content_type = 'text/plain'
            # set the expires header to now to verify that it's working.
            expires = datetime.utcnow()
            expires = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
            metadata = {'Expires': expires, 'Content-Type': content_type}
            if verbosity > 2:
                print key.name, metadata
            key.copy(settings.AWS_STORAGE_BUCKET_NAME, key, metadata=metadata, preserve_acl=True)

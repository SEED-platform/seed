"""
:copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf import settings
from django.core.management.base import BaseCommand
import boto
from boto.s3.cors import CORSConfiguration


class Command(BaseCommand):
    help = "My shiny new management command."

    def handle(self, *args, **options):
        conn = boto.connect_s3(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        cors_cfg = CORSConfiguration()
        cors_cfg.add_rule(['GET', 'POST', 'PUT'], '*', allowed_header='*')
        try:
            b = conn.get_bucket(settings.AWS_STORAGE_BUCKET_NAME)
            b.set_acl('public-read')
            b.set_cors(cors_cfg)
        except boto.exception.S3ResponseError:
            b = conn.create_bucket(settings.AWS_STORAGE_BUCKET_NAME)
            b.set_acl('public-read')
            b.set_cors(cors_cfg)

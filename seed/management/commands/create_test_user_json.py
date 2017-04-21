# -*- coding: utf-8 -*-
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
from optparse import make_option

from django.core.management.base import BaseCommand

from seed.landing.models import SEEDUser as User


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--username',
                    default='demo@seed-platform.org',
                    help='Sets the default username.',
                    action='store',
                    type='string',
                    dest='username'),
        make_option('--file',
                    default='./seed/tests/api/api_test_user.json',
                    help='File name to save JSON',
                    action='store',
                    type='string',
                    dest='file'),

    )
    help = 'Creates the JSON file needed for testing the API'

    def handle(self, *args, **options):
        if User.objects.filter(username=options['username']).exists():
            u = User.objects.get(username=options['username'])

            data = {
                'name': 'seed_api_test',
                'host': 'http://127.0.0.1:8000',
                'username': options['username'],
                'api_key': u.api_key,
            }

            with open(options['file'], 'w') as outfile:
                json.dump(data, outfile, indent=2)
        else:
            print('User does not exist')
            exit(1)

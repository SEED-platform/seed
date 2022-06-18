# -*- coding: utf-8 -*-
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import json
import re

from django.core.management.base import BaseCommand

from seed.landing.models import SEEDUser as User


class Command(BaseCommand):
    help = 'Creates the JSON file needed for testing the API'

    def add_arguments(self, parser):
        parser.add_argument('--username',
                            default='demo@seed-platform.org',
                            help='Sets the default username.',
                            action='store',
                            dest='username')

        parser.add_argument('--host',
                            default='http://127.0.0.1:8000',
                            help='Host',
                            action='store',
                            dest='host')

        parser.add_argument('--file',
                            default='none',
                            help='File name to save JSON',
                            action='store',
                            dest='file')

        parser.add_argument('--pyseed',
                            help='Write out in the format for pyseed',
                            action='store_true',
                            dest='pyseed')

    def handle(self, *args, **options):
        if User.objects.filter(username=options['username']).exists():
            u = User.objects.get(username=options['username'])

            if not options['pyseed']:
                data = {
                    'name': 'seed_api_test',
                    'host': options['host'],
                    'username': options['username'],
                    'api_key': u.api_key,
                }
            else:
                # pull out the protocol, port, and url to break up the parts
                pattern = re.compile(r'^(.*:)//([A-Za-z0-9\-\.]+)(:[0-9]+)?(.*)$')
                match = pattern.match(options['host'])
                data = {
                    'name': 'seed_api_test',
                    'base_url': f"{match.group(1)}//{match.group(2)}",
                    'username': options['username'],
                    'api_key': u.api_key,
                    'port': int(match.group(3).replace(':', '')) if match.group(3) else 80,
                    'use_ssl': True if 'https' in match.group(1) else False,
                }

            if options['file'] == 'none':
                print(json.dumps(data))
            else:
                with open(options['file'], 'w') as outfile:
                    json.dump(data, outfile, indent=2)

        else:
            print('User does not exist')
            exit(1)

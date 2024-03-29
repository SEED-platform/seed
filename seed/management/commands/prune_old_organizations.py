"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

Delete all organizations that are not part of the main 12.
See code for organization list and source documentation.
"""

import logging

from _localtools import get_core_organizations
from django.core.management.base import BaseCommand

import seed.models
import seed.tasks

logging.basicConfig(level=logging.DEBUG)


def get_organizations_to_delete():
    """Get all organizations that are not in the global white list."""

    all_organizations = seed.models.Organization.objects.all()
    bad_organizations = [org for org in all_organizations if org.id not in get_core_organizations()]
    return bad_organizations


def destroy_organization(org):
    """Delete an organization using the Celery information."""
    logging.info(f'Deleting organization {org}')
    seed.tasks.delete_organization(org.pk)


class Command(BaseCommand):
    def handle(self, *args, **options):
        """Delete all organizations that are not in Robin's whitelist."""

        logging.debug('**NOTE - Celery server must be running for this operation to work')

        deprecated_organizations = get_organizations_to_delete()

        logging.info(f'Deleting {deprecated_organizations} deprecated organizations.')
        for org in deprecated_organizations:
            destroy_organization(org)

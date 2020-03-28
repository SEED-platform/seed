# -*- coding: utf-8 -*-
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author

Delete all organizations that are not part of the main 12.
See code for organization list and source documentation.
"""
from __future__ import unicode_literals

import logging

from django.core.management.base import BaseCommand

import seed.models
import seed.tasks
from _localtools import get_core_organizations

logging.basicConfig(level=logging.DEBUG)


def get_organizations_to_delete():
    """Get all organizations that are not in the global white list."""

    all_organizations = seed.models.Organization.objects.all()
    bad_organizations = [org for org in all_organizations if org.id not in get_core_organizations()]
    return bad_organizations


def destroy_organization(org):
    """Delete an organization using the Celery information."""
    logging.info("Deleting organization {}".format(org))
    seed.tasks.delete_organization(org.pk)
    return


class Command(BaseCommand):
    def handle(self, *args, **options):
        """Delete all organizations that are not in Robin's whitelist."""

        logging.debug("**NOTE - Celery server must be running for this operation to work")

        deprecated_organizations = get_organizations_to_delete()

        logging.info("Deleting {} deprecated organizations.".format(deprecated_organizations))
        for org in deprecated_organizations:
            destroy_organization(org)

        return

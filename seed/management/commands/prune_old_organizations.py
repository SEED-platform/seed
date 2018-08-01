"""Delete all organizations that are not part of the main 12.

See code for organization list and source documentation.
"""

from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from IPython import embed
import logging
import seed.tasks
import seed.models
from _localtools import get_core_organizations

logging.basicConfig(level=logging.DEBUG)

def getOrganizationsToDelete():
    """Get all organizations that are not in the global white list."""

    all_organizations = seed.models.Organization.objects.all()
    bad_organizations = [org for org in all_organizations if org.id not in get_core_organizations()]
    return bad_organizations


def destroyOrganization(org):
    """Delete an organization using the Celery information."""
    logging.info("Deleting organization {}".format(org))
    seed.tasks.delete_organization(org.pk)
    return


class Command(BaseCommand):
    def handle(self, *args, **options):
        """Delete all organizations that are not in Robin's whitelist."""

        logging.debug("**NOTE - Celery server must be running for this operation to work")

        deprecated_organizations = getOrganizationsToDelete()

        logging.info("Deleting {} deprecated organizations.".format(deprecated_organizations))
        for org in deprecated_organizations:
            destroyOrganization(org)

        return

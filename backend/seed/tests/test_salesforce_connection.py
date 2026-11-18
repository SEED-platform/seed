"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from unittest import skipUnless

from django.conf import settings
from django.test import SimpleTestCase

# Alias the import so the unittest/pytest collectors never mistake the
# `test_connection` helper for a test function in this module.
from seed.utils.salesforce import test_connection as check_salesforce_connection

HAS_LIVE_SALESFORCE_CREDENTIALS = all(
    [
        settings.SF_INSTANCE,
        settings.SF_USERNAME,
        settings.SF_PASSWORD,
        settings.SF_SECURITY_TOKEN,
    ]
)


def salesforce_connection_params():
    """Build Salesforce connection params from settings, mirroring the app.

    Only includes ``domain`` when ``SF_DOMAIN == "test"`` (sandbox), matching
    the behavior of ``seed.utils.salesforce.retrieve_connection_params``.
    """
    params = {
        "instance": settings.SF_INSTANCE,
        "username": settings.SF_USERNAME,
        "password": settings.SF_PASSWORD,
        "security_token": settings.SF_SECURITY_TOKEN,
    }
    if settings.SF_DOMAIN == "test":
        params["domain"] = settings.SF_DOMAIN
    return params


class SalesforceConnectionTests(SimpleTestCase):
    """Standalone Salesforce connectivity check.

    This is intentionally isolated from ``SalesforceViewTests`` (no database,
    no orgs/columns/labels/mappings setup) so it can be run on its own to debug
    live Salesforce connectivity -- for example on CI runs where the
    environment or source IP differs (Dependabot PRs, forks, etc.):

        uv run python manage.py test \\
            seed.tests.test_salesforce_connection.SalesforceConnectionTests.test_salesforce_connection \\
            --settings=config.settings.docker_test

    The test skips when Salesforce credentials are not configured, so it is a
    no-op in environments without the ``SF_*`` settings/secrets.
    """

    @skipUnless(HAS_LIVE_SALESFORCE_CREDENTIALS, "Salesforce integration credentials are not configured for this test environment")
    def test_salesforce_connection(self):
        params = salesforce_connection_params()
        status, message, client = check_salesforce_connection(params)

        # Non-secret context to make CI failures easy to diagnose. Password and
        # security token are deliberately never included here.
        context = f"instance={params.get('instance')!r} domain={params.get('domain')!r} username={params.get('username')!r}"

        self.assertTrue(status, msg=f"Salesforce connection failed ({context}): {message}")
        self.assertIsNone(message, msg=f"Unexpected Salesforce connection message ({context}): {message}")
        self.assertIsNotNone(client, msg=f"Salesforce client was not created ({context})")

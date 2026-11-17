"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import getpass
import os
import sys
from collections import Counter

from cryptography.fernet import Fernet
from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.encoding import force_bytes

from seed.utils.encrypt import ENCRYPTED_FIELDS, ReencryptState, reencrypt_column, secret_key_fernet

OLD_KEY_ENV_VAR = "OLD_SECRET_KEY"


class Command(BaseCommand):
    help = (
        "Re-encrypts the stored third-party credentials (the Audit Template, Salesforce, BETTER, and MapQuest passwords, "
        "tokens, and keys) that were encrypted with an old SECRET_KEY with the current SECRET_KEY. Run it after changing "
        "SECRET_KEY, with SEED in maintenance mode so that no request saves an old value back. It prompts for the old key, "
        f"or reads it from the {OLD_KEY_ENV_VAR} environment variable."
    )
    # Lets tests replace stdin, as for `createsuperuser`
    stealth_options = ("stdin",)

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report what would be re-encrypted without saving anything")

    def handle(self, *args, **options):
        # the key itself is never kept in a local during the database work, which error reporting would capture
        old_fernet = self.get_old_fernet(options.get("stdin", sys.stdin))

        dry_run = options["dry_run"]
        totals: Counter = Counter()
        try:
            # all or nothing, and the rows are locked until every column is re-encrypted
            with transaction.atomic():
                for label, field_names in ENCRYPTED_FIELDS.items():
                    model = apps.get_model(label)
                    for field_name in field_names:
                        pks = reencrypt_column(model, field_name, old_fernet, dry_run=dry_run)
                        self.report_column(f"{label}.{field_name}", pks, dry_run=dry_run)
                        totals.update({state: len(state_pks) for state, state_pks in pks.items()})
        except KeyboardInterrupt:
            self.stderr.write("\nOperation cancelled. Nothing was changed.")
            sys.exit(1)

        reencrypted = totals[ReencryptState.REENCRYPTED]
        undecryptable = totals[ReencryptState.UNDECRYPTABLE]
        if undecryptable and not reencrypted:
            # nothing was changed, but fail so that a mistyped key isn't mistaken for success
            raise CommandError(
                f"The old key decrypted none of the {undecryptable} credentials (listed above) that SECRET_KEY doesn't decrypt, "
                "so nothing was changed. Check that it's the previous SECRET_KEY, or re-enter those credentials in SEED."
            )
        if undecryptable:
            self.stderr.write(
                self.style.WARNING(
                    f"{undecryptable} credentials (listed above) are decrypted by neither the old key nor SECRET_KEY and were left "
                    "unchanged. Run this command again with the key that encrypted them, or re-enter them in SEED."
                )
            )
        if dry_run:
            self.stdout.write(f"Dry run: {reencrypted} credentials would be re-encrypted with SECRET_KEY. Nothing was saved.")
        elif reencrypted:
            self.stdout.write(self.style.SUCCESS(f"Re-encrypted {reencrypted} credentials with SECRET_KEY."))
        else:
            self.stdout.write("Nothing to re-encrypt: every stored credential is already encrypted with SECRET_KEY.")

    def get_old_fernet(self, stdin) -> Fernet:
        old_key = os.environ.get(OLD_KEY_ENV_VAR)
        if old_key is None:
            if not (hasattr(stdin, "isatty") and stdin.isatty()):
                raise CommandError(f"Set {OLD_KEY_ENV_VAR} to the old SECRET_KEY, or run this command interactively to be prompted for it.")
            try:
                old_key = getpass.getpass("Old SECRET_KEY: ")
            except KeyboardInterrupt:
                self.stderr.write("\nOperation cancelled.")
                sys.exit(1)
        if not old_key:
            raise CommandError("The old key can't be empty.")
        if force_bytes(old_key) == force_bytes(settings.SECRET_KEY):
            raise CommandError("The old key is the current SECRET_KEY. Change SECRET_KEY to the new key before running this command.")
        return secret_key_fernet(old_key)

    def report_column(self, label: str, pks: dict[ReencryptState, list[int]], *, dry_run: bool) -> None:
        # values are never reported, only primary keys
        for pk in pks.get(ReencryptState.UNDECRYPTABLE, []):
            self.stdout.write(f"{label} pk={pk}: {ReencryptState.UNDECRYPTABLE}")
        if pks:
            counts = ", ".join(
                f"{len(pks[state])} {'to re-encrypt' if dry_run and state == ReencryptState.REENCRYPTED else state}"
                for state in ReencryptState
                if state in pks
            )
            self.stdout.write(f"{label}: {counts}")

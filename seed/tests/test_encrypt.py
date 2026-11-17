"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import contextlib
import importlib
import io
import os
from typing import Any
from unittest import mock

import pytest
from django.apps import apps
from django.conf import settings
from django.core import signing
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import models, transaction
from django.test import SimpleTestCase, TestCase, override_settings

from seed.lib.superperms.orgs.models import Organization
from seed.management.commands.reencrypt_credentials import OLD_KEY_ENV_VAR
from seed.models import BBSalesforceConfig, SalesforceConfig
from seed.utils.encrypt import (
    ENCRYPTED_FIELDS,
    LegacySecretState,
    ReencryptState,
    SecretDecryptionError,
    _warn_once,
    convert_legacy_secret,
    decrypt_secret,
    decrypt_secret_strict,
    encrypt_if_changed,
    encrypt_secret,
    is_encrypted,
    reencrypt_secret,
    secret_key_fernet,
)

OTHER_KEY = "another-secret-key-that-is-not-configured"
THIRD_KEY = "a-third-secret-key-that-is-not-configured"


def legacy_sign(value, key=None):
    """Sign a value as the old `encrypt()` did, with SECRET_KEY as the key and salt"""
    key = key or settings.SECRET_KEY
    return signing.Signer(key=key, salt=key).sign_object(value)


class EncryptSecretTests(SimpleTestCase):
    def setUp(self):
        _warn_once.cache_clear()

    def test_round_trip(self):
        for plaintext in ["password", "with:colon$and dollar", "  padded  ", "InBhc3N3b3JkIg", "\N{GRINNING FACE}" * 128]:
            with self.subTest(plaintext=plaintext):
                token = encrypt_secret(plaintext)
                assert is_encrypted(token)
                assert plaintext.strip() not in token
                assert len(token) <= 787
                assert decrypt_secret(token) == plaintext
                assert decrypt_secret_strict(token) == plaintext
                # a random IV makes every encryption differ
                assert encrypt_secret(plaintext) != token

    def test_empty_values_are_not_encrypted(self):
        assert encrypt_secret("") == ""
        assert encrypt_secret(None) is None
        assert decrypt_secret("") == ""
        assert decrypt_secret(None) == ""

    def test_encrypt_rejects_non_strings(self):
        non_strings: list[Any] = [False, 1, b"bytes"]
        for value in non_strings:
            with self.subTest(value=value), pytest.raises(TypeError):
                encrypt_secret(value)

    def test_undecryptable_values_return_empty_and_warn_once(self):
        with override_settings(SECRET_KEY=OTHER_KEY):
            foreign_token = encrypt_secret("foreign password")
        tampered_token = encrypt_secret("tampered password")[:-4] + "AAAA"
        for i, value in enumerate(
            ["garbage", "fernet$garbage", "fernet$\N{GRINNING FACE}", foreign_token, tampered_token, legacy_sign("legacy")]
        ):
            with self.subTest(value=value):
                context = f"test secret {i}"
                with self.assertLogs("seed.utils.encrypt", "WARNING") as logs:
                    assert decrypt_secret(value, context=context) == ""
                assert len(logs.output) == 1
                assert context in logs.output[0]
                assert value not in logs.output[0]

                with self.assertNoLogs("seed.utils.encrypt"):
                    assert decrypt_secret(value, context=context) == ""
                with pytest.raises(SecretDecryptionError):
                    decrypt_secret_strict(value)

    def test_secret_key_fallbacks_are_not_used(self):
        # after SECRET_KEY changes, the `reencrypt_credentials` command re-encrypts the secrets with the new key
        token = encrypt_secret("password")
        signed = legacy_sign("password")

        with override_settings(SECRET_KEY=OTHER_KEY, SECRET_KEY_FALLBACKS=[settings.SECRET_KEY]):
            assert decrypt_secret(token) == ""
            with pytest.raises(SecretDecryptionError, match="reencrypt_credentials"):
                decrypt_secret_strict(token)
            # nor to verify legacy signed values
            converted, state = convert_legacy_secret(signed)
            assert state == LegacySecretState.SIGNED_UNVERIFIED
            assert decrypt_secret(converted) == "password"

    def test_reencrypt_secret(self):
        with override_settings(SECRET_KEY=OTHER_KEY):
            old_token = encrypt_secret("old password")
        with override_settings(SECRET_KEY=THIRD_KEY):
            foreign_token = encrypt_secret("foreign password")
        current_token = encrypt_secret("current password")

        for old_key in [OTHER_KEY, OTHER_KEY.encode()]:
            with self.subTest(old_key=old_key):
                old_fernet = secret_key_fernet(old_key)
                reencrypted, state = reencrypt_secret(old_token, old_fernet)
                assert state == ReencryptState.REENCRYPTED
                assert is_encrypted(reencrypted)
                assert decrypt_secret(reencrypted) == "old password"
                # re-encrypting is idempotent
                assert reencrypt_secret(reencrypted, old_fernet) == (reencrypted, ReencryptState.CURRENT)

                assert reencrypt_secret(current_token, old_fernet) == (current_token, ReencryptState.CURRENT)
                for value in [foreign_token, "fernet$garbage", "plaintext", legacy_sign("password", OTHER_KEY)]:
                    assert reencrypt_secret(value, old_fernet) == (value, ReencryptState.UNDECRYPTABLE)

    def test_encrypt_if_changed(self):
        token = encrypt_secret("password")

        # submitting the stored password keeps the stored value
        assert encrypt_if_changed(token, "password") == token
        # a new password is encrypted, and "" or None clear it
        assert decrypt_secret(encrypt_if_changed(token, "new password")) == "new password"
        assert encrypt_if_changed(token, "") == ""
        assert encrypt_if_changed(token, None) is None
        assert encrypt_if_changed(None, "") == ""
        assert encrypt_if_changed("", None) is None
        not_a_string: Any = False
        with pytest.raises(TypeError):
            encrypt_if_changed(token, not_a_string)

        # submitting "" (what is shown for a value that can't be decrypted) keeps it, while a new password replaces it
        with override_settings(SECRET_KEY=OTHER_KEY):
            assert encrypt_if_changed(token, "") == token
            assert decrypt_secret(encrypt_if_changed(token, "new password")) == "new password"

    def test_convert_legacy_secret(self):
        cases = [
            (legacy_sign("password"), "password", LegacySecretState.SIGNED),
            (legacy_sign("with:colon"), "with:colon", LegacySecretState.SIGNED),
            (legacy_sign("\N{GRINNING FACE}"), "\N{GRINNING FACE}", LegacySecretState.SIGNED),
            (legacy_sign("password", OTHER_KEY), "password", LegacySecretState.SIGNED_UNVERIFIED),
            # previously hardcoded in the Audit Template tests, but signed with a key the tests don't use
            ("InBhc3N3b3JkIg:xIgRoZurgtGDvmVEUL5Tx1vGbAQe-Iepsct5hiQx29Q", "password", LegacySecretState.SIGNED_UNVERIFIED),
            # signed by migration 0031 and by the old view when the password was omitted
            (legacy_sign(""), "", LegacySecretState.SIGNED),
            (legacy_sign(False), "", LegacySecretState.SIGNED),
            (legacy_sign(None), "", LegacySecretState.SIGNED),
            (legacy_sign(12345), "12345", LegacySecretState.SIGNED_NON_STRING),
            (legacy_sign({"a": 1}), "", LegacySecretState.SIGNED_NON_STRING),
            # the old views signed lone surrogates from JSON escapes, which can't be encoded (or sent)
            (legacy_sign("pa\ud800ss"), "", LegacySecretState.SIGNED_INVALID_STRING),
            ("hunter2", "hunter2", LegacySecretState.PLAINTEXT),
            ("a:b", "a:b", LegacySecretState.PLAINTEXT),
            ("abc:" + "A" * 43, "abc:" + "A" * 43, LegacySecretState.PLAINTEXT),
        ]
        for value, plaintext, state in cases:
            with self.subTest(value=value):
                converted, converted_state = convert_legacy_secret(value)
                assert converted_state == state
                if plaintext:
                    assert is_encrypted(converted)
                else:
                    assert converted == ""
                assert decrypt_secret(converted) == plaintext
                # conversion is idempotent
                if converted:
                    assert convert_legacy_secret(converted) == (converted, LegacySecretState.ENCRYPTED)

    def test_convert_legacy_secret_in_a_plaintext_column(self):
        # a key that happens to look signed is encrypted verbatim
        for value in ["api-key", legacy_sign("password"), "\N{GRINNING FACE}"]:
            with self.subTest(value=value):
                converted, state = convert_legacy_secret(value, signed=False)
                assert state == LegacySecretState.PLAINTEXT
                assert decrypt_secret(converted) == value
                assert convert_legacy_secret(converted, signed=False) == (converted, LegacySecretState.ENCRYPTED)

    def test_convert_legacy_secret_keeps_empty_and_undecryptable_values(self):
        assert convert_legacy_secret("") == ("", None)
        assert convert_legacy_secret(None) == (None, None)
        with override_settings(SECRET_KEY=OTHER_KEY):
            foreign_token = encrypt_secret("password")
        assert convert_legacy_secret(foreign_token) == (foreign_token, LegacySecretState.UNDECRYPTABLE)
        assert convert_legacy_secret("fernet$garbage") == ("fernet$garbage", LegacySecretState.UNDECRYPTABLE)


class EncryptSecretMigrationTests(TestCase):
    """Tests of the data migrations that encrypt the stored credentials (legacy signed passwords and plaintext)"""

    # Columns that held legacy signed passwords, and columns that held plaintext
    SIGNED_FIELDS = [(Organization, "audit_template_password"), (SalesforceConfig, "password")]
    PLAINTEXT_FIELDS = [
        (Organization, "at_organization_token"),
        (Organization, "better_analysis_api_key"),
        (Organization, "mapquest_api_key"),
        (SalesforceConfig, "security_token"),
        (BBSalesforceConfig, "client_secret"),
    ]

    def setUp(self):
        _warn_once.cache_clear()
        self.orgs_migration = importlib.import_module("seed.lib.superperms.orgs.migrations.0048_encrypt_credentials")
        self.seed_migration = importlib.import_module("seed.migrations.0260_encrypt_credentials")

        with override_settings(SECRET_KEY=OTHER_KEY):
            self.foreign_token = encrypt_secret("foreign secret")
        # stored and decrypted values of the signed columns
        self.signed_stored = {
            "signed": legacy_sign("signed password"),
            "unverified": legacy_sign("unverified password", OTHER_KEY),
            "signed empty": legacy_sign(""),
            "signed false": legacy_sign(False),
            "plaintext": "plaintext password",
            "empty": "",
            "undecryptable": self.foreign_token,
        }
        self.signed_expected = {
            "signed": "signed password",
            "unverified": "unverified password",
            "signed empty": "",
            "signed false": "",
            "plaintext": "plaintext password",
            "empty": "",
            "undecryptable": "",
        }
        # stored values of the plaintext columns, which are encrypted verbatim (even one that looks signed)
        self.plaintext_stored = {name: f"plaintext-secret-{i}" for i, name in enumerate(self.signed_stored)}
        self.plaintext_stored |= {"unverified": legacy_sign("looks signed"), "empty": "", "undecryptable": self.foreign_token}

        self.instances = {}
        for name in self.signed_stored:
            org = Organization.objects.create(name=f"org {name}")
            self.instances[name] = {
                Organization: org,
                SalesforceConfig: SalesforceConfig.objects.create(organization=org),
                BBSalesforceConfig: BBSalesforceConfig.objects.create(organization=org),
            }
            for model, field_name in self.SIGNED_FIELDS:
                model.objects.filter(pk=self.instances[name][model].pk).update(**{field_name: self.signed_stored[name]})
            for model, field_name in self.PLAINTEXT_FIELDS:
                model.objects.filter(pk=self.instances[name][model].pk).update(**{field_name: self.plaintext_stored[name]})
        null_org = Organization.objects.create(name="org null")
        self.null_salesforce_config = SalesforceConfig.objects.create(organization=null_org, password=None, security_token=None)
        self.null_bb_salesforce_config = BBSalesforceConfig.objects.create(organization=null_org, client_secret=None)

    def run_migrations(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            for migration in [self.orgs_migration, self.seed_migration]:
                # each migration is atomic
                with transaction.atomic():
                    migration.encrypt_credentials(apps, None)
        return stdout.getvalue()

    def stored_values(self):
        return {
            (model, field_name, name): getattr(model.objects.get(pk=instances[model].pk), field_name)
            for model, field_name in self.SIGNED_FIELDS + self.PLAINTEXT_FIELDS
            for name, instances in self.instances.items()
        }

    def expected_plaintext(self, model, field_name, name):
        if (model, field_name) in self.SIGNED_FIELDS:
            return self.signed_expected[name]
        return "" if name == "undecryptable" else self.plaintext_stored[name]

    def test_encrypt(self):
        modified = Organization.objects.get(pk=self.instances["signed"][Organization].pk).modified
        output = self.run_migrations()

        stored = self.stored_values()
        for (model, field_name, name), value in stored.items():
            with self.subTest(field=f"{model._meta.label}.{field_name}", name=name):
                expected = self.expected_plaintext(model, field_name, name)
                if name == "undecryptable":
                    # left unchanged so that `reencrypt_credentials` can re-encrypt it with the key that encrypted it
                    assert value == self.foreign_token
                elif expected:
                    assert is_encrypted(value)
                    assert decrypt_secret(value) == expected
                else:
                    assert value == ""
        null_salesforce_config = SalesforceConfig.objects.get(pk=self.null_salesforce_config.pk)
        null_bb_salesforce_config = BBSalesforceConfig.objects.get(pk=self.null_bb_salesforce_config.pk)
        # compared as a tuple: without Django stubs, IDEs type fields as `TextField`, so `is None` marks the rest unreachable
        null_values = (null_salesforce_config.password, null_salesforce_config.security_token, null_bb_salesforce_config.client_secret)
        assert null_values == (None, None, None)
        # the rows are updated without saving the models
        assert Organization.objects.get(pk=self.instances["signed"][Organization].pk).modified == modified

        # values that may need attention are reported by primary key (plaintext only in the signed columns)
        for model, field_name in self.SIGNED_FIELDS + self.PLAINTEXT_FIELDS:
            flagged = {"unverified", "plaintext", "undecryptable"} if (model, field_name) in self.SIGNED_FIELDS else {"undecryptable"}
            for name, instances in self.instances.items():
                with self.subTest(field=f"{model._meta.label}.{field_name}", name=name):
                    reported = f"{model._meta.label}.{field_name} pk={instances[model].pk}:" in output
                    assert reported == (name in flagged)
        # and no value is reported
        for value in [*self.signed_stored.values(), *self.signed_expected.values(), *self.plaintext_stored.values()]:
            if value:
                assert value not in output

        # running it again changes nothing
        self.run_migrations()
        assert self.stored_values() == stored

    def test_encrypt_clears_false_audit_template_tokens(self):
        # the settings view saved an omitted token as "False"
        org = self.instances["signed"][Organization]
        Organization.objects.filter(pk=org.pk).update(at_organization_token="False")

        output = self.run_migrations()

        assert Organization.objects.get(pk=org.pk).at_organization_token == ""
        assert 'orgs.Organization.at_organization_token: cleared 1 values of "False"' in output

    def test_historical_migration_still_imports(self):
        migration = importlib.import_module("seed.lib.superperms.orgs.migrations.0031_encrypt_existing_audit_template_passwords")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            migration.encrypt_existing_audit_template_passwords(apps, None)
        assert stdout.getvalue() == ""


class ReencryptCredentialsCommandTests(TestCase):
    """Tests of the `reencrypt_credentials` command, which re-encrypts the credentials after SECRET_KEY changes"""

    FIELDS = [(apps.get_model(label), field_name) for label, field_names in ENCRYPTED_FIELDS.items() for field_name in field_names]
    OLD_KEY = OTHER_KEY

    def setUp(self):
        # each organization's credentials are encrypted with the old key, SECRET_KEY, or a key that's unknown, or empty
        self.stored = {}
        self.instances = {}
        for name, key in [("old", self.OLD_KEY), ("current", settings.SECRET_KEY), ("unknown", THIRD_KEY), ("empty", None)]:
            org = Organization.objects.create(name=f"org {name}")
            self.instances[name] = {
                Organization: org,
                SalesforceConfig: SalesforceConfig.objects.create(organization=org),
                BBSalesforceConfig: BBSalesforceConfig.objects.create(organization=org),
            }
            for model, field_name in self.FIELDS:
                if key is None:
                    value = "" if model is Organization else None
                else:
                    with override_settings(SECRET_KEY=key):
                        value = encrypt_secret(f"{name} {model._meta.label}.{field_name}")
                model.objects.filter(pk=self.instances[name][model].pk).update(**{field_name: value})
                self.stored[(model, field_name, name)] = value

    def call(self, *args, old_key: str | None = OLD_KEY, stdin=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ):
            os.environ.pop(OLD_KEY_ENV_VAR, None)
            if old_key is not None:
                os.environ[OLD_KEY_ENV_VAR] = old_key
            call_command("reencrypt_credentials", *args, stdout=stdout, stderr=stderr, stdin=stdin or io.StringIO())
        return stdout.getvalue(), stderr.getvalue()

    def stored_values(self):
        return {
            (model, field_name, name): getattr(model.objects.get(pk=instances[model].pk), field_name)
            for model, field_name in self.FIELDS
            for name, instances in self.instances.items()
        }

    def assert_unchanged(self):
        assert self.stored_values() == self.stored

    def assert_no_secrets_in(self, output):
        assert self.OLD_KEY not in output
        for value in self.stored.values():
            if value:
                assert value not in output
        # nor the plaintext
        for model, field_name in self.FIELDS:
            for name in self.instances:
                assert f"{name} {model._meta.label}.{field_name}" not in output

    def test_encrypted_fields(self):
        # every field that the migrations encrypted is re-encrypted
        migrated = {
            ("orgs.Organization", field_name)
            for field_name in importlib.import_module("seed.lib.superperms.orgs.migrations.0048_encrypt_credentials").SECRET_FIELDS
        } | {
            (f"seed.{model_name}", field_name)
            for model_name, field_name, _ in importlib.import_module("seed.migrations.0260_encrypt_credentials").SECRET_FIELDS
        }
        assert migrated <= {(model._meta.label, field_name) for model, field_name in self.FIELDS}
        for model, field_name in self.FIELDS:
            assert isinstance(model._meta.get_field(field_name), models.TextField)

    def test_reencrypt(self):
        modified = Organization.objects.get(pk=self.instances["old"][Organization].pk).modified
        stdout, stderr = self.call()

        stored = self.stored_values()
        for (model, field_name, name), value in stored.items():
            with self.subTest(field=f"{model._meta.label}.{field_name}", name=name):
                if name == "old":
                    assert is_encrypted(value)
                    assert decrypt_secret(value) == f"old {model._meta.label}.{field_name}"
                else:
                    # values encrypted with SECRET_KEY or an unknown key, and empty values, are unchanged
                    assert value == self.stored[(model, field_name, name)]
        # the rows are updated without saving the models
        assert Organization.objects.get(pk=self.instances["old"][Organization].pk).modified == modified

        # values that can't be decrypted are reported by primary key, and nothing is reported by value
        for model, field_name in self.FIELDS:
            label = f"{model._meta.label}.{field_name}"
            with self.subTest(field=label):
                assert f"{label}: 1 re-encrypted, 1 already encrypted with SECRET_KEY, 1 decrypted by neither" in stdout
                for name, instances in self.instances.items():
                    reported = f"{label} pk={instances[model].pk}:" in stdout
                    assert reported == (name == "unknown")
        assert f"Re-encrypted {len(self.FIELDS)} credentials with SECRET_KEY." in stdout
        assert f"{len(self.FIELDS)} credentials (listed above) are decrypted by neither" in stderr
        self.assert_no_secrets_in(stdout + stderr)

        # running it again changes nothing, and fails since only values that can't be decrypted remain
        with pytest.raises(CommandError, match=f"decrypted none of the {len(self.FIELDS)} credentials"):
            self.call()
        assert self.stored_values() == stored

        # and succeeds once those are re-entered
        for model, field_name in self.FIELDS:
            model.objects.filter(pk=self.instances["unknown"][model].pk).update(**{field_name: encrypt_secret("re-entered")})
        stdout, _ = self.call()
        assert "Nothing to re-encrypt" in stdout

    def test_dry_run(self):
        stdout, _ = self.call("--dry-run")

        self.assert_unchanged()
        assert "orgs.Organization.mapquest_api_key: 1 to re-encrypt, 1 already encrypted with SECRET_KEY" in stdout
        assert f"Dry run: {len(self.FIELDS)} credentials would be re-encrypted with SECRET_KEY. Nothing was saved." in stdout
        self.assert_no_secrets_in(stdout)

    def test_prompts_for_the_old_key(self):
        stdin = mock.Mock(isatty=mock.Mock(return_value=True))
        with mock.patch("getpass.getpass", return_value=self.OLD_KEY) as getpass:
            stdout, _ = self.call(old_key=None, stdin=stdin)

        getpass.assert_called_once_with("Old SECRET_KEY: ")
        assert f"Re-encrypted {len(self.FIELDS)} credentials" in stdout
        assert decrypt_secret(self.stored_values()[(Organization, "audit_template_password", "old")])

    def test_invalid_old_keys(self):
        cases = [
            # not interactive, and no key in the environment
            (None, "Set OLD_SECRET_KEY"),
            ("", "can't be empty"),
            (settings.SECRET_KEY, "is the current SECRET_KEY"),
            # a key that decrypts nothing
            ("not-the-old-key", f"decrypted none of the {2 * len(self.FIELDS)} credentials"),
        ]
        for old_key, message in cases:
            with self.subTest(old_key=old_key), pytest.raises(CommandError, match=message):
                self.call(old_key=old_key)
            self.assert_unchanged()

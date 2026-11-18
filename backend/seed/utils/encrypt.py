"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

Encryption for third-party credentials (e.g., the Audit Template, Salesforce, BETTER, and MapQuest keys).

Secrets are encrypted with Fernet (AES-128-CBC with an HMAC-SHA256 tag and a random IV) using a key derived from
`SECRET_KEY` (not `SECRET_KEY_FALLBACKS`). Changing `SECRET_KEY` makes the stored secrets undecryptable until the
`reencrypt_credentials` management command re-encrypts them with the new key (see `reencrypt_column`).
Stored values are prefixed with `PREFIX`; empty values are stored as-is so "is it configured?" checks keep working.

The passwords used to be signed, not encrypted, with `django.core.signing`, and the other credentials were stored in
plaintext. The migration helpers at the bottom of this module encrypt those values and are used by the orgs 0048 and
seed 0260 migrations, so they must stay importable.
"""

import base64
import functools
import json
import logging
import re
from collections import Counter, defaultdict
from enum import StrEnum
from typing import overload

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings
from django.core import signing
from django.utils.encoding import force_bytes

logger = logging.getLogger(__name__)

# Marks an encrypted value; "$" is in neither the Fernet token alphabet nor the legacy signed format
PREFIX = "fernet$"

# Maximum length of a secret in plaintext characters (the encrypted value is longer)
MAX_SECRET_LENGTH = 128

# Separates these keys from Django's other uses of SECRET_KEY
_HKDF_INFO = b"seed.utils.encrypt:fernet:v1"

# Every field that stores a secret encrypted with `encrypt_secret`, by model label
ENCRYPTED_FIELDS = {
    "orgs.Organization": ("audit_template_password", "at_organization_token", "better_analysis_api_key", "mapquest_api_key"),
    "seed.SalesforceConfig": ("password", "security_token"),
    "seed.BBSalesforceConfig": ("client_secret",),
}


class SecretDecryptionError(Exception):
    """A stored secret can't be decrypted. The message never includes the value."""


@functools.lru_cache(maxsize=8)
def secret_key_fernet(secret_key: str | bytes) -> Fernet:
    """
    The Fernet that encrypts secrets with a SECRET_KEY. Pass it instead of the key itself, so that the key isn't in
    the frame locals that error reporting (e.g., Sentry) captures.
    """
    # Cached by key so that changed settings (e.g., `override_settings` in tests) use the new key.
    # SECRET_KEY is a high-entropy key rather than a password, so HKDF (without key stretching) is sufficient.
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=_HKDF_INFO).derive(force_bytes(secret_key))
    return Fernet(base64.urlsafe_b64encode(key))


def is_encrypted(value: object) -> bool:
    """Whether a stored value is in the encrypted format (without checking that it can be decrypted)"""
    return isinstance(value, str) and value.startswith(PREFIX)


@overload
def encrypt_secret(plaintext: str) -> str: ...
@overload
def encrypt_secret(plaintext: None) -> None: ...
def encrypt_secret(plaintext: str | None) -> str | None:
    """Encrypt a secret for storage. None and "" are returned unchanged."""
    if plaintext is None:
        return None
    if not isinstance(plaintext, str):
        raise TypeError(f"encrypt_secret() expects a str or None, not {type(plaintext).__name__}")
    if not plaintext:
        return ""

    token = secret_key_fernet(settings.SECRET_KEY).encrypt(plaintext.encode("utf-8"))
    return PREFIX + token.decode("ascii")


def _decrypt(stored: str, fernet: Fernet) -> str:
    if not is_encrypted(stored):
        raise SecretDecryptionError("the value is not encrypted")

    try:
        return fernet.decrypt(stored[len(PREFIX) :].encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        # `from None` keeps the value (included in Unicode errors) out of tracebacks
        raise SecretDecryptionError("SECRET_KEY doesn't decrypt it (if SECRET_KEY was changed, run reencrypt_credentials)") from None


def decrypt_secret_strict(stored: str) -> str:
    """Decrypt a stored secret, raising `SecretDecryptionError` if it isn't encrypted or SECRET_KEY doesn't decrypt it"""
    return _decrypt(stored, secret_key_fernet(settings.SECRET_KEY))


@functools.lru_cache(maxsize=1024)
def _warn_once(context: str, reason: str) -> None:
    # Limits a misconfigured key to one warning per stored secret per process
    logger.warning("Cannot decrypt %s: %s", context, reason)


def decrypt_secret(stored: str | None, *, context: str = "a stored secret") -> str:
    """
    Decrypt a stored secret. Returns "" for an empty value and, with a warning, for one that can't be decrypted.

    A secret is never encrypted as "", so a non-empty stored value that decrypts to "" can't be decrypted.
    `context` identifies the secret in the warning (e.g., "organization 1 audit_template_password") and
    must not include the value.
    """
    if not stored:
        return ""

    try:
        return decrypt_secret_strict(stored)
    except SecretDecryptionError as e:
        _warn_once(context, str(e))
        return ""


@overload
def encrypt_if_changed(stored: str | None, plaintext: str, *, context: str = ...) -> str: ...
@overload
def encrypt_if_changed(stored: str | None, plaintext: None, *, context: str = ...) -> None: ...
def encrypt_if_changed(stored: str | None, plaintext: str | None, *, context: str = "a stored secret") -> str | None:
    """
    Return the value to store when a client submits `plaintext` for a secret currently stored as `stored`.

    Submitting the value the client was shown (the decrypted secret, or "" for one that can't be decrypted) keeps
    the stored value, so saving a form doesn't re-encrypt an unchanged secret or discard one that was encrypted
    with an old SECRET_KEY (which `reencrypt_credentials` can still re-encrypt). None clears the secret.
    """
    if plaintext is None:
        return None
    if not isinstance(plaintext, str):
        raise TypeError(f"encrypt_if_changed() expects a str or None, not {type(plaintext).__name__}")
    if stored and plaintext == decrypt_secret(stored, context=context):
        return stored

    return encrypt_secret(plaintext)


# Migration helpers. Legacy passwords were signed by `django.core.signing.Signer(salt=SECRET_KEY)`: the URL-safe
# base64 of the JSON plaintext, a colon, and the base64 HMAC-SHA256 signature.
_LEGACY_SIGNED_FORMAT = re.compile(r"[A-Za-z0-9_-]+:[A-Za-z0-9_-]{43}")


class LegacySecretState(StrEnum):
    ENCRYPTED = "already encrypted"
    UNDECRYPTABLE = "encrypted, but SECRET_KEY doesn't decrypt it"
    SIGNED = "signed"
    SIGNED_UNVERIFIED = "signed with a key that is not configured"
    SIGNED_NON_STRING = "signed value that is not a string"
    SIGNED_INVALID_STRING = "signed string that is not valid Unicode, cleared"
    PLAINTEXT = "not signed"


# States that are reported by primary key since they may need attention (and plaintext in a signed column)
_FLAGGED_STATES = {
    LegacySecretState.UNDECRYPTABLE,
    LegacySecretState.SIGNED_UNVERIFIED,
    LegacySecretState.SIGNED_NON_STRING,
    LegacySecretState.SIGNED_INVALID_STRING,
}

_NOT_SIGNED = object()


def _decode_legacy_signed(value: str) -> object:
    """Return the payload of a legacy signed value without verifying its signature, or `_NOT_SIGNED`"""
    if not _LEGACY_SIGNED_FORMAT.fullmatch(value):
        return _NOT_SIGNED
    try:
        return json.loads(signing.b64_decode(value.rsplit(":", 1)[0].encode()))
    except ValueError:
        return _NOT_SIGNED


def _legacy_signature_verifies(value: str) -> bool:
    # The legacy format used SECRET_KEY as both the key and the salt
    key = settings.SECRET_KEY
    try:
        signing.Signer(key=key, salt=key, fallback_keys=[]).unsign(value)
    except signing.BadSignature:
        return False
    return True


def convert_legacy_secret(value: str | None, *, signed: bool = True) -> tuple[str | None, LegacySecretState | None]:
    """
    Convert a stored secret to the encrypted format, returning the value to store and its original state.

    Empty values return a state of None. Encrypted values are returned unchanged, so conversion is idempotent.
    Other values are encrypted as plaintext unless `signed` (the column held legacy signed passwords), in which case
    legacy signed values are decoded even if the signature can't be verified (signing never hid the plaintext).
    The old view signed False when the password was omitted, so a signed None or boolean converts to "". The old
    views also signed strings with lone surrogates (from JSON escapes), which can't be encoded, so they convert to "".
    """
    if not value:
        return value, None

    if is_encrypted(value):
        try:
            decrypt_secret_strict(value)
        except SecretDecryptionError:
            return value, LegacySecretState.UNDECRYPTABLE
        return value, LegacySecretState.ENCRYPTED

    payload = _decode_legacy_signed(value) if signed else _NOT_SIGNED
    if payload is _NOT_SIGNED:
        return encrypt_secret(value), LegacySecretState.PLAINTEXT

    state = LegacySecretState.SIGNED if _legacy_signature_verifies(value) else LegacySecretState.SIGNED_UNVERIFIED
    if isinstance(payload, str):
        plaintext = payload
        try:
            plaintext.encode("utf-8")
        except UnicodeEncodeError:
            # it could never have been sent to the service
            return "", LegacySecretState.SIGNED_INVALID_STRING
    elif payload is None or isinstance(payload, bool):
        plaintext = ""
    else:
        state = LegacySecretState.SIGNED_NON_STRING
        plaintext = str(payload) if isinstance(payload, (int, float)) else ""

    return encrypt_secret(plaintext), state


def _stored_secrets(model, field_name: str, *, lock: bool = False) -> list[tuple[int, str]]:
    queryset = model._base_manager.exclude(**{f"{field_name}__isnull": True}).exclude(**{field_name: ""}).order_by("pk")
    if lock:
        # FOR NO KEY UPDATE blocks concurrent saves of these rows, but not inserts of rows that reference them
        queryset = queryset.select_for_update(no_key=True)
    return list(queryset.values_list("pk", field_name))


def encrypt_column(model, field_name: str, *, signed: bool) -> Counter:
    """
    Encrypt every stored value of a model's secret field (a forward data migration). `signed` is whether the column
    held legacy signed passwords rather than plaintext. Values are written with `update()`, so no signals run, and
    values that need attention are reported by primary key, never by value.
    """
    label = f"{model._meta.label}.{field_name}"
    counts: Counter = Counter()
    for pk, value in _stored_secrets(model, field_name):
        new_value, state = convert_legacy_secret(value, signed=signed)
        counts[state] += 1
        if new_value != value:
            model._base_manager.filter(pk=pk).update(**{field_name: new_value})
        if state in _FLAGGED_STATES or (signed and state == LegacySecretState.PLAINTEXT):
            print(f"{label} pk={pk}: {state}")

    if counts[LegacySecretState.SIGNED_UNVERIFIED]:
        print(
            f"{label}: values signed with a key that is not configured were decrypted without verifying their signatures. "
            "If every value is affected, check that this migration ran with the application's SECRET_KEY."
        )
    if counts[LegacySecretState.UNDECRYPTABLE]:
        print(f"{label}: values that SECRET_KEY doesn't decrypt were left unchanged; if SECRET_KEY was changed, run reencrypt_credentials.")
    if counts:
        print(f"{label}: {', '.join(f'{count} {state}' for state, count in counts.items())}")
    return counts


class ReencryptState(StrEnum):
    REENCRYPTED = "re-encrypted"
    CURRENT = "already encrypted with SECRET_KEY"
    UNDECRYPTABLE = "decrypted by neither the old key nor SECRET_KEY"


def reencrypt_secret(stored: str, old_fernet: Fernet) -> tuple[str, ReencryptState]:
    """
    Re-encrypt a stored secret that was encrypted with an old SECRET_KEY (whose `secret_key_fernet` is `old_fernet`)
    with the current SECRET_KEY, returning the value to store and its state. Values that neither key decrypts are
    returned unchanged.
    """
    try:
        decrypt_secret_strict(stored)
    except SecretDecryptionError:
        pass
    else:
        return stored, ReencryptState.CURRENT

    try:
        # not assigned to a local, which error reporting would capture
        return encrypt_secret(_decrypt(stored, old_fernet)), ReencryptState.REENCRYPTED
    except SecretDecryptionError:
        return stored, ReencryptState.UNDECRYPTABLE


def reencrypt_column(model, field_name: str, old_fernet: Fernet, *, dry_run: bool = False) -> dict[ReencryptState, list[int]]:
    """
    Re-encrypt every stored value of a model's secret field that was encrypted with an old SECRET_KEY (whose
    `secret_key_fernet` is `old_fernet`) with the current SECRET_KEY, returning the primary keys of the rows in each
    state. Unless `dry_run`, this must run in a transaction: the rows are locked until it ends, so values saved
    meanwhile aren't overwritten. The lock doesn't stop a save of a row loaded before then from writing the old value
    back, so `reencrypt_credentials` is run with SEED in maintenance mode. Values are written with `update()`, so no
    signals run.
    """
    pks: defaultdict[ReencryptState, list[int]] = defaultdict(list)
    for pk, stored in _stored_secrets(model, field_name, lock=not dry_run):
        new_value, state = reencrypt_secret(stored, old_fernet)
        pks[state].append(pk)
        if new_value != stored and not dry_run:
            model._base_manager.filter(pk=pk).update(**{field_name: new_value})
    return dict(pks)

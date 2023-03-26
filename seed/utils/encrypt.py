"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import os

from django.conf import settings
from django.core import signing


def encrypt(password: str) -> str:
    """Encrypts a password"""

    secret = get_secret()

    signer = signing.Signer(salt=secret)
    enc = signer.sign_object(password)
    return enc


def decrypt(password: str):
    """ Decrypts a password """

    secret = get_secret()

    signer = signing.Signer(salt=secret)
    try:
        enc = signer.unsign_object(password)
        return enc, None
    except signing.BadSignature as e:
        print("Error: Cannot decrypt password.")
        return None, e


def get_secret() -> str:

    if settings.SECRET_KEY:
        secret = settings.SECRET_KEY
    else:
        secret = os.environ.get('SECRET_KEY', None)

    return secret

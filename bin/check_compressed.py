# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import sys

from django.core.management import CommandError, call_command

try:
    call_command("compress", force=True)
    print("compression passed")
except CommandError as e:
    print("compression failed")
    print(str(e))
    sys.exit(1)

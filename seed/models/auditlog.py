"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

AUDIT_IMPORT = 0
AUDIT_USER_EDIT = 1
AUDIT_USER_CREATE = 2

DATA_UPDATE_TYPE = ((AUDIT_IMPORT, "ImportFile"), (AUDIT_USER_EDIT, "UserEdit"), (AUDIT_USER_CREATE, "UserCreate"))

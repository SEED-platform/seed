"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from __future__ import unicode_literals

AUDIT_IMPORT = 0
AUDIT_USER_EDIT = 1
AUDIT_USER_CREATE = 2

DATA_UPDATE_TYPE = (
    (AUDIT_IMPORT, "ImportFile"),
    (AUDIT_USER_EDIT, "UserEdit"),
    (AUDIT_USER_CREATE, "UserCreate")
)

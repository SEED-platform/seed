from __future__ import unicode_literals

from django.db import models
from django.contrib.contenttypes.fields import GenericRelation


AUDIT_IMPORT = 0
AUDIT_USER_EDIT = 1

DATA_UPDATE_TYPE = (
    (AUDIT_IMPORT, "ImportFile"),
    ("AUDIT_USER_EDIT", "UserEdit"))

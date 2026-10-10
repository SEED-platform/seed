"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.contrib.gis.db.backends.postgis.base import DatabaseWrapper as PostGISDatabaseWrapper

from .creation import DatabaseCreation


class DatabaseWrapper(PostGISDatabaseWrapper):
    creation_class = DatabaseCreation

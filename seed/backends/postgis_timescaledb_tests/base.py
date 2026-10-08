from django.contrib.gis.db.backends.postgis.base import DatabaseWrapper as PostGISDatabaseWrapper

from .creation import DatabaseCreation


class DatabaseWrapper(PostGISDatabaseWrapper):
    creation_class = DatabaseCreation

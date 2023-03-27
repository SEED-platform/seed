# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import models


class NotDeletedManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).exclude(deleted=True)

    def get_all(self, *args, **kwargs):
        """Method to return ALL ImportFiles, including the ones where `deleted == True` which are normally excluded.
        This is used for database/filesystem cleanup."""
        return super().get_queryset(*args, **kwargs)

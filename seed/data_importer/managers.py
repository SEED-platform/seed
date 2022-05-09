# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
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

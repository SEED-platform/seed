# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.db import models


class NotDeletedManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).exclude(deleted=True)

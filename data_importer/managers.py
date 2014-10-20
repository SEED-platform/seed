"""
:copyright: (c) 2014 Building Energy Inc
"""
from django.db import models

class NotDeletedManager(models.Manager):
    use_for_related_fields = True

    def get_query_set(self, *args, **kwargs):
        return super(NotDeletedManager, self).get_query_set(*args, **kwargs).exclude(deleted=True)

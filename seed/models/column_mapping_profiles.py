# !/usr/bin/env python
# encoding: utf-8

from django.db import models
from django.contrib.postgres.fields import JSONField

from seed.lib.superperms.orgs.models import Organization


class ColumnMappingProfile(models.Model):
    NORMAL = 0
    BUILDINGSYNC_DEFAULT = 1
    BUILDINGSYNC_CUSTOM = 2

    COLUMN_MAPPING_PROFILE_TYPES = (
        (NORMAL, 'Normal'),
        (BUILDINGSYNC_DEFAULT, 'BuildingSync Default'),
        (BUILDINGSYNC_CUSTOM, 'BuildingSync Custom')
    )

    name = models.CharField(max_length=255, blank=False)
    mappings = JSONField(default=list, blank=True)

    organizations = models.ManyToManyField(Organization)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    profile_type = models.IntegerField(choices=COLUMN_MAPPING_PROFILE_TYPES, default=NORMAL)

    @classmethod
    def get_profile_type(cls, profile_type):
        """Returns the integer value for a profile type. Raises exception when
        profile_type is invalid.

        :param profile_type: int | str
        :return: str
        """
        if isinstance(profile_type, int):
            return profile_type
        types_dict = dict((v, k) for k, v in cls.COLUMN_MAPPING_PROFILE_TYPES)
        if profile_type in types_dict:
            return types_dict[profile_type]
        raise Exception(f'Invalid profile type "{profile_type}"')

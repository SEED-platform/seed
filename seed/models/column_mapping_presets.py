# !/usr/bin/env python
# encoding: utf-8

from django.db import models
from django.contrib.postgres.fields import JSONField

from seed.lib.superperms.orgs.models import Organization


class ColumnMappingPreset(models.Model):
    NORMAL = 0
    BUILDINGSYNC_DEFAULT = 1
    BUILDINGSYNC_CUSTOM = 2

    COLUMN_MAPPING_PRESET_TYPES = (
        (NORMAL, 'Normal'),
        (BUILDINGSYNC_DEFAULT, 'BuildingSync Default'),
        (BUILDINGSYNC_CUSTOM, 'BuildingSync Custom')
    )

    name = models.CharField(max_length=255, blank=False)
    mappings = JSONField(default=list, blank=True)

    organizations = models.ManyToManyField(Organization)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    preset_type = models.IntegerField(choices=COLUMN_MAPPING_PRESET_TYPES, default=NORMAL)

    @classmethod
    def get_preset_type(cls, preset_type):
        """Returns the integer value for a preset type. Raises exception when
        preset_type is invalid.

        :param preset_type: int | str
        :return: str
        """
        if isinstance(preset_type, int):
            return preset_type
        types_dict = dict((v, k) for k, v in cls.COLUMN_MAPPING_PRESET_TYPES)
        if preset_type in types_dict:
            return types_dict[preset_type]
        raise Exception(f'Invalid preset type "{preset_type}"')

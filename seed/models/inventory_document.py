# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import models

from seed.models import Property


class InventoryDocument(models.Model):

    UNKNOWN = 0
    PDF = 1
    OSM = 2
    IDF = 3
    DXF = 4

    FILE_TYPES = (
        (UNKNOWN, 'Unknown'),
        (PDF, 'PDF'),
        (OSM, 'OSM'),
        (IDF, 'IDF'),
        (DXF, 'DXF')
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='inventory_documents',
        null=True,
        blank=True
    )

    created = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to="inventory_documents", max_length=500, blank=True, null=True)
    file_type = models.IntegerField(choices=FILE_TYPES, default=UNKNOWN)
    filename = models.CharField(blank=True, max_length=255)

    def __str__(self):
        return 'Inventory Document - %s' % (self.pk)

    @classmethod
    def str_to_file_type(cls, file_type):
        """
        convert an integer or string of the file_type to the integer that will be saved

        :param file_type: integer or string, file type name
        :return: integer, enum integer
        """
        if not file_type:
            return None

        # If it is already an integer, then move along.
        try:
            if int(file_type):
                return int(file_type)
        except ValueError:
            pass

        value = [y[0] for x, y in enumerate(cls.FILE_TYPES) if
                 y[1].lower() == file_type.lower()]
        if len(value) == 1:
            return value[0]
        else:
            return None

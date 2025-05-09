"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
import locale
import logging
import re
import string

from django.conf import settings
from django.db import models

from seed.models import Organization

_log = logging.getLogger(__name__)

BUILDINGSYNC_MEASURES = [
    {
        "name": "RetrofitWithCFLs",
        "display_name": "Retrofit with CFLs",
        "category": "LightingImprovements",
        "category_name": "Lighting Improvements",
    }
]


def _snake_case(display_name):
    """
    Convert the BuildingSync measure display names into reasonable snake_case for storing into
    database.

    :param display_name: BuildingSync measure display name
    :return: string
    """
    str_re = re.compile(f"[{re.escape(string.punctuation)}]")
    str = str_re.sub(" ", display_name)
    str = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", str)
    str = re.sub("([a-z0-9])([A-Z])", r"\1_\2", str).lower()
    return re.sub(" +", "_", str)


class Measure(models.Model):
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    category_display_name = models.CharField(max_length=255)
    schema_type = models.CharField(max_length=255, default="BuildingSync")
    schema_version = models.CharField(max_length=15, default="1.0.0")

    # relationships
    properties = models.ManyToManyField("PropertyState", through="PropertyMeasure")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Measure - {self.category}.{self.name}"

    class Meta:
        ordering = ["-created"]
        get_latest_by = "created"
        unique_together = ("organization", "category", "name", "schema_version")

    @classmethod
    def populate_measures(cls, organization_id, schema_type="BuildingSync", schema_version="1.0.0"):
        """
        Populate the list of measures from the BuildingSync
        Default is BuildingSync 1.0.0

        :param organization_id: integer, ID of the organization to populate measures
        :return:
        """
        # find enumerations.json file matching schema version
        # filename syntax convention is enumerations_v1_0_0.json (replace dots with underscores)
        filename = f"seed/building_sync/enumerations/enumerations_v{schema_version.replace('.', '_')}.json"
        with open(filename, encoding=locale.getpreferredencoding(False)) as f:
            data = json.load(f)

            for datum in data:
                # "name": "MeasureName",
                # "sub_name": "AdvancedMeteringSystems",
                # "documentation": "Advanced Metering Systems",
                # "enumerations": [
                #                     "Install advanced metering systems",
                #                     "Clean and/or repair",
                #                     "Implement training and/or documentation",
                #                     "Upgrade operating protocols, calibration, and/or sequencing",
                #                     "Other"
                #                 ],
                if datum["name"] == "MeasureName":
                    for enum in datum["enumerations"]:
                        Measure.objects.get_or_create(
                            organization_id=organization_id,
                            category=_snake_case(datum["sub_name"]),
                            category_display_name=datum["documentation"],
                            name=_snake_case(enum),
                            display_name=enum,
                            schema_type=schema_type,
                            schema_version=schema_version,
                        )

    @classmethod
    def validate_measures(cls, data, schema_version=settings.BUILDINGSYNC_VERSION):
        """
        Take a list of measure ids or measure names and return just a list of ids.

        :param data: list, either category.name of measure or primary key
        :param schema_version: defaults to Default Version specified in settings file
        :return: list of integers, the list are primary key of measures
        """
        if len(data) > 0:
            resp = []
            for d in data:
                try:
                    if isinstance(d, int) or d.isdigit():
                        # validate that the measure exists
                        resp.append(Measure.objects.get(pk=d).pk)
                    elif len(d) == 0:
                        continue
                    else:
                        if "." not in d or len(d) == 1:
                            _log.error(f"Invalid measure name: {d}")
                            continue

                        measure = d.split(".")
                        resp.append(Measure.objects.get(category=measure[0], name=measure[1], schema_version=schema_version).pk)
                except Measure.DoesNotExist:
                    _log.error(f"Could not find measure for {d}")
            return resp
        else:
            return []

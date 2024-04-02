# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import csv
import locale
import os

from django.db import models

from seed.lib.superperms.orgs.models import Organization


class ColumnMappingProfile(models.Model):
    NORMAL = 0
    BUILDINGSYNC_DEFAULT = 1
    BUILDINGSYNC_CUSTOM = 2

    COLUMN_MAPPING_PROFILE_TYPES = (
        (NORMAL, 'Normal'),
        (BUILDINGSYNC_DEFAULT, 'BuildingSync Default'),
        (BUILDINGSYNC_CUSTOM, 'BuildingSync Custom'),
    )

    name = models.CharField(max_length=255, blank=False)
    mappings = models.JSONField(default=dict, blank=True)

    # TODO: Need to verify that we want ManyToMany here. This might be needed for
    # the BuildingSync related profiles, but the dev database appears to just
    # have one org per profile.
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
        types_dict = {v: k for k, v in cls.COLUMN_MAPPING_PROFILE_TYPES}
        if profile_type in types_dict:
            return types_dict[profile_type]
        raise Exception(f'Invalid profile type "{profile_type}"')

    @classmethod
    def create_from_file(
        cls, filename: str, org: Organization, profile_name: str, profile_type: int = NORMAL, overwrite_if_exists: bool = False
    ):
        """Generate a ColumnMappingProfile from a set of mappings in a file. The format of the file
        is slightly different from the Column.create_mappings_from_file, but is the same format as
        the file that you download from the column mappings page within SEED.

        Args:
            filename (str): path to the file to create the mappings from.
            org (Organization): Instance object of the organization
            profile_name (str): Name of the new profile to create
            profile_type (int, optional): Type of profile, will be NORMAL for most cases. Defaults to NORMAL.
            overwrite_if_exists (bool, optional): If the mapping exists, then overwrite. Defaults to False.

        Raises:
            Exception: If the file does not exist, mappings are empty, or the profile already exists and overwrite_if_exists is False.
        """
        mappings = []
        if os.path.isfile(filename):
            with open(filename, newline=None, encoding=locale.getpreferredencoding(False)) as csvfile:
                csvreader = csv.reader(csvfile)
                next(csvreader)  # skip header
                for row in csvreader:
                    data = {
                        'from_field': row[0],
                        'from_units': row[1],
                        'to_table_name': row[2],
                        'to_field': row[3],
                    }
                    mappings.append(data)
        else:
            raise Exception(f'Mapping file does not exist: {filename}')

        if len(mappings) == 0:
            raise Exception(f'No mappings in file: {filename}')

        # Because this object has a many to many on orgs (which I argue shouldn't), then
        # first, get all the org's mapping profiles
        profiles = org.columnmappingprofile_set.all()

        # second, get or create the profile now that we are only seeing my 'orgs' profiles
        profile, created = profiles.get_or_create(name=profile_name, profile_type=profile_type)
        if not created and not overwrite_if_exists:
            raise Exception(f'ColumnMappingProfile already exists, not overwriting: {profile_name}')

        # Do I need to confirm that the mappings are defined in the Columns world?
        profile.mappings = mappings
        profile.save()

        # make sure that it is added to the org
        org.columnmappingprofile_set.add(profile)

        return profile

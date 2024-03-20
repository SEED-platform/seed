# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from seed.lib.mcm import reader
from seed.lib.superperms.orgs.models import Organization


class AccessLevelInstancesParser(object):
    """
    This class parses and validates different details about access level instances
    Import File - to be created before execution.

    The expected input is a csv/xlsx. The columns headers should be the names of the
    access hierarchy levels, omitting the root level since it is the same across all. Example:

        - Level 2 Name : string
        - Level 3 Name : string
        - ...
    """

    def __init__(self, org_id, access_level_instances_details, num_levels):
        # defaulted to None to show it hasn't been cached yet
        self.access_level_instances_details = access_level_instances_details
        self._org_id = org_id
        self.num_levels = num_levels

    @classmethod
    def factory(cls, access_level_instances_file, org_id):
        """Factory function for accessLevelInstancesParser

        :param access_level_instances_file: File
        :param org_id: int
        :return: AccessLevelInstancesParser
        """
        parser = reader.MCMParser(access_level_instances_file)
        raw_data = list(parser.data)

        try:
            keys = list(raw_data[0].keys())
        except IndexError:
            raise ValueError("File has no rows")

        level_names = keys
        # already checked that headers match level names before saving file
        # raise ValueError if not
        AccessLevelInstancesParser._access_level_names(org_id)

        num_levels = len(level_names)

        return cls(org_id, raw_data, num_levels)

    @classmethod
    def _access_level_names(cls, org_id):
        access_level_names = []
        if org_id:
            access_level_names = Organization.objects.get(pk=org_id).access_level_names
        return access_level_names

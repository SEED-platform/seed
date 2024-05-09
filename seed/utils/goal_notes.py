# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from seed.models import AccessLevelInstance

def get_permission_data(data, access_level_instance_id):
    # leaf users are only permitted to update 'resolution'
    access_level_instance = AccessLevelInstance.objects.get(pk=access_level_instance_id)
    write_permission = access_level_instance.is_root() or not access_level_instance.is_leaf()
    if write_permission:
        return data

    return {"resolution": data.get("resolution")} if "resolution" in data else {}

"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from seed.models import AccessLevelInstance

# the goal note fields users may update (a note's goal and property are fixed)
GOAL_NOTE_FIELDS = ("question", "resolution", "passed_checks", "new_or_acquired")


def get_permission_data(data, access_level_instance_id):
    # leaf users are only permitted to update 'resolution'
    access_level_instance = AccessLevelInstance.objects.get(pk=access_level_instance_id)
    write_permission = access_level_instance.is_root() or not access_level_instance.is_leaf()
    fields = GOAL_NOTE_FIELDS if write_permission else ("resolution",)

    return {field: data[field] for field in fields if field in data}

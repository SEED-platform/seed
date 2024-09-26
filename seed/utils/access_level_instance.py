from django.core.exceptions import ObjectDoesNotExist

from seed.models import AccessLevelInstance


def access_level_filter(access_level_instance_id):
    try:
        access_level_instance = AccessLevelInstance.objects.get(pk=access_level_instance_id)
    except ObjectDoesNotExist:
        return {}

    return {"access_level_instance__lft__gte": access_level_instance.lft, "access_level_instance__rgt__lte": access_level_instance.rgt}

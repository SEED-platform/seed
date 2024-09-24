def access_level_filter(access_level_instance):
    if not access_level_instance:
        return {}

    return {
        "access_level_instance__lft__gte": access_level_instance.lft,
        "access_level_instance__rgt__lte": access_level_instance.rgt
    } 
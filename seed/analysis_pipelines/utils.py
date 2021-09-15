def get_json_path(json_path, data):
    """very naive JSON path implementation. WARNING: it only handles key names that are dot separated
    e.g. 'key1.key2.key3'

    :param json_path: str
    :param data: dict
    :return: value, None if path not valid for dict
    """
    json_path = json_path.split('.')
    result = data
    for key in json_path:
        result = result.get(key, {})

    if type(result) is dict and not result:
        # path was probably not valid in the data...
        return None
    else:
        return result

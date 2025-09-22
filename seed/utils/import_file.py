import json

from seed.models import ColumnMapping, Cycle, ImportFile


def get_import_file_table_mappings(import_file_id):
    """
    Given an ImportFile, return the column mappings grouped by table
    for that file broken down by table name.

    The return is the same format as ColumnMapping.get_column_mappings_by_table_name
    but limited to the mappings specified in the ImportFile's cached_mapped_columns.

    ex return:
    {
        'PropertyState': {
            'address line 1': ('PropertyState', 'address_line_1', 'Address Line 1', False),
            'city': ('PropertyState', 'city', 'City', False),
            ...
        },
        ...
    }
    """
    try:
        import_file = ImportFile.objects.get(pk=import_file_id)
        org = import_file.cycle.organization
    except (ImportFile.DoesNotExist, Cycle.DoesNotExist):
        raise ValueError("No such resource.")

    org_mappings = ColumnMapping.get_column_mappings_by_table_name(org)
    cached_mappings = json.loads(import_file.cached_mapped_columns or "[]")

    result = {}
    for mapping in cached_mappings:
        table_name = mapping.get("to_table_name")
        from_field = mapping.get("from_field")
        if mapping_data := org_mappings.get(table_name, {}).get(from_field, ()):
            result.setdefault(table_name, {})[from_field] = mapping_data
    return result

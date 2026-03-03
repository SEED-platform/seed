import json
import logging

from seed.models import Column, ColumnMapping, ImportFile


def get_import_file_table_mappings(import_file_id):
    """
    Given an ImportFile, return the column mappings grouped by table
    for that file broken down by table name.

    The return is the same format as ColumnMapping.get_column_mappings_by_table_name
    but limited to the mappings specified in the ImportFile's cached_mapped_columns.

    Ali info is saved under the '' (empty string) key.

    ex return:
    {
        '': {
            '1st Gen': ('', '1st Gen', '', True),
        },
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
        org = import_file.import_record.super_organization
    except (ImportFile.DoesNotExist, AttributeError):
        logging.error(f"Unable to get Organization from ImportFile {import_file_id}")
        return {}

    ali_column_names = Column.objects.filter(
        organization=org,
        column_name__in=org.access_level_names,
        is_extra_data=True,
    ).values_list("column_name", flat=True)
    org_mappings = ColumnMapping.get_column_mappings_by_table_name(org)
    cached_mappings = json.loads(import_file.cached_mapped_columns or "[]")

    result = {}
    for mapping in cached_mappings:
        table_name = mapping.get("to_table_name")
        from_field = mapping.get("from_field")

        # Try to find the existing mapping, ali info will be placed under an empty table name. If neither exists, ignore.
        if mapping_data := org_mappings.get(table_name, {}).get(from_field, ()):
            result.setdefault(table_name, {})[from_field] = mapping_data
        elif from_field in ali_column_names:
            mapping_data = org_mappings.get("", {}).get(from_field, ())
            result.setdefault("", {})[from_field] = mapping_data

    return result

import json
import logging
from django.db.models import Count, Q

from seed.models import (
    Column,
    ColumnMapping,
    DATA_STATE_UNKNOWN,
    DATA_STATE_IMPORT,
    DATA_STATE_DELETE,
    ImportFile,
    PropertyState,
    TaxLotState
)


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

def verify_data_types(org_id, import_file_id):
    """
    To check for data type parsing errors, check non string fields for None values. 
    ex: If a column has a numeric data type, attempting to parse a string will result in None.
    This gives the user a warning there may be a data type mapping issue
    """
    import_file = ImportFile.objects.filter(id=import_file_id, import_record__super_organization_id=org_id).first()
    if not import_file:
        return
    mapped_cols = import_file.get_cached_mapped_columns
    if not import_file or not mapped_cols:
        return
    
    propertystate_ids = list(
        PropertyState.objects.filter(import_file=import_file)
        .exclude(data_state__in=[DATA_STATE_UNKNOWN, DATA_STATE_IMPORT, DATA_STATE_DELETE])
        .values_list("id", flat=True)
    )
    taxlotstate_ids = list(
        TaxLotState.objects.filter(import_file=import_file)
        .exclude(data_state__in=[DATA_STATE_UNKNOWN, DATA_STATE_IMPORT, DATA_STATE_DELETE])
        .values_list("id", flat=True)
    )

    if not len(propertystate_ids) and not len(taxlotstate_ids):
        return
    
    from datetime import datetime
    start = datetime.now()
    
    import_file.mapping_error_messages = ""

    # {column_name: display_name, ...} for canonical cols with numeric (non-text) data types
    column_map = dict(Column.objects
        .filter(organization_id=org_id, is_extra_data=False, derived_column_id__isnull=True)
        .exclude(data_type__in=['string', 'None'])
        .exclude(table_name='')
        .values_list('column_name', 'display_name')
    )
    # Check columns that are within import file's mapping AND column_map
    canonical_column_names = set(column_map.keys())
    property_column_names = [col_name for table, col_name in mapped_cols if table == "PropertyState" and col_name in canonical_column_names]
    taxlot_column_names = [col_name for table, col_name in mapped_cols if table == "TaxLotState" and col_name in canonical_column_names]

    columns_with_blanks = set()

    # create aggregations to check if null values exist for the selected column names
    # run query against import record inventory and count results
    if property_column_names:
        property_null_checks = {f"{field}_null": Count('id', filter=Q(**{f"{field}__isnull": True})) for field in property_column_names}
        property_counts = PropertyState.objects.filter(id__in=propertystate_ids).aggregate(**property_null_checks)
        columns_with_blanks.update([column_map[field] for field in property_column_names if property_counts[f"{field}_null"]])
    
    if taxlot_column_names:
        taxlot_null_checks = {f"{field}_null": Count('id', filter=Q(**{f"{field}__isnull": True})) for field in taxlot_column_names}
        taxlot_counts = TaxLotState.objects.filter(id__in=taxlotstate_ids).aggregate(**taxlot_null_checks)
        columns_with_blanks.update([column_map[field] for field in taxlot_column_names if taxlot_counts[f"{field}_null"]])

    if columns_with_blanks:
        col_string = ", ".join(sorted(columns_with_blanks))
        err_msg = (
            f"Blank values detected in columns: {col_string}. Review import file data or Save Mappings to ignore."
        )
        import_file.mapping_error_messages = err_msg

    import logging
    end = datetime.now()
    diff = end - start
    logging.error(f'>>> TOOK {diff.seconds}s, {diff.microseconds}micros')
    import_file.save()

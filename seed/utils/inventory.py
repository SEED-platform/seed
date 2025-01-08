from seed.models import Column, Property, PropertyAuditLog, PropertyState, PropertyView, TaxLot, TaxLotAuditLog, TaxLotState, TaxLotView
from seed.utils.match import get_matching_criteria_column_names


def create_inventory(inventory_type, org_id, cycle_id, access_level_instance_id, new_state_data):
    inventory_class, view_class, state_class, auditlog_class, cycle_query, viewset = _inventorty_config(inventory_type)

    # Create extra data columns if necessary
    extra_data = new_state_data.get("extra_data", {})
    for column in extra_data:
        Column.objects.get_or_create(is_extra_data=True, column_name=column, organization_id=org_id, table_name=state_class.__name__)

    # Create stub state
    state = state_class.objects.create(organization_id=org_id)
    # get_or_create existing inventory and view
    matching_columns = get_matching_criteria_column_names(org_id, state_class.__name__)
    filter_query = {col: new_state_data.get(col) for col in matching_columns if col in new_state_data}
    filter_query.update({"organization": org_id, cycle_query: cycle_id, f"{inventory_type}view__isnull": False})
    matching_state = state_class.objects.filter(**filter_query).first()
    if matching_state:
        view = getattr(matching_state, viewset).first()
        inventory = getattr(view, inventory_type)
    else:
        inventory = inventory_class.objects.create(organization_id=org_id, access_level_instance_id=access_level_instance_id)
        view_data = {"cycle_id": cycle_id, inventory_type: inventory, "state": state}
        view = view_class.objects.create(**view_data)

    auditlog_class.objects.create(organization_id=org_id, state=state, view=view, name="Form Creation")

    return view


def _inventorty_config(inventory_type):
    if inventory_type == "property":
        return Property, PropertyView, PropertyState, PropertyAuditLog, "propertyview__cycle", "propertyview_set"
    elif inventory_type == "taxlot":
        return TaxLot, TaxLotView, TaxLotState, TaxLotAuditLog, "taxlotview__cycle", "taxlotview_set"
    else:
        raise ValueError(f"Invalid inventory type: {inventory_type}")

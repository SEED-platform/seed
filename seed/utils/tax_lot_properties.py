import math
from collections import OrderedDict

from seed.models import ColumnListProfile, TaxLotProperty
from seed.serializers.meter_readings import MeterReadingSerializer
from seed.serializers.meters import MeterSerializer

def format_export_data(
        ids,
        org_id,
        profile_id,
        view_klass_str,
        view_klass,
        access_level_instance,
        column_profile,
        include_notes,
        include_meter_data,
        export_type,
        progress_data=False,
    ):
    # Set the first column to be the ID
    column_name_mappings = OrderedDict([("id", "ID")])
    column_ids, add_column_name_mappings, columns_from_database = ColumnListProfile.return_columns(org_id, profile_id, view_klass_str)
    column_name_mappings.update(add_column_name_mappings)

    select_related = ["state", "cycle"]
    prefetch_related = ["labels"]
    filter_str = {}
    if ids:
        filter_str["id__in"] = ids
    if hasattr(view_klass, "property"):
        select_related.append("property")
        filter_str["property__organization_id"] = org_id
        filter_str["property__access_level_instance__lft__gte"] = access_level_instance.lft
        filter_str["property__access_level_instance__rgt__lte"] = access_level_instance.rgt
        # always export the labels and notes
        column_name_mappings["property_notes"] = "Property Notes"
        column_name_mappings["property_labels"] = "Property Labels"

    elif hasattr(view_klass, "taxlot"):
        select_related.append("taxlot")
        filter_str["taxlot__organization_id"] = org_id
        filter_str["taxlot__access_level_instance__lft__gte"] = access_level_instance.lft
        filter_str["taxlot__access_level_instance__rgt__lte"] = access_level_instance.rgt
        # always export the labels and notes
        column_name_mappings["taxlot_notes"] = "Tax Lot Notes"
        column_name_mappings["taxlot_labels"] = "Tax Lot Labels"

    model_views = (
        view_klass.objects.select_related(*select_related).prefetch_related(*prefetch_related).filter(**filter_str).order_by("id")
    )
    if progress_data:
        progress_data.step("Exporting Inventory...")
    data = TaxLotProperty.serialize(model_views, column_ids, columns_from_database)

    derived_columns = column_profile.derived_columns.all() if column_profile is not None else []
    column_name_mappings.update({dc.name: dc.name for dc in derived_columns})
    if progress_data:
        progress_data.step("Exporting Inventory...")

    # export_type = request.data.get("export_type", "csv")

    # add labels, notes, and derived columns
    # include_notes = request.data.get("include_notes", True)
    batch_size = math.ceil(len(model_views) / 98)
    for i, record in enumerate(model_views):
        label_string = []
        note_string = []
        for label in list(record.labels.all().order_by("name")):
            label_string.append(label.name)
        if include_notes:
            for note in list(record.notes.all().order_by("created")):
                note_string.append(note.created.astimezone().strftime("%Y-%m-%d %I:%M:%S %p") + "\n" + note.text)

        if hasattr(record, "property"):
            data[i]["property_labels"] = ",".join(label_string)
            data[i]["property_notes"] = "\n----------\n".join(note_string) if include_notes else "(excluded during export)"

            # include_meter_data = request.data.get("include_meter_readings", False)
            if include_meter_data and export_type == "geojson":
                meters = []
                for meter in record.property.meters.all():
                    meters.append(MeterSerializer(meter).data)
                    meters[-1]["readings"] = []
                    for meter_reading in meter.meter_readings.all().order_by("start_time"):
                        meters[-1]["readings"].append(MeterReadingSerializer(meter_reading).data)

                data[i]["_meters"] = meters
        elif hasattr(record, "taxlot"):
            data[i]["taxlot_labels"] = ",".join(label_string)
            data[i]["taxlot_notes"] = "\n----------\n".join(note_string) if include_notes else "(excluded during export)"

        # add derived columns
        for derived_column in derived_columns:
            data[i][derived_column.name] = derived_column.evaluate(inventory_state=record.state)

        if batch_size > 0 and i % batch_size == 0 and progress_data:
            progress_data.step("Exporting Inventory...")

    # force the data into the same order as the IDs
    if ids:
        order_dict = {obj_id: index for index, obj_id in enumerate(ids)}
        if view_klass_str == "properties":
            view_id_str = "property_view_id"
        else:
            view_id_str = "taxlot_view_id"
        data.sort(key=lambda inventory_obj: order_dict[inventory_obj[view_id_str]])
    
    return data, column_name_mappings
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from itertools import chain
from typing import TYPE_CHECKING

from django.apps import apps
from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.timezone import make_naive
from quantityfield.units import ureg

from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models.columns import Column
from seed.serializers.pint import DEFAULT_UNITS
from seed.utils.geocode import bounding_box_wkt, long_lat_wkt
from seed.utils.ubid import centroid_wkt

if TYPE_CHECKING:
    from seed.models.properties import PropertyView
    from seed.models.tax_lots import TaxLotView

logger = logging.getLogger(__name__)


class TaxLotProperty(models.Model):
    property_view = models.ForeignKey("PropertyView", on_delete=models.CASCADE)
    taxlot_view = models.ForeignKey("TaxLotView", on_delete=models.CASCADE)
    cycle = models.ForeignKey("Cycle", on_delete=models.CASCADE)

    # If there is a complex TaxLot/Property association, this field
    # lists the "main" tax lot that Properties should be reported under.
    # User controlled flag.
    primary = models.BooleanField(default=True)

    def __str__(self):
        return f"M2M Property View {self.property_view_id} / TaxLot View {self.taxlot_view_id}"

    class Meta:
        unique_together = (
            "property_view",
            "taxlot_view",
        )
        index_together = [["cycle", "property_view"], ["cycle", "taxlot_view"], ["property_view", "taxlot_view"]]

    @classmethod
    def extra_data_to_dict_with_mapping(cls, instance, mappings, fields=None, units={}):
        """
        Convert the extra data to a dictionary with a name mapping for the keys

        :param instance: dict, the extra data dictionary
        :param mappings: dict, mapping names { "from_name": "to_name", ...}
        :param fields: list, extra data fields to include. Use the original column names (the ones in the database)
        :param units: dict, extra data units

        :return: dict
        """
        data = {}

        def check_and_convert_numeric(value):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return True, value
            if isinstance(value, str):
                try:
                    return True, float(value)
                except ValueError:
                    pass
            return False, value

        if fields:
            for field in fields:
                value = instance.get(field, None)
                is_numeric, numeric_value = check_and_convert_numeric(value)
                if is_numeric and units.get(field):
                    value = numeric_value * ureg(units[field])
                if field in mappings:
                    data[mappings[field]] = value
                else:
                    data[field] = value

        return data

    @classmethod
    def model_to_dict_with_mapping(cls, instance, mappings, fields=None, exclude=None):
        """
        Copied from Django method and added a mapping for field names and excluding
        specific API fields.
        """
        from django.db import models

        opts = instance._meta
        data = {}
        for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
            if not getattr(f, "editable", False):
                continue
            if fields is not None and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue
            if f.name in Column.EXCLUDED_COLUMN_RETURN_FIELDS:
                continue

            # fix specific time stamps
            if f.name in {"recent_sale_date", "release_date", "generation_date"}:
                value = f.value_from_object(instance)
                if value:
                    value = make_naive(value).isoformat()
            elif isinstance(f, GeometryField):
                # If this is a GeometryField, convert (non-JSON serializable) geometry to string (wkt)
                value = f.value_from_object(instance)
                if value:
                    value = GEOSGeometry(value, srid=4326).wkt
            else:
                value = f.value_from_object(instance)

            if f.name in mappings:
                data[mappings[f.name]] = value
            else:
                data[f.name] = value

            # Evaluate ManyToManyField QuerySets to prevent subsequent model
            # alteration of that field from being reflected in the data.
            if isinstance(f, models.ManyToManyField):
                data[f.name] = list(data[f.name])
        return data

    @classmethod
    def serialize(
        cls,
        object_list: Sequence[PropertyView] | Sequence[TaxLotView],
        show_columns: list[int] | None,
        columns_from_database: list[dict],
        include_related: bool = True,
        goal_id: int = False,
    ) -> list[dict]:
        """
        This method takes a list of TaxLotViews or PropertyViews and returns the data along
        with the related TaxLotView or PropertyView.

        The columns are the items as seen by the front end. This means that the columns
        are prepended with tax_ or property_ if they are the related columns.

        This method is just a copy/abstraction from the _get_filtered_results in the
        Property/TaxLot viewset.  In the future this should become a serializer. For now it is
        here so that we can use this method to create the data for exporting to CSV on the backend.

        :param object_list:
        :param show_columns: columns (as defined by backend), Pass None to default
                             to all columns excluding extra data
        :param columns_from_database: columns from the database as list of dict
        :param include_related: if False, the related data is NOT included (i.e.,
                                only the object_list is serialized) - optional (default is True)
        """
        if len(object_list) == 0:
            return []

        if object_list[0].__class__.__name__ == "PropertyView":
            this_cls, this_lower = "Property", "property"
            related_cls, related_lower = "TaxLot", "taxlot"
        else:
            this_cls, this_lower = "TaxLot", "taxlot"
            related_cls, related_lower = "Property", "property"

        lookups = {
            "audit_log_class": apps.get_model("seed", f"{this_cls}AuditLog"),
            "view_class": apps.get_model("seed", f"{this_cls}View"),
            "obj_class": f"{this_cls}View",
            "obj_query_in": f"{this_lower}_view_id__in",
            "obj_state_id": f"{this_lower}_state_id",
            "obj_view_id": f"{this_lower}_view_id",
            "obj_id": f"{this_lower}_id",
            "centroid": "centroid",
            "bounding_box": "bounding_box",
            "long_lat": "long_lat",
            "related_audit_log_class": apps.get_model("seed", f"{related_cls}AuditLog"),
            "related_class": f"{related_cls}View",
            "related_query_in": f"{related_lower}_view_id__in",
            "select_related": f"{related_lower}",
            "related_view": f"{related_lower}_view",
            "related_view_class": apps.get_model("seed", f"{related_cls}View"),
            "related_view_id": f"{related_lower}_view_id",
            "related_state_id": f"{related_lower}_state_id",
        }

        ids = [obj.pk for obj in object_list]

        # getting these at the top keeps us querying for any ali more once, and allows us to query for them all at once.
        if this_cls == "Property":
            needed_ali_ids = [obj.property.access_level_instance_id for obj in object_list]
        else:
            needed_ali_ids = [obj.taxlot.access_level_instance_id for obj in object_list]
        alis = AccessLevelInstance.objects.filter(id__in=needed_ali_ids)
        ali_path_by_id = {ali.id: ali.path for ali in alis}

        # gather meter counts
        Meter = apps.get_model("seed", "Meter")
        if this_cls == "Property":
            obj_meter_counts = dict(
                Meter.objects.filter(property__in=[obj.property_id for obj in object_list])
                .values_list("property_id")
                .annotate(Count("property_id"))
            )

        # gather note counts
        Note = apps.get_model("seed", "Note")
        obj_note_counts = {
            x[0]: x[1]
            for x in Note.objects.filter(**{lookups["obj_query_in"]: ids})
            .values_list(lookups["obj_view_id"])
            .order_by()
            .annotate(Count(lookups["obj_view_id"]))
        }

        # determine merge statuses
        states_qs = lookups["view_class"].objects.filter(id__in=ids)
        merged_state_ids = (
            lookups["audit_log_class"]
            .objects.filter(
                name__in=["Manual Match", "System Match", "Merge current state in migration"],
                state_id__in=models.Subquery(states_qs.values("state_id")),
            )
            .values_list("state_id", flat=True)
        )

        # gather all columns - separate the 'related' columns
        related_columns = []
        obj_columns = []
        obj_column_name_mapping = {}
        for column in columns_from_database:
            if column["related"]:
                related_columns.append(column)
            else:
                obj_columns.append(column)
                obj_column_name_mapping[column["column_name"]] = column["name"]

        # gather the _shown_ columns
        if show_columns is None:
            filtered_fields = {col["column_name"] for col in obj_columns if not col["is_extra_data"]}
        else:
            filtered_fields = {col["column_name"] for col in obj_columns if not col["is_extra_data"] and col["id"] in show_columns}
            extra_data_units = {}
            filtered_extra_data_fields = set()
            derived_data_units = {}
            filtered_derived_data_fields = set()
            for col in obj_columns:
                if col["is_extra_data"] and col["id"] in show_columns:
                    filtered_extra_data_fields.add(col["column_name"])
                    extra_data_units[col["column_name"]] = DEFAULT_UNITS.get(col["data_type"])
                elif col["derived_column"] is not None and col["id"] in show_columns:
                    filtered_derived_data_fields.add(col["column_name"])
                    derived_data_units[col["column_name"]] = DEFAULT_UNITS.get(col["data_type"])

        # get the related data
        join_map = {}
        if include_related:
            join_map = cls.get_related(ids, show_columns, related_columns, lookups)

        # serialize everything
        results = []
        for obj in object_list:
            # Each object in the response is built from the state data, with related data added on.
            obj_dict = TaxLotProperty.model_to_dict_with_mapping(
                obj.state, obj_column_name_mapping, fields=filtered_fields, exclude=["extra_data"]
            )

            # Only add extra data columns if a settings profile was used
            if show_columns is not None:
                obj_dict.update(
                    TaxLotProperty.extra_data_to_dict_with_mapping(
                        obj.state.extra_data, obj_column_name_mapping, fields=filtered_extra_data_fields, units=extra_data_units
                    ).items()
                )
                obj_dict.update(
                    TaxLotProperty.extra_data_to_dict_with_mapping(
                        obj.state.derived_data, obj_column_name_mapping, fields=filtered_derived_data_fields, units=derived_data_units
                    ).items()
                )

            # Use property_id instead of default (state_id)
            obj_dict["id"] = getattr(obj, lookups["obj_id"])
            obj_dict["notes_count"] = obj_note_counts.get(obj.id, 0)

            obj_dict[lookups["obj_state_id"]] = obj.state.id
            obj_dict[lookups["obj_view_id"]] = obj.id

            obj_dict["merged_indicator"] = obj.state_id in merged_state_ids

            if this_cls == "Property":
                obj_dict.update(ali_path_by_id[obj.property.access_level_instance_id])
                obj_dict["meters_exist_indicator"] = obj_meter_counts.get(obj.property_id, 0) > 0
                obj_dict["groups_indicator"] = obj.property.group_mappings.count() > 0
            else:
                obj_dict.update(ali_path_by_id[obj.taxlot.access_level_instance_id])
                obj_dict["groups_indicator"] = obj.taxlot.group_mappings.count() > 0

            # bring in GIS data
            obj_dict[lookups["bounding_box"]] = bounding_box_wkt(obj.state)
            obj_dict[lookups["long_lat"]] = long_lat_wkt(obj.state)
            obj_dict[lookups["centroid"]] = centroid_wkt(obj.state)

            # These are not added in model_to_dict_with_mapping as these fields are not 'editable'
            # Also, do not make these timestamps naive. They persist correctly.
            if "updated" in filtered_fields:
                obj_dict[obj_column_name_mapping["updated"]] = obj.state.updated
            if "created" in filtered_fields:
                obj_dict[obj_column_name_mapping["created"]] = obj.state.created

            # All the related tax lot states.
            obj_dict["related"] = join_map.get(obj.pk, [])

            # remove the measures from this view for now
            if obj_dict.get("measures"):
                del obj_dict["measures"]

            # add goal note data
            if goal_id:
                goal_note = obj.property.goalnote_set.filter(goal=goal_id).first()
                obj_dict["goal_note"] = goal_note.serialize() if goal_note else None
                obj_dict["historical_note"] = obj.property.historical_note.serialize()

            # add non goal label ids
            if this_cls == "Property":
                obj_dict["labels"] = list(obj.propertyviewlabel_set.filter(goal__isnull=True).values_list("statuslabel_id", flat=True))
            else:
                obj_dict["labels"] = list(obj.labels.values_list("id", flat=True))

            results.append(obj_dict)

        return results

    @classmethod
    def get_related(
        cls, ids: list[int], show_columns: list[int] | None, related_columns: list[dict], lookups: dict
    ) -> dict[int, list[dict]]:
        # Ids of views to look up in m2m
        joins = TaxLotProperty.objects.filter(**{lookups["obj_query_in"]: ids}).select_related(lookups["related_view"])

        # Get all ids of related views on these joins
        related_ids = [getattr(j, lookups["related_view_id"]) for j in joins]

        # Get all related views from the related_class
        related_views = (
            apps.get_model("seed", lookups["related_class"])
            .objects.select_related(lookups["select_related"], "state", "cycle")
            .filter(pk__in=related_ids)
        )

        related_column_name_mapping = {col["column_name"]: col["name"] for col in related_columns}

        related_map = {}

        if show_columns is None:
            filtered_fields = {col["column_name"] for col in related_columns if not col["is_extra_data"]}
        else:
            filtered_fields = {col["column_name"] for col in related_columns if not col["is_extra_data"] and col["id"] in show_columns}
            filtered_extra_data_fields = {
                col["column_name"] for col in related_columns if col["is_extra_data"] and col["id"] in show_columns
            }
            derived_data_units = {
                col["column_name"] for col in related_columns if col["derived_column"] is not None and col["id"] in show_columns
            }

        for related_view in related_views:
            related_dict = TaxLotProperty.model_to_dict_with_mapping(
                related_view.state, related_column_name_mapping, fields=filtered_fields, exclude=["extra_data"]
            )

            related_dict[lookups["related_state_id"]] = related_view.state.id

            # Add GIS stuff to the related dict
            # (I guess these are special fields not in columns and not directly JSON serializable...)
            related_dict[lookups["bounding_box"]] = bounding_box_wkt(related_view.state)
            related_dict[lookups["long_lat"]] = long_lat_wkt(related_view.state)
            related_dict[lookups["centroid"]] = centroid_wkt(related_view.state)

            # custom handling for when it is TaxLotView
            if lookups["obj_class"] == "TaxLotView":
                # Do not make these timestamps naive. They persist correctly.
                if "updated" in filtered_fields:
                    related_dict[related_column_name_mapping["updated"]] = related_view.property.updated
                if "created" in filtered_fields:
                    related_dict[related_column_name_mapping["created"]] = related_view.property.created
            elif lookups["obj_class"] == "PropertyView":
                # Do not make these timestamps naive. They persist correctly.
                if "updated" in filtered_fields:
                    related_dict[related_column_name_mapping["updated"]] = related_view.taxlot.updated
                if "created" in filtered_fields:
                    related_dict[related_column_name_mapping["created"]] = related_view.taxlot.created

            # Only add extra data columns if a settings profile was used
            if show_columns is not None:
                related_dict.update(
                    TaxLotProperty.extra_data_to_dict_with_mapping(
                        related_view.state.extra_data, related_column_name_mapping, fields=filtered_extra_data_fields
                    ).items()
                )
                related_dict.update(
                    TaxLotProperty.extra_data_to_dict_with_mapping(
                        related_view.state.derived_data, related_column_name_mapping, fields=derived_data_units
                    ).items()
                )
            related_map[related_view.pk] = related_dict

            # Replace taxlot_view id with taxlot id
            related_map[related_view.pk]["id"] = getattr(related_view, lookups["select_related"]).id

        # Not sure what this code is really doing, but it only exists for TaxLotViews
        if lookups["obj_class"] == "TaxLotView":
            # Get whole taxlotstate table:
            tuple_prop_to_jurisdiction_tl = tuple(
                TaxLotProperty.objects.values_list("property_view_id", "taxlot_view__state__jurisdiction_tax_lot_id")
            )

            # create a mapping that defaults to an empty list
            prop_to_jurisdiction_tl = defaultdict(list)

            # populate the mapping
            for name, pth in tuple_prop_to_jurisdiction_tl:
                prop_to_jurisdiction_tl[name].append(pth)

        Note = apps.get_model("seed", "Note")
        join_note_counts = {
            x[0]: x[1]
            for x in Note.objects.filter(**{lookups["related_query_in"]: related_ids})
            .values_list(lookups["related_view_id"])
            .order_by()
            .annotate(Count(lookups["related_view_id"]))
        }

        # Get merged_indicators for related
        join_states_qs = lookups["related_view_class"].objects.filter(id__in=related_ids)
        join_merged_state_ids = (
            lookups["related_audit_log_class"]
            .objects.filter(
                name__in=["Manual Match", "System Match", "Merge current state in migration"],
                state_id__in=models.Subquery(join_states_qs.values("state_id")),
            )
            .values_list("state_id", flat=True)
        )

        # A mapping of object's view pk to a list of related state info for a related view
        join_map: dict[int, list[dict]] = {}
        for join in joins:
            # Another taxlot specific view
            if lookups["obj_class"] == "TaxLotView":
                jurisdiction_tax_lot_ids = prop_to_jurisdiction_tl[join.property_view_id]

                # Filter out associated tax lots that are present but which do not have preferred
                none_in_jurisdiction_tax_lot_ids = None in jurisdiction_tax_lot_ids
                jurisdiction_tax_lot_ids = list(filter(lambda x: x is not None, jurisdiction_tax_lot_ids))

                if none_in_jurisdiction_tax_lot_ids:
                    jurisdiction_tax_lot_ids.append("Missing")

                join_dict = related_map[getattr(join, lookups["related_view_id"])].copy()
                join_dict.update(
                    {
                        # 'primary': 'P' if join.primary else 'S',
                        # 'calculated_taxlot_ids': '; '.join(jurisdiction_tax_lot_ids),
                        lookups["related_view_id"]: getattr(join, lookups["related_view_id"])
                    }
                )

            else:
                join_dict = related_map[getattr(join, lookups["related_view_id"])].copy()
                join_dict.update(
                    {
                        # 'primary': 'P' if join.primary else 'S',
                        lookups["related_view_id"]: getattr(join, lookups["related_view_id"])
                    }
                )

            join_dict["notes_count"] = join_note_counts.get(getattr(join, lookups["related_view_id"]), 0)
            join_dict["merged_indicator"] = getattr(join, lookups["related_view"]).state_id in join_merged_state_ids

            # remove the measures from this view for now
            if join_dict.get("measures"):
                del join_dict["measures"]

            try:
                join_map[getattr(join, lookups["obj_view_id"])].append(join_dict)
            except KeyError:
                join_map[getattr(join, lookups["obj_view_id"])] = [join_dict]

        return join_map


@receiver(pre_save, sender=TaxLotProperty)
def presave_organization(sender, instance, **kwargs):
    p_ali = instance.property_view.property.access_level_instance.pk
    t_ali = instance.taxlot_view.taxlot.access_level_instance.pk

    if p_ali != t_ali:
        raise ValidationError("taxlot and property must have same access level instance.")

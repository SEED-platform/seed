# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import unicode_literals

import logging
from collections import defaultdict
from itertools import chain

from django.apps import apps
from django.db import models
from django.db.models import Count
from django.utils.timezone import make_naive

from seed.models.columns import Column
from seed.utils.geocode import long_lat_wkt

logger = logging.getLogger(__name__)


class TaxLotProperty(models.Model):
    property_view = models.ForeignKey('PropertyView')
    taxlot_view = models.ForeignKey('TaxLotView')
    cycle = models.ForeignKey('Cycle')

    # If there is a complex TaxLot/Property association, this field
    # lists the "main" tax lot that Properties should be reported under.
    # User controlled flag.
    primary = models.BooleanField(default=True)

    def __str__(self):
        return 'M2M Property View %s / TaxLot View %s' % (
            self.property_view_id, self.taxlot_view_id)

    class Meta:
        unique_together = ('property_view', 'taxlot_view',)
        index_together = [
            ['cycle', 'property_view'],
            ['cycle', 'taxlot_view'],
            ['property_view', 'taxlot_view']
        ]

    @classmethod
    def extra_data_to_dict_with_mapping(cls, instance, mappings, fields=None):
        """
        Convert the extra data to a dictionary with a name mapping for the keys

        :param instance: dict, the extra data dictionary
        :param mappings: dict, mapping names { "from_name": "to_name", ...}
        :param fields: list, extra data fields to include. Use the original column names (the ones in the database)
        :return: dict
        """
        data = {}

        if fields:
            for field in fields:
                if field in mappings:
                    data[mappings[field]] = instance.get(field, None)
                else:
                    data[field] = instance.get(field, None)

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
            if not getattr(f, 'editable', False):
                continue
            if fields is not None and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue
            if f.name in Column.EXCLUDED_COLUMN_RETURN_FIELDS:
                continue

            # fix specific time stamps
            if f.name in ['recent_sale_date', 'release_date', 'generation_date', 'analysis_start_time',
                          'analysis_end_time']:
                value = f.value_from_object(instance)
                if value:
                    value = make_naive(value).isoformat()
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
    def get_related(cls, object_list, show_columns, columns_from_database):
        """
        This method takes a list of TaxLotViews or PropertyViews and returns the data along
        with the related TaxLotView or PropertyView.

        The columns are the items as seen by the front end. This means that the columns
        are prepended with tax_ or property_ if they are the related columns.

        This method is just a copy/abstraction from the _get_filtered_results in the
        Property/TaxLot viewset.  In the future this should become a serializer. For now it is
        here so that we can use this method to create the data for exporting to CSV on the backend.

        :param object_list: list
        :param show_columns: list, columns (as defined by backend), Pass None to default to all columns excluding extra
                             data
        :param columns_from_database: list, columns from the database as list of dict
        :return: list
        """
        results = []

        if len(object_list) == 0:
            return results

        Note = apps.get_model('seed', 'Note')

        if object_list[0].__class__.__name__ == 'PropertyView':
            lookups = {
                'obj_class': 'PropertyView',
                'obj_query_in': 'property_view_id__in',
                'obj_state_id': 'property_state_id',
                'obj_view_id': 'property_view_id',
                'obj_id': 'property_id',
                'long_lat': 'long_lat',
                'related_class': 'TaxLotView',
                'related_query_in': 'taxlot_view_id__in',
                'select_related': 'taxlot',
                'related_view': 'taxlot_view',
                'related_view_id': 'taxlot_view_id',
                'related_state_id': 'taxlot_state_id',
            }
        else:
            lookups = {
                'obj_class': 'TaxLotView',
                'obj_query_in': 'taxlot_view_id__in',
                'obj_state_id': 'taxlot_state_id',
                'obj_view_id': 'taxlot_view_id',
                'obj_id': 'taxlot_id',
                'long_lat': 'long_lat',
                'related_class': 'PropertyView',
                'related_query_in': 'property_view_id__in',
                'select_related': 'property',
                'related_view': 'property_view',
                'related_view_id': 'property_view_id',
                'related_state_id': 'property_state_id',
            }

        # Ids of views to look up in m2m
        ids = [obj.pk for obj in object_list]
        joins = TaxLotProperty.objects.filter(**{lookups['obj_query_in']: ids}).select_related(lookups['related_view'])

        # Get all ids of related views on these joins
        related_ids = [getattr(j, lookups['related_view_id']) for j in joins]

        # Get all related views from the related_class
        related_views = apps.get_model('seed', lookups['related_class']).objects.select_related(
            lookups['select_related'], 'state', 'cycle').filter(pk__in=related_ids)

        related_columns = []
        related_column_name_mapping = {}
        obj_columns = []
        obj_column_name_mapping = {}
        for column in columns_from_database:
            if column['related']:
                related_columns.append(column)
                related_column_name_mapping[column['column_name']] = column['name']
            else:
                obj_columns.append(column)
                obj_column_name_mapping[column['column_name']] = column['name']

        related_map = {}

        if show_columns is None:
            filtered_fields = set([col['column_name'] for col in related_columns if not col['is_extra_data']])
        else:
            filtered_fields = set([col['column_name'] for col in related_columns if not col['is_extra_data']
                                   and col['id'] in show_columns])
            filtered_extra_data_fields = set([col['column_name'] for col in related_columns if col['is_extra_data']
                                              and col['id'] in show_columns])

        for related_view in related_views:
            related_dict = TaxLotProperty.model_to_dict_with_mapping(
                related_view.state,
                related_column_name_mapping,
                fields=filtered_fields,
                exclude=['extra_data']
            )

            related_dict[lookups['related_state_id']] = related_view.state.id

            # custom handling for when it is TaxLotView
            if lookups['obj_class'] == 'TaxLotView':
                if 'campus' in filtered_fields:
                    related_dict[related_column_name_mapping['campus']] = related_view.property.campus
                # Do not make these timestamps naive. They persist correctly.
                if 'updated' in filtered_fields:
                    related_dict[related_column_name_mapping['updated']] = related_view.property.updated
                if 'created' in filtered_fields:
                    related_dict[related_column_name_mapping['created']] = related_view.property.created
                # Replace the enumerations
                if 'analysis_state' in filtered_fields:
                    related_dict[
                        related_column_name_mapping['analysis_state']] = related_view.state.get_analysis_state_display()
            elif lookups['obj_class'] == 'PropertyView':
                # Do not make these timestamps naive. They persist correctly.
                if 'updated' in filtered_fields:
                    related_dict[related_column_name_mapping['updated']] = related_view.taxlot.updated
                if 'created' in filtered_fields:
                    related_dict[related_column_name_mapping['created']] = related_view.taxlot.created

            # Only add extra data columns if a settings profile was used
            if show_columns is not None:
                related_dict.update(
                    TaxLotProperty.extra_data_to_dict_with_mapping(
                        related_view.state.extra_data,
                        related_column_name_mapping,
                        fields=filtered_extra_data_fields
                    ).items()
                )
            related_map[related_view.pk] = related_dict

            # Replace taxlot_view id with taxlot id
            related_map[related_view.pk]['id'] = getattr(related_view, lookups['select_related']).id

        # Not sure what this code is really doing, but it only exists for TaxLotViews
        if lookups['obj_class'] == 'TaxLotView':
            # Get whole taxlotstate table:
            tuple_prop_to_jurisdiction_tl = tuple(
                TaxLotProperty.objects.values_list('property_view_id', 'taxlot_view__state__jurisdiction_tax_lot_id')
            )

            # create a mapping that defaults to an empty list
            prop_to_jurisdiction_tl = defaultdict(list)

            # populate the mapping
            for name, pth in tuple_prop_to_jurisdiction_tl:
                prop_to_jurisdiction_tl[name].append(pth)

        join_note_counts = {x[0]: x[1] for x in Note.objects.filter(**{lookups['related_query_in']: related_ids})
                            .values_list(lookups['related_view_id']).order_by().annotate(Count(lookups['related_view_id']))}

        # A mapping of object's view pk to a list of related state info for a related view
        join_map = {}
        for join in joins:
            # Another taxlot specific view
            if lookups['obj_class'] == 'TaxLotView':
                jurisdiction_tax_lot_ids = prop_to_jurisdiction_tl[join.property_view_id]

                # Filter out associated tax lots that are present but which do not have preferred
                none_in_jurisdiction_tax_lot_ids = None in jurisdiction_tax_lot_ids
                jurisdiction_tax_lot_ids = list(filter(lambda x: x is not None, jurisdiction_tax_lot_ids))

                if none_in_jurisdiction_tax_lot_ids:
                    jurisdiction_tax_lot_ids.append('Missing')

                join_dict = related_map[getattr(join, lookups['related_view_id'])].copy()
                join_dict.update({
                    # 'primary': 'P' if join.primary else 'S',
                    # 'calculated_taxlot_ids': '; '.join(jurisdiction_tax_lot_ids),
                    lookups['related_view_id']: getattr(join, lookups['related_view_id'])
                })

            else:
                join_dict = related_map[getattr(join, lookups['related_view_id'])].copy()
                join_dict.update({
                    # 'primary': 'P' if join.primary else 'S',
                    lookups['related_view_id']: getattr(join, lookups['related_view_id'])
                })

            join_dict['notes_count'] = join_note_counts.get(join.id, 0)

            # remove the measures from this view for now
            if join_dict.get('measures'):
                del join_dict['measures']

            try:
                join_map[getattr(join, lookups['obj_view_id'])].append(join_dict)
            except KeyError:
                join_map[getattr(join, lookups['obj_view_id'])] = [join_dict]

        if show_columns is None:
            filtered_fields = set([col['column_name'] for col in obj_columns if not col['is_extra_data']])
        else:
            filtered_fields = set([col['column_name'] for col in obj_columns if not col['is_extra_data']
                                   and col['id'] in show_columns])
            filtered_extra_data_fields = set([col['column_name'] for col in obj_columns if col['is_extra_data']
                                              and col['id'] in show_columns])

        obj_note_counts = {x[0]: x[1] for x in Note.objects.filter(**{lookups['obj_query_in']: ids})
                           .values_list(lookups['obj_view_id']).order_by().annotate(Count(lookups['obj_view_id']))}

        for obj in object_list:
            # Each object in the response is built from the state data, with related data added on.
            obj_dict = TaxLotProperty.model_to_dict_with_mapping(obj.state,
                                                                 obj_column_name_mapping,
                                                                 fields=filtered_fields,
                                                                 exclude=['extra_data'])

            # Only add extra data columns if a settings profile was used
            if show_columns is not None:
                obj_dict.update(
                    TaxLotProperty.extra_data_to_dict_with_mapping(
                        obj.state.extra_data,
                        obj_column_name_mapping,
                        fields=filtered_extra_data_fields
                    ).items()
                )

            # Use property_id instead of default (state_id)
            obj_dict['id'] = getattr(obj, lookups['obj_id'])
            obj_dict['notes_count'] = obj_note_counts.get(obj.id, 0)

            obj_dict[lookups['obj_state_id']] = obj.state.id
            obj_dict[lookups['obj_view_id']] = obj.id

            obj_dict[lookups['long_lat']] = long_lat_wkt(obj.state)

            # store the property / taxlot data to the object dictionary as well. This is hacky.
            if lookups['obj_class'] == 'PropertyView':
                if 'campus' in filtered_fields:
                    obj_dict[obj_column_name_mapping['campus']] = obj.property.campus
                # Do not make these timestamps naive. They persist correctly.
                if 'created' in filtered_fields:
                    obj_dict[obj_column_name_mapping['created']] = obj.property.created
                if 'updated' in filtered_fields:
                    obj_dict[obj_column_name_mapping['updated']] = obj.property.updated
                if 'analysis_state' in filtered_fields:
                    obj_dict[obj_column_name_mapping['analysis_state']] = obj.state.get_analysis_state_display()
            elif lookups['obj_class'] == 'TaxLotView':
                # Do not make these timestamps naive. They persist correctly.
                if 'updated' in filtered_fields:
                    obj_dict[obj_column_name_mapping['updated']] = obj.taxlot.updated
                if 'created' in filtered_fields:
                    obj_dict[obj_column_name_mapping['created']] = obj.taxlot.created

            # All the related tax lot states.
            obj_dict['related'] = join_map.get(obj.pk, [])

            # remove the measures from this view for now
            if obj_dict.get('measures'):
                del obj_dict['measures']

            # # This isn't currently used, but if we ever re-enable it we need to prefetch all of the label data using a
            # # single query for performance.  This code causes one query with a join for every record
            # label_string = []
            # if hasattr(obj, 'property'):
            #     for label in obj.property.labels.all().order_by('name'):
            #         label_string.append(label.name)
            #     obj_dict['property_labels'] = ','.join(label_string)
            #
            # elif hasattr(obj, 'taxlot'):
            #     for label in obj.taxlot.labels.all().order_by('name'):
            #         label_string.append(label.name)
            #     obj_dict['taxlot_labels'] = ','.join(label_string)

            results.append(obj_dict)

        return results

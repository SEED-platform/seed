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
from django.utils.timezone import make_naive
from seed.models.columns import Column

logger = logging.getLogger(__name__)


class TaxLotProperty(models.Model):
    property_view = models.ForeignKey('PropertyView')
    taxlot_view = models.ForeignKey('TaxLotView')
    cycle = models.ForeignKey('Cycle')

    # If there is a complex TaxLot/Property association, this field
    # lists the "main" tax lot that Properties should be reported under.
    # User controlled flag.
    primary = models.BooleanField(default=True)

    def __unicode__(self):
        return u'M2M Property View %s / TaxLot View %s' % (
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
        for extra_data_field, extra_data_value in instance.items():
            if fields and extra_data_field not in fields:
                continue

            if extra_data_field in mappings:
                data[mappings[extra_data_field]] = extra_data_value
            else:
                data[extra_data_field] = extra_data_value

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
            if fields and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue
            if f.name in Column.EXCLUDED_API_FIELDS:
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
        :param show_columns: list, columns (as defined by frontend), Pass None to default to all columns
        :param columns_from_database: list, columns from the database as list of dict
        :return: list
        """
        results = []

        if len(object_list) == 0:
            return results

        if object_list[0].__class__.__name__ == 'PropertyView':
            lookups = {
                'obj_class': 'PropertyView',
                'obj_query_in': 'property_view_id__in',
                'obj_state_id': 'property_state_id',
                'obj_view_id': 'property_view_id',
                'obj_id': 'property_id',
                'related_class': 'TaxLotView',
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
                'related_class': 'PropertyView',
                'select_related': 'property',
                'related_view': 'property_view',
                'related_view_id': 'property_view_id',
                'related_state_id': 'property_state_id',
            }

        # Ids of propertyviews to look up in m2m
        ids = [obj.pk for obj in object_list]
        joins = TaxLotProperty.objects.filter(**{lookups['obj_query_in']: ids}).select_related(lookups['related_view'])

        # Get all ids of tax lots on these joins
        related_ids = [getattr(j, lookups['related_view_id']) for j in joins]

        # Get all related views from the related_class
        related_views = apps.get_model('seed', lookups['related_class']).objects.select_related(
            lookups['select_related'], 'state', 'cycle').filter(pk__in=related_ids)

        related_column_name_mapping = {}
        obj_column_name_mapping = {}
        for column in columns_from_database:
            if column['related']:
                related_column_name_mapping[column['column_name']] = column['name']
            else:
                obj_column_name_mapping[column['column_name']] = column['name']

        related_map = {}
        for related_view in related_views:
            related_dict = TaxLotProperty.model_to_dict_with_mapping(related_view.state,
                                                                     related_column_name_mapping,
                                                                     fields=show_columns,
                                                                     exclude=['extra_data'])

            related_dict[lookups['related_state_id']] = related_view.state.id

            # custom handling for when it is TaxLotView
            if lookups['obj_class'] == 'TaxLotView':
                related_dict[related_column_name_mapping['campus']] = related_view.property.campus
                # Do not make these timestamps naive. They persist correctly.
                related_dict[related_column_name_mapping['updated']] = related_view.property.updated
                related_dict[related_column_name_mapping['created']] = related_view.property.created
                # Replace the enumerations
                related_dict['analysis_state'] = related_view.state.get_analysis_state_display()
            elif lookups['obj_class'] == 'PropertyView':
                # Do not make these timestamps naive. They persist correctly.
                related_dict[related_column_name_mapping['updated']] = related_view.taxlot.updated
                related_dict[related_column_name_mapping['created']] = related_view.taxlot.created

            related_dict = dict(
                related_dict.items() +
                TaxLotProperty.extra_data_to_dict_with_mapping(
                    related_view.state.extra_data,
                    related_column_name_mapping, fields=show_columns
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

        # A mapping of object's view pk to a list of related state info for a related view
        join_map = {}
        for join in joins:
            # Another taxlot specific view
            if lookups['obj_class'] == 'TaxLotView':
                jurisdiction_tax_lot_ids = prop_to_jurisdiction_tl[join.property_view_id]

                # Filter out associated tax lots that are present but which do not have preferred
                none_in_jurisdiction_tax_lot_ids = None in jurisdiction_tax_lot_ids
                jurisdiction_tax_lot_ids = filter(lambda x: x is not None, jurisdiction_tax_lot_ids)

                if none_in_jurisdiction_tax_lot_ids:
                    jurisdiction_tax_lot_ids.append('Missing')

                join_dict = related_map[getattr(join, lookups['related_view_id'])].copy()
                join_dict.update({
                    'primary': 'P' if join.primary else 'S',
                    'calculated_taxlot_ids': '; '.join(jurisdiction_tax_lot_ids),
                    lookups['related_view_id']: getattr(join, lookups['related_view_id'])
                })

            else:
                join_dict = related_map[getattr(join, lookups['related_view_id'])].copy()
                join_dict.update({
                    'primary': 'P' if join.primary else 'S',
                    lookups['related_view_id']: getattr(join, lookups['related_view_id'])
                })

            join_dict['notes_count'] = getattr(join, lookups['related_view']).notes.count()

            # remove the measures from this view for now
            if join_dict.get('measures'):
                del join_dict['measures']

            try:
                join_map[getattr(join, lookups['obj_view_id'])].append(join_dict)
            except KeyError:
                join_map[getattr(join, lookups['obj_view_id'])] = [join_dict]

        for obj in object_list:
            # Each object in the response is built from the state data, with related data added on.
            obj_dict = TaxLotProperty.model_to_dict_with_mapping(obj.state,
                                                                 obj_column_name_mapping,
                                                                 fields=show_columns,
                                                                 exclude=['extra_data'])

            obj_dict = dict(
                obj_dict.items() +
                TaxLotProperty.extra_data_to_dict_with_mapping(
                    obj.state.extra_data,
                    obj_column_name_mapping,
                    fields=show_columns
                ).items()
            )

            # Use property_id instead of default (state_id)
            obj_dict['id'] = getattr(obj, lookups['obj_id'])
            obj_dict['notes_count'] = obj.notes.count()

            obj_dict[lookups['obj_state_id']] = obj.state.id
            obj_dict[lookups['obj_view_id']] = obj.id

            # store the property / taxlot data to the object dictionary as well. This is hacky.
            if lookups['obj_class'] == 'PropertyView':
                obj_dict['campus'] = obj.property.campus
                # Do not make these timestamps naive. They persist correctly.
                obj_dict[obj_column_name_mapping['created']] = obj.property.created
                obj_dict[obj_column_name_mapping['updated']] = obj.property.updated
                obj_dict['analysis_state'] = obj.state.get_analysis_state_display()
            elif lookups['obj_class'] == 'TaxLotView':
                # Do not make these timestamps naive. They persist correctly.
                obj_dict[obj_column_name_mapping['updated']] = obj.taxlot.updated
                obj_dict[obj_column_name_mapping['created']] = obj.taxlot.created

            # All the related tax lot states.
            obj_dict['related'] = join_map.get(obj.pk, [])

            # remove the measures from this view for now
            if obj_dict.get('measures'):
                del obj_dict['measures']

            label_string = []
            if hasattr(obj, 'property'):
                for label in obj.property.labels.all().order_by('name'):
                    label_string.append(label.name)
                obj_dict['property_labels'] = ','.join(label_string)

            elif hasattr(obj, 'taxlot'):
                for label in obj.taxlot.labels.all().order_by('name'):
                    label_string.append(label.name)
                obj_dict['taxlot_labels'] = ','.join(label_string)

            results.append(obj_dict)

        return results

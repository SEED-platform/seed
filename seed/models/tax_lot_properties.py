# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import unicode_literals

import logging
from collections import defaultdict

from django.apps import apps
from django.db import models
from django.forms.models import model_to_dict
from django.utils.timezone import make_naive

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
    def get_related(cls, object_list, columns):
        """
        This method takes a list of TaxLotViews or PropertyViews and returns the data along
        with the related TaxLotView or PropertyView.

        The columns are the items as seen by the front end. This means that the columns
        are prepended with tax_ or property_ if they are the related columns.

        This method is just a copy/abstraction from the _get_filtered_results in the
        Property/TaxLot viewset.  In the future this should become a serializer. For now it is
        here so that we can use this method to create the data for exporting to CSV on the backend.

        :param object_list: list
        :param columns: list, columns (as defined by frontend)
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
                'obj_id_name': 'property_id',
                'related_class': 'TaxLotView',
                'select_related': 'taxlot',
                'related_view_name': 'taxlot_view',
                'related_view_id_name': 'taxlot_view_id',
                'related_state_id': 'taxlot_state_id',
                'related_column_key': 'tax',
            }
        else:
            lookups = {
                'obj_class': 'TaxLotView',
                'obj_query_in': 'taxlot_view_id__in',
                'obj_state_id': 'taxlot_state_id',
                'obj_view_id': 'taxlot_view_id',
                'obj_id_name': 'taxlot_id',
                'related_class': 'PropertyView',
                'select_related': 'property',
                'related_view_name': 'property_view',
                'related_view_id_name': 'property_view_id',
                'related_state_id': 'property_state_id',
                'related_column_key': 'property',
            }

        # Ids of propertyviews to look up in m2m
        ids = [obj.pk for obj in object_list]
        joins = TaxLotProperty.objects.filter(**{lookups['obj_query_in']: ids}).select_related(
            lookups['related_view_name'])

        # Get all ids of tax lots on these joins
        related_ids = [getattr(j, lookups['related_view_id_name']) for j in joins]

        # Get all tax lot views that are related
        related_views = apps.get_model('seed', lookups['related_class']).objects.select_related(
            lookups['select_related'], 'state', 'cycle').filter(pk__in=related_ids)

        # Map the related view id to the other view's state data
        # so we can reference these easily and save some queries.
        db_columns = apps.get_model('seed', 'Column').retrieve_db_fields()

        related_map = {}
        for related_view in related_views:
            related_dict = model_to_dict(related_view.state, exclude=['extra_data'])
            related_dict[lookups['related_state_id']] = related_view.state.id

            # custom handling for when it is TaxLotView
            if lookups['obj_class'] == 'TaxLotView':
                related_dict['campus'] = related_view.property.campus
                # Do not make these timestamps naive. They persist correctly.
                related_dict['db_property_updated'] = related_view.property.updated
                related_dict['db_property_created'] = related_view.property.created
            elif lookups['obj_class'] == 'PropertyView':
                # Do not make these timestamps naive. They persist correctly.
                related_dict['db_taxlot_updated'] = related_view.taxlot.updated
                related_dict['db_taxlot_created'] = related_view.taxlot.created

            # Add extra data fields right to this object.
            for extra_data_field, extra_data_value in related_view.state.extra_data.items():
                if extra_data_field == 'id':
                    extra_data_field += '_extra'

                while extra_data_field in db_columns:
                    extra_data_field += '_extra'

                related_dict[extra_data_field] = extra_data_value

            # Only return the requested rows. speeds up the json string time.
            # The front end requests for related columns have 'tax_'/'property_' prepended
            # to them, so check for that too.
            related_dict = {key: value for key, value in related_dict.items() if
                            (key in columns) or ("{}_{}".format(lookups['related_column_key'], key) in columns)}
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

                    # jurisdiction_tax_lot_ids = [""]

                join_dict = related_map[join.property_view_id].copy()
                join_dict.update({
                    'primary': 'P' if join.primary else 'S',
                    'calculated_taxlot_ids': '; '.join(jurisdiction_tax_lot_ids)
                })

            else:
                join_dict = related_map[getattr(join, lookups['related_view_id_name'])].copy()
                join_dict.update({
                    'primary': 'P' if join.primary else 'S',
                    lookups['related_view_id_name']: getattr(join, lookups['related_view_id_name'])
                })

            # fix specific time stamps - total hack right now. Need to reconcile with
            # /data_importer/views.py and /seed/views/properties.py
            if join_dict.get('recent_sale_date'):
                join_dict['recent_sale_date'] = make_naive(join_dict['recent_sale_date']).isoformat()

            if join_dict.get('release_date'):
                join_dict['release_date'] = make_naive(join_dict['release_date']).isoformat()

            if join_dict.get('generation_date'):
                join_dict['generation_date'] = make_naive(join_dict['generation_date']).isoformat()

            try:
                join_map[getattr(join, lookups['obj_view_id'])].append(join_dict)
            except KeyError:
                join_map[getattr(join, lookups['obj_view_id'])] = [join_dict]

        for obj in object_list:
            # Each object in the response is built from the state data, with related data added on.
            obj_dict = model_to_dict(obj.state, exclude=['extra_data'])

            for extra_data_field, extra_data_value in obj.state.extra_data.items():
                if extra_data_field == 'id':
                    extra_data_field += '_extra'

                while extra_data_field in db_columns:
                    extra_data_field += '_extra'

                obj_dict[extra_data_field] = extra_data_value

            # Use property_id instead of default (state_id)
            obj_dict['id'] = getattr(obj, lookups['obj_id_name'])

            obj_dict[lookups['obj_state_id']] = obj.state.id
            obj_dict[lookups['obj_view_id']] = obj.id

            # store the property / taxlot data to the object dictionary as well. This is hacky.
            if lookups['obj_class'] == 'PropertyView':
                obj_dict['campus'] = obj.property.campus
                # Do not make these timestamps naive. They persist correctly.
                obj_dict['db_property_updated'] = obj.property.updated
                obj_dict['db_property_created'] = obj.property.created
            elif lookups['obj_class'] == 'TaxLotView':
                # Do not make these timestamps naive. They persist correctly.
                obj_dict['db_taxlot_updated'] = obj.taxlot.updated
                obj_dict['db_taxlot_created'] = obj.taxlot.created

            # All the related tax lot states.
            obj_dict['related'] = join_map.get(obj.pk, [])

            # fix specific time stamps - total hack right now. Need to reconcile with
            # /data_importer/views.py
            if obj_dict.get('recent_sale_date'):
                obj_dict['recent_sale_date'] = make_naive(obj_dict['recent_sale_date']).isoformat()

            if obj_dict.get('release_date'):
                obj_dict['release_date'] = make_naive(obj_dict['release_date']).isoformat()

            if obj_dict.get('generation_date'):
                obj_dict['generation_date'] = make_naive(obj_dict['generation_date']).isoformat()

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

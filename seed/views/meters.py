# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
# import json

from django.http import JsonResponse
# from django.contrib.auth.decorators import login_required
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import detail_route
from rest_framework.parsers import JSONParser, FormParser

from seed.authentication import SEEDAuthentication
from seed.decorators import require_organization_id_class
# from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    obj_to_dict,
    Meter,
    PropertyView,
)
from seed.utils.api import api_endpoint_class


def _convert_energy_data(name, mapping):
    """Converts human name to integer for DB.

    ``mapping`` looks like ((3, 'Electricity'), (4, 'Natural Gas'))
    See ``ENERGY_TYPES`` and ``ENERGY_UNITS`` in ``seed.models``.

    :parm name: str, the unit or type name from JS.
    :param mapping: tuple of tuples used for Django Meter choices.
    :return: int, the intereger value of the string stored in the DB.
    """
    return filter(lambda x: x[1] == name, [t for t in mapping])[0][0]


class MeterViewSet(viewsets.ViewSet):
    raise_exception = True
    authentication_classes = (SessionAuthentication, SEEDAuthentication)
    parser_classes = (JSONParser, FormParser)

    @api_endpoint_class
    @require_organization_id_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        """
        Returns all of the meters for a property view
        ---
        type:
            status:
                required: true
                type: string
                description: Either success or error
            property_view_id:
                required: true
                type: integer
                description: property view id of the request
            meters:
                required: true
                type: array[meters]
                description: list of meters for property_view_id
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: property_view_id
              description: The property_view_id of the building holding the meter data
              required: true
              paramType: query
        """
        pv_id = request.GET.get('property_view_id', None)
        org_id = request.GET.get('organization_id')

        if pv_id is None:
            return JsonResponse({
                'status': 'error',
                'message': 'No property_view_id specified',
                'meters': []
            })

        # verify that the user has access to view property
        pvs = PropertyView.objects.filter(id=pv_id, state__organization=org_id)
        if pvs.count() == 0:
            return JsonResponse({
                'status': 'success',
                'message': 'No property_ids found for organization',
                'meters': []
            })
        else:
            return JsonResponse({
                'status': 'success',
                'property_view_id': pv_id,
                'meters': [
                    obj_to_dict(m) for m in Meter.objects.filter(property_view=pv_id)
                ]
            })

    @api_endpoint_class
    @has_perm_class('requires_viewer')
    def retrieve(self, request, pk=None):
        """
        Returns a single meter based on its id
        ---
        type:
            status:
                required: true
                type: string
                description: Either success or error
            meters:
                required: true
                type: dict
                description: meter object
        parameters:
            - name: pk
              description: Meter primary key
              required: true
              paramType: path
        """
        meter = Meter.objects.get(pk=pk)
        if meter:
            res = {}
            res['status'] = 'success'
            res['meter'] = obj_to_dict(meter)
            res['meter']['timeseries_count'] = meter.timeseries_set.count()
            return JsonResponse(res)
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'No meter object found',
            })



    @api_endpoint_class
    @require_organization_id_class
    @has_perm_class('requires_member')
    def create(self, request):
        """
        Creates a new project

        :POST: Expects organization_id in query string.
        ---
        parameters:
            - name: organization_id
              description: ID of organization to associate new project with
              type: integer
              required: true
              paramType: query
            - name: property_view_id
              description: Property view id to which to add the meter
              required: true
              paramType: form
            - name: name
              description: name of the new meter
              type: string
              required: true
              paramType: form
            - name: energy_type
              description: type of metered energy
              type: integer
              required: true
              paramType: form
            - name: energy_units
              description: units of energy being metered
              type: integer
              required: true
              paramType: form
        type:
            status:
                required: true
                type: string
                description: Either success or error

        """
        org_id = request.GET.get('organization_id', '')

        # verify that the user has access to view property
        pv_id = request.data['property_view_id']
        pvs = PropertyView.objects.filter(id=pv_id, state__organization=org_id)
        if pvs.count() == 0 or pvs.count() > 1:
            return JsonResponse({
                'status': 'success',
                'message': 'No property id {} found for organization {}'.format(pv_id, org_id),
            })
        else:
            #     energy_type = _convert_energy_data(energy_type_name, ENERGY_TYPES)
            #     energy_units = _convert_energy_data(energy_unit_name, ENERGY_UNITS)
            data = {
                "name": request.data['name'],
                "energy_type": request.data['energy_type'],
                "energy_units": request.data['energy_units'],
                "property_view": pvs.first(),
            }
            m = Meter.objects.create(**data)

            return JsonResponse({
                'status': 'success',
                'meter': obj_to_dict(m),
            })

    @api_endpoint_class
    @has_perm_class('requires_viewer')
    def timeseries(self, request, pk=None):
        """
        Returns timeseries for meter
        ---
        type:
            status:
                required: true
                type: string
                description: Either success or error
            meter:
                required: true
                type: dict
                description: meter information
            data:
                required: true
                type: list
                description: timeseries information
        parameters:
            - name: pk
              description: Meter primary key
              required: true
              paramType: path
        """
        meter = Meter.objects.get(pk=pk)
        res = {}
        res['status'] = 'success'
        res['meter'] = obj_to_dict(meter)
        res['meter']['data'] = []

        ts = meter.timeseries_set.order_by('begin_time')
        for t in ts:
            res['meter']['data'].append({
                'begin': str(t.begin_time),
                'end': str(t.begin_time),
                'value': t.reading,
            })

        return JsonResponse(res)

    @api_endpoint_class
    @has_perm_class('can_modify_data')
    def add_timeseries(self, request, pk=None):
        """
        Returns timeseries for meter
        ---
        type:
            status:
                required: true
                type: string
                description: Either success or error
            meter:
                required: true
                type: dict
                description: meter information
            timeseries:
                required: true
                type: list
                description: timeseries information
        parameters:
            - name: pk
              description: Meter primary key
              required: true
              paramType: path
        """
        # TODO: Finish implementing this
        return JsonResponse({
            'status': 'success',
            'message': 'Not yet implemented'
        })

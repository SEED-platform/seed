# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:authors Paul Munday<paul@paulmunday.net> Fable Turas <fable@raintechpdx.com>
"""
from seed.filtersets import CycleFilterSet
from seed.models import Cycle
from seed.pagination import NoPagination

from seed.serializers.cycles import CycleSerializer
from seed.utils.viewsets import SEEDOrgModelViewSet


class CycleViewSet(SEEDOrgModelViewSet):
    """API endpoint for viewing and creating cycles (time periods).

        Returns::
            {
                'status': 'success',
                'cycles': [
                    {
                        'id': Cycle`s primary key,
                        'name': Name given to cycle,
                        'start': Start date of cycle,
                        'end': End date of cycle,
                        'created': Created date of cycle,
                        'properties_count': Count of properties in cycle,
                        'taxlots_count': Count of tax lots in cycle,
                        'organization': Id of organization cycle belongs to,
                        'user': Id of user who created cycle
                    }
                ]
            }


    retrieve:
        Return a cycle instance by pk if it is within user`s specified org.

        :GET: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: cycle pk
            :Description: id for desired cycle
            :required: true

    list:
        Return all cycles available to user through user`s specified org.

        :GET: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: name
            :Description: optional name for filtering cycles
            :required: false
            :Parameter: start_lte
            :Description: optional iso date for filtering by cycles
                that start on or before the given date
            :required: false
            :Parameter: end_gte
            :Description: optional iso date for filtering by cycles
                that end on or after the given date
            :required: false

    create:
        Create a new cycle within user`s specified org.

        :POST: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: name
            :Description: cycle name
            :required: true
            :Parameter: start
            :Description: cycle start date. format: ``YYYY-MM-DDThh:mm``
            :required: true
            :Parameter: end
            :Description: cycle end date. format: ``YYYY-MM-DDThh:mm``
            :required: true

    delete:
        Remove an existing cycle.

        :DELETE: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: cycle pk
            :Description: id for desired cycle
            :required: true

    update:
        Update a cycle record.

        :PUT: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: cycle pk
            :Description: id for desired cycle
            :required: true
            :Parameter: name
            :Description: cycle name
            :required: true
            :Parameter: start
            :Description: cycle start date. format: ``YYYY-MM-DDThh:mm``
            :required: true
            :Parameter: end
            :Description: cycle end date. format: ``YYYY-MM-DDThh:mm``
            :required: true

    partial_update:
        Update one or more fields on an existing cycle.

        :PUT: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: cycle pk
            :Description: id for desired cycle
            :required: true
            :Parameter: name
            :Description: cycle name
            :required: false
            :Parameter: start
            :Description: cycle start date. format: ``YYYY-MM-DDThh:mm``
            :required: false
            :Parameter: end
            :Description: cycle end date. format: ``YYYY-MM-DDThh:mm``
            :required: false
    """
    serializer_class = CycleSerializer
    pagination_class = NoPagination
    model = Cycle
    data_name = 'cycles'
    filter_class = CycleFilterSet

    def get_queryset(self):
        org_id = self.get_organization(self.request)
        # Order cycles by name because if the user hasn't specified then the front end WILL default to the first
        return Cycle.objects.filter(organization_id=org_id).order_by('name')

    def perform_create(self, serializer):
        org_id = self.get_organization(self.request)
        user = self.request.user
        serializer.save(organization_id=org_id, user=user)

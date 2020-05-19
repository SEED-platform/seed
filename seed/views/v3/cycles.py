# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:authors Paul Munday<paul@paulmunday.net> Fable Turas <fable@raintechpdx.com>
"""
from seed.models import Cycle

from seed.serializers.cycles import CycleSerializer
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet
from seed.utils.api_schema import AutoSchemaHelper


class CycleSchema(AutoSchemaHelper):
    def __init__(self, *args):
        super().__init__(*args)

        self.manual_fields = {
            ('GET', 'list'): [self.org_id_field()],
            ('POST', 'create'): [self.org_id_field()],
            ('GET', 'retrieve'): [self.org_id_field()],
            ('PUT', 'update'): [self.org_id_field()],
            ('DELETE', 'destroy'): [self.org_id_field()],
        }


class CycleViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
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

    list:

        Return all cycles available to user through user`s specified org.

    create:
        Create a new cycle within user`s specified org.

    delete:
        Remove an existing cycle.

    update:
        Update a cycle record.

    """
    serializer_class = CycleSerializer
    swagger_schema = CycleSchema
    pagination_class = None
    model = Cycle
    data_name = 'cycles'

    def get_queryset(self):
        org_id = self.get_organization(self.request)
        # Order cycles by name because if the user hasn't specified then the front end WILL default to the first
        return Cycle.objects.filter(organization_id=org_id).order_by('name')

    def perform_create(self, serializer):
        org_id = self.get_organization(self.request)
        user = self.request.user
        serializer.save(organization_id=org_id, user=user)

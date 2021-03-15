# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from seed.filtersets import GAPropertyFilterSet
from seed.models import GreenAssessmentProperty
from seed.serializers.certification import GreenAssessmentPropertySerializer
from seed.utils.viewsets import SEEDOrgModelViewSet


class GreenAssessmentPropertyViewSet(SEEDOrgModelViewSet):
    """API endpoint to view and create green assessment property attachments.

        Returns::
            {
                'status': 'success',
                'data': [
                    {
                        'id': Green Assessment primary key,
                        'source': Source of this certification e.g. assessor,
                        'status': Status for multi-step processes,
                        'status_date': date status first applied,
                        'metric': score if value is numeric,
                        'rating': score if value is non-numeric,
                        'version': version of certification issued,
                        'date': date certification issued,
                        'target_date': date achievement of cert is expected,
                        'eligibility': BEDES eligibility,
                        'expiration_date': date certification expires,
                        'is_valid': state of certification validity,
                        'year': year certification was awarded,
                        'urls': array of related green assessment urls,
                        'assessment': dict of associated green assessment data,
                        'view': dict of associated property view data,
                    }
                ]
            }


    retrieve:
        Return an assessment property instance by pk if its associated
        assessment is within the specified organization.

    list:
        Return all green assessment properties available to user through
        associated green assessment via specified organization.

    create:
        Create a new green assessment property within user`s specified org.

    delete:
        Remove an existing green assessment property.

    update:
        Update a green assessment property record.

    partial_update:
        Update one or more fields on an existing green assessment...
    """
    serializer_class = GreenAssessmentPropertySerializer
    model = GreenAssessmentProperty
    orgfilter = 'assessment__organization_id'
    filter_class = GAPropertyFilterSet

    @action(detail=True, methods=['get'])
    def reso_format(self, request, pk=None):
        """Return an assessment property instance by pk in reso format"""
        assessment = self.get_object()
        status_code = status.HTTP_200_OK
        return Response(assessment.to_reso_dict(), status=status_code)

    @action(detail=True, methods=['get'])
    def bedes_format(self, request, pk=None):
        """Return an assessment property instance by pk in bedes format"""
        assessment = self.get_object()
        status_code = status.HTTP_200_OK
        return Response(assessment.to_bedes_dict(), status=status_code)

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
"""

from seed.models import GreenAssessmentURL
from seed.serializers.certification import GreenAssessmentURLSerializer
from seed.utils.viewsets import SEEDOrgModelViewSet


class GreenAssessmentURLViewSet(SEEDOrgModelViewSet):

    """API endpoint for viewing and creating green assessment urls.

        Returns::
            {
                'status': 'success',
                'data': [
                    {
                        'id': Green Assessment Url primary key,
                        'url': link to rating or scoring details for premises,
                        'property_assessment': id of associated property
                    }
                ]
            }


    retrieve:
        Return a green assessment url instance by pk if its associated
        assessment property is within the specified organization.

        :GET: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: green assessment url pk
            :Description: id for desired green assessment url
            :required: true

    list:
        Return green assessment urls available to user through specified org.

        :GET: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true

    create:
        Create a new green assessment url.

        :POST: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: url
            :Description: link to rating or scoring details for premises
            :required: true
            :Parameter: property_assessment
            :Description: id for associated green assessment url
            :required: true

    delete:
        Remove an existing green assessment url.

        :DELETE: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: green assessment url pk
            :Description: id for desired green assessment url
            :required: true

    update:
        Update a green assessment url record.

        :PUT: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: url
            :Description: link to rating or scoring details for premises
            :required: true
            :Parameter: property_assessment
            :Description: id for associated green assessment url
            :required: true

    partial_update:
        Update one or more fields on an existing green assessment url.

        :PUT: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: url
            :Description: link to rating or scoring details for premises
            :required: false
            :Parameter: property_assessment
            :Description: id for associated green assessment url
            :required: false

    """
    serializer_class = GreenAssessmentURLSerializer
    model = GreenAssessmentURL
    orgfilter = 'property_assessment__assessment__organization_id'
    filter_fields = ('property_assessment__id',)

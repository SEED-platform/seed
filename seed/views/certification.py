# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Paul Munday <paul@paulmunday.net>
"""

from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response

from seed.filtersets import GAPropertyFilterSet, GreenAssessmentFilterSet
from seed.models import (
    GreenAssessment,
    GreenAssessmentProperty,
    GreenAssessmentURL
)

from seed.serializers.certification import (
    GreenAssessmentSerializer,
    GreenAssessmentPropertySerializer,
    GreenAssessmentURLSerializer
)

from seed.utils.viewsets import (
    SEEDOrgModelViewSet,
    SEEDOrgCreateUpdateModelViewSet
)


class GreenAssessmentViewSet(SEEDOrgCreateUpdateModelViewSet):
    """API endpoint for viewing and creating green assessment certifications.

        Returns::
            {
                'status': 'success',
                'data': [
                    {
                        'id': Green Assessment primary key,
                        'name': Name given to green assessment,
                        'award_body': Name of body issuing assessment,
                        'recognition_type': assessment recognition type,
                        'recognition_description': description of assessment,
                        'is_numeric_score': assessment score is a numeric,
                        'is_integer_score': assessment score is an integer,
                        'validity_duration': duration of assessment validity,
                        'organization': Id of org assessment associated with
                    }
                ]
            }


    retrieve:
        Return a green assessment instance by pk if it is within specified org.

        :GET: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: green assessment pk
            :Description: id for desired green assessment
            :required: true

    list:
        Return all green assessments available to user through specified org.

        :GET: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true

    create:
        Create a new green assessment within user`s specified org.

        :POST: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: name
            :Description: green assessment name
            :required: false
            :Parameter: award_body
            :Description: name of body issuing assessment
            :required: false
            :Parameter: recognition_type
            :Description: recognition type selection
            :required: false
            :Parameter: is_numeric_score
            :Description: score is numeric value if true
            :required: false
            :Parameter: is_integer_score
            :Description: score is integer value if true
            :required: false
            :Parameter: validity_duration
            :Description: duration of assessment validity. ``[DD] [HH:[MM:]]``
            :required: false

    delete:
        Remove an existing green assessment.

        :DELETE: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: green assessment pk
            :Description: id for desired green assessment
            :required: true

    update:
        Update a green assessment record.

        :PUT: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: green assessment pk
            :Description: id for desired green assessment
            :required: true
            :Parameter: name
            :Description: green assessment name
            :required: false
            :Parameter: award_body
            :Description: name of body issuing assessment
            :required: false
            :Parameter: recognition_type
            :Description: recognition type selection
            :required: false
            :Parameter: is_numeric_score
            :Description: score is numeric value if true
            :required: false
            :Parameter: is_integer_score
            :Description: score is integer value if true
            :required: false
            :Parameter: validity_duration
            :Description: duration of assessment validity. ``[DD] [HH:[MM:]]``
            :required: false

    partial_update:
        Update one or more fields on an existing green assessment.

        :PUT: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: green assessment pk
            :Description: id for desired green assessment
            :required: true
            :Parameter: name
            :Description: green assessment name
            :required: false
            :Parameter: award_body
            :Description: name of body issuing assessment
            :required: false
            :Parameter: recognition_type
            :Description: recognition type selection
            :required: false
            :Parameter: is_numeric_score
            :Description: score is numeric value if true
            :required: false
            :Parameter: is_integer_score
            :Description: score is integer value if true
            :required: false
            :Parameter: validity_duration
            :Description: duration of assessment validity. ``[DD] [HH:[MM:]]``
            :required: false
    """
    serializer_class = GreenAssessmentSerializer
    model = GreenAssessment
    filter_class = GreenAssessmentFilterSet


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

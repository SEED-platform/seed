# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
"""

from seed.filtersets import GreenAssessmentFilterSet
from seed.models import GreenAssessment
from seed.serializers.certification import GreenAssessmentSerializer
from seed.utils.viewsets import SEEDOrgCreateUpdateModelViewSet


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

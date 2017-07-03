# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Paul Munday <paul@paulmunday.net>
"""
from collections import OrderedDict, Sequence
from datetime import timedelta
from django.core.exceptions import ValidationError

from rest_framework import serializers

from seed.models import (
    GreenAssessment, GreenAssessmentProperty, GreenAssessmentURL,
    PropertyView
)

from seed.models.auditlog import AUDIT_USER_CREATE
from seed.utils.api import OrgValidator, OrgValidateMixin

ASSESSMENT_VALIDATOR = OrgValidator('assessment', 'organization_id')
ASSESSMENT_PROPERTY_VALIDATOR = OrgValidator(
    'property_assessment', 'assessment__organization_id'
)
PROPERTY_VIEW_VALIDATOR = OrgValidator('view', 'property__organization_id')


class GreenAssessmentField(serializers.PrimaryKeyRelatedField):
    """Display serialized assessment but set using id"""

    def to_representation(self, value):
        """Serialize GreenAssessment"""
        green_assessment = GreenAssessment.objects.get(pk=value.pk)
        return GreenAssessmentSerializer(green_assessment).data


class GreenAssessmentURLField(serializers.ListField):
    """De/Serialize urls attached to GreenAssessmentProperty"""
    child = serializers.URLField()
    allow_empty = True

    def to_representation(self, obj):
        """Return list of attached urls"""
        urls = list(obj.all())
        return [(url.url, url.description) for url in urls]


class PropertyViewField(serializers.PrimaryKeyRelatedField):
    """Display serialized assessment but set using id"""

    def to_representation(self, value):
        """Serialize PropertyView"""
        property_view = PropertyView.objects.get(id=value.pk)
        state = property_view.state
        cycle = property_view.cycle
        start = '{}-{}-{}'.format(
            cycle.start.year, cycle.start.month, cycle.start.day
        )
        end = '{}-{}-{}'.format(
            cycle.end.year, cycle.end.month, cycle.end.day
        )
        cycle_dict = OrderedDict((
            ('id', cycle.id),
            ('start', start),
            ('end', end)
        ))
        address_line_1 = state.normalized_address.title()\
            if state.normalized_address else None
        return OrderedDict((
            ('id', value.pk),
            ('address_line_1', address_line_1),
            ('address_line_2', state.address_line_2),
            ('city', state.city),
            ('state', state.state),
            ('postal_code', state.postal_code),
            ('property', property_view.property.id),
            ('cycle', cycle_dict)
        ))


class ValidityDurationField(serializers.Field):
    """Serialize validity_duration (as number of days)."""

    def to_representation(self, obj):
        """Serialize as number of days"""
        return obj.days

    def to_internal_value(self, data):
        if isinstance(data, basestring):
            try:
                data = int(data)
            except ValueError:
                raise ValidationError(
                    'validity_duration must be an integer or None.'
                )

        if not isinstance(data, (int, type(None))):
            raise ValidationError(
                'validity_duration must be an integer or None.'
            )
        if data is not None and not (data > 0):
            raise ValidationError(
                'validity_duration should be a number of days > 0.'
            )
        validity_duration = None
        if isinstance(data, int):
            validity_duration = timedelta(days=data)
        return validity_duration


class GreenAssessmentSerializer(serializers.ModelSerializer):

    recognition_type = serializers.ChoiceField(
        GreenAssessment.RECOGNITION_TYPE_CHOICES
    )
    recognition_description = serializers.SerializerMethodField()
    validity_duration = ValidityDurationField(required=False)

    class Meta:
        model = GreenAssessment
        fields = (
            'id', 'name', 'award_body', 'recognition_type',
            'recognition_description', 'description', 'is_numeric_score',
            'is_integer_score', 'validity_duration'
        )

    def get_recognition_description(self, obj):
        """Human readable recognition_type"""
        return obj.get_recognition_type_display()


class GreenAssessmentPropertySerializer(OrgValidateMixin,
                                        serializers.ModelSerializer):

    # use all for queryset as model ensures orgs match
    assessment = GreenAssessmentField(
        queryset=GreenAssessment.objects.all(), allow_null=True
    )
    view = PropertyViewField(
        queryset=PropertyView.objects.all(), allow_null=True
    )
    urls = GreenAssessmentURLField(allow_empty=True, required=False)
    # specify to ensure @property based fields are writable
    metric = serializers.FloatField(required=False, allow_null=True)
    rating = serializers.CharField(
        required=False, allow_null=True, max_length=100)
    # ensure reuqest.users org matches that of view and assessment
    org_validators = [ASSESSMENT_VALIDATOR, PROPERTY_VIEW_VALIDATOR]

    def __init__(self, *args, **kwargs):
        """Override to allow dynamic control of view display"""
        no_view = kwargs.pop('no_view', None)
        super(GreenAssessmentPropertySerializer, self).__init__(*args, **kwargs)
        if no_view:
            self.fields.pop('view')

    class Meta:
        model = GreenAssessmentProperty
        depth = 1
        fields = ('id', 'source', 'status', 'status_date', 'score',
                  'metric', 'rating', 'version', 'date', 'target_date',
                  'eligibility', 'expiration_date', 'is_valid', 'year',
                  'urls', 'assessment', 'view')

    def create(self, validated_data):
        """Override create to handle urls"""
        urls = get_url_list(validated_data.pop('urls', []))
        request = self.context.get('request', None)
        user = getattr(request, 'user', None)
        instance = super(GreenAssessmentPropertySerializer, self).create(
            validated_data
        )
        initial_log = instance.initialize_audit_logs(
            user=user,
            changed_fields=unicode(validated_data),
            description="Created by api call."
        )
        GreenAssessmentURL.objects.bulk_create(
            [
                GreenAssessmentURL(property_assessment=instance, url=url)
                for url in urls
            ]
        )
        if urls:
            instance.log(
                user=user,
                changed_fields="urls: {}".format(urls),
                description="Urls added by create api call.",
                record_type=AUDIT_USER_CREATE,
                ancestor=initial_log,
                parent=initial_log
            )
        return instance

    def update(self, instance, validated_data):
        """Override create to handle urls"""
        urls = get_url_list(validated_data.pop('urls', []))
        request = self.context.get('request', None)
        user = getattr(request, 'user', None)
        instance = super(GreenAssessmentPropertySerializer, self).update(
            instance, validated_data
        )
        log = instance.log(
            user=user,
            changed_fields=unicode(validated_data),
            description="Updated by api call."
        )
        # PATCH request, remove exisiting urls only if urls is supplied
        # PUT request, always remove urls
        # remove any existing urls not in urls
        if urls or not self.partial:
            all_urls = GreenAssessmentURL.objects.filter(
                property_assessment=instance
            )
            existing = all_urls.filter(url__in=urls).values_list(
                'url', 'description',
            )
            # delete any not supplied
            to_delete = all_urls.exclude(url__in=urls)
            deleted = list(to_delete)
            to_delete.delete()
            # create any that don't exist
            urls = urls - set(existing)
            GreenAssessmentURL.objects.bulk_create(
                [
                    GreenAssessmentURL(
                        property_assessment=instance,
                        url=url[0], description=url[1]
                    ) for url in urls
                ]
            )
            instance.log(
                user=user,
                changed_fields="added urls: {}".format(urls),
                description="Urls added by update serializer method",
                parent=log,
                ancestor=log.ancestor
            )
            if deleted:
                instance.log(
                    user=user,
                    changed_fields="deleted urls: {}".format(urls),
                    description="Urls deleted by update serializer method",
                    parent=log,
                    ancestor=log.ancestor
                )
        return instance

    def validate(self, data):
        """Object level validation."""
        # Only rating, metric can be supplied
        scores = ([
            elem for elem in [
                data.get('metric'), data.get('rating')
            ] if elem is not None
        ])
        if len(scores) > 1:
            msg = 'Only one of metric or rating can be supplied.'
            raise ValidationError(msg)

        # check rating/metric type
        assessment = data.get('assessment')
        if not assessment and self.instance:
            assessment = getattr(self.instance, 'assessment', None)
        if not assessment:
            raise ValidationError('Could not find assessment.')

        rating = data.get('rating')
        if rating and assessment.is_numeric_score:
            msg = "{} uses a metric (numeric score).".format(assessment.name)
            raise ValidationError(msg)
        elif rating and not isinstance(rating, basestring):
            raise ValidationError('Rating must be a string.')

        metric = data.get('metric')
        if metric and not assessment.is_numeric_score:
            msg = "{} uses a rating (non numeric score).".format(
                assessment.name
            )
            raise ValidationError(msg)
        if metric:
            try:
                float(metric)
            except ValueError:
                raise ValidationError('Metric must be a number.')
            if assessment.is_integer_score and not float(int(metric)) == metric:
                raise ValidationError('Metric must be an integer.')
        # validate org_ids match
        return super(GreenAssessmentPropertySerializer, self).validate(data)


class GreenAssessmentURLSerializer(OrgValidateMixin, serializers.ModelSerializer):
    # ensure reuqest.users org matches that property_assessment
    org_validators = [ASSESSMENT_PROPERTY_VALIDATOR]

    class Meta:
        model = GreenAssessmentURL


class GreenAssessmentPropertyReadOnlySerializer(serializers.BaseSerializer):
    """Simple read only Serializer describing Green Assessment attached to
    property. Use with prefetch_related to avoid extra database calls.
    """

    def to_representation(self, obj):
        """Serialize green assessment property"""
        urls = [(url.url, url.description) for url in obj.urls.all()]
        assessment = OrderedDict((
            ('id', obj.assessment.id),
            ('name', obj.assessment.name),
            ('award_body', obj.assessment.award_body),
            ('recognition_type', obj.assessment.recognition_type),
            ('recognition_description',
             obj.assessment.get_recognition_type_display()),
            ('description', obj.assessment.description),
            ('is_numeric_score', obj.assessment.is_numeric_score),
            ('is_integer_score', obj.assessment.is_integer_score),
            (
                'validity_duration',
                str(obj.assessment.validity_duration)
                if obj.assessment.validity_duration else None
            ),
        ))
        return OrderedDict((
            ('id', obj.id),
            ('source', obj.source),
            ('status', obj.status),
            (
                'status_date',
                obj.status_date.ctime() if obj.status_date else None
            ),
            ('score', obj.score),
            ('metric', obj.metric),
            ('rating', obj.rating),
            ('version', obj.version),
            (
                'target_date',
                obj.target_date.ctime() if obj.target_date else None
            ),
            (
                'expiration_date',
                obj.expiration_date.ctime() if obj.expiration_date else None
            ),
            ('is_valid', obj.is_valid),
            ('year', obj.year),
            ('date', obj.date),
            ('urls', urls),
            ('assessment', assessment)
        ))


def get_url_list(url_list):
    """Simple helper functions to allow urls supplied as string or seq"""
    return set([
        (url[0], url[1]) if isinstance(url, Sequence) else (url, None)
        for url in url_list
    ])

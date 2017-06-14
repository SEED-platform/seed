# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Paul Munday <paul@paulmunday.net>
"""
# pylint:disable=too-few-public-methods
from __future__ import unicode_literals
import datetime

# import logging

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import JSONField

from seed.lib.superperms.orgs.models import Organization
from seed.models.auditlog import (
    AUDIT_USER_EDIT,
    AUDIT_USER_CREATE,
    DATA_UPDATE_TYPE
)
from seed.landing.models import SEEDUser
from seed.models import PropertyView

DEFAULT_GREEN_ASSESSEMENT_VALIDITY_DURATION = getattr(
    settings, 'GREEN_ASSESSMENT_DEFAULT_VALIDITY_DURATION', None
)
if DEFAULT_GREEN_ASSESSEMENT_VALIDITY_DURATION:
    DEFAULT_GREEN_ASSESSEMENT_VALIDITY_DURATION = datetime.timedelta(
        DEFAULT_GREEN_ASSESSEMENT_VALIDITY_DURATION
    )

# logger = logging.getLogger(__name__)


class GreenAssessment(models.Model):
    """
    Green assessments shared properties (name etc)
    Mapping to RESO/BEDES
    Model       RESO                            BEDES
    name        GreenBuildingVerificationType   Assessment Program
    award_body  GreenVerification[Type]Body     Assessment Program Organization
    recognition_type    n/a                     Assessment Recognition Type
    description n/a                             n/a
    """
    AWARD = "AWD"
    CERTIFICATION = "CRT"
    LABEL = "LBL"
    PARTICIPANT = "PRT"
    RATING = "RAT"
    SCORE = "SCR"
    ZERO = "ZER"
    RECOGNITION_TYPE_CHOICES = (
        (AWARD, "Award"),
        (CERTIFICATION, "Certification"),
        (LABEL, "Label"),
        (PARTICIPANT, "Participant"),
        (RATING, "Rating"),
        (SCORE, "Score"),
        (ZERO, "Zero Energy Ready Home")
    )
    # A DOE Zero Energy Ready Home is a high performance home which is so energy
    # efficient, that a renewable energy system can offset all or most of its
    # annual energy consumption.

    def __unicode__(self):
        # pylint:disable=no-member
        return u"{}, {}, {}".format(
            self.award_body, self.name,
            self.get_recognition_type_display()
        )

    organization = models.ForeignKey(Organization)
    # assessment name (General - use PropertyGreenVerification.rating for
    # particular certification awarded).
    name = models.CharField(max_length=255)
    # name of body issuing assessment
    # called award_body because older versions of swagger overwrite the body
    # of a POST etc with the contents of a field called 'body' in POST data
    award_body = models.CharField(max_length=100, null=True, blank=True)
    recognition_type = models.CharField(
        max_length=3, choices=RECOGNITION_TYPE_CHOICES, default=CERTIFICATION
    )
    # not in BEDES/RESO
    description = models.TextField(null=True, blank=True)
    is_numeric_score = models.BooleanField()
    is_integer_score = models.BooleanField(default=True)
    validity_duration = models.DurationField(
        null=True, blank=True,
        default=DEFAULT_GREEN_ASSESSEMENT_VALIDITY_DURATION
    )

    class Meta:
        unique_together = ("organization", "name", "award_body")


class GreenAssessmentProperty(models.Model):
    """
    Green assessment (certifications) attached to a property.
    Compatible with RESO v1.5/BEDES
    Max lengths for Charfields set to 2 x RESO recommendation.
    Mapping to RESO/BEDES
    Model       RESO                            BEDES
    source      GreenVerification[Type]Source   n/a
    status      GreenVerification[Type]Status   Assessment Recognition Status
    status_date n/a                             Assessment Recognition Status Date
    metric      GreenVerification[Type]Metric   Assessment Value
    rating      GreenVerification[Type]Rating   Assessment Level
    url         GreenVerification[Type]URL      Assessment Program URL
    version     GreenVerification[Type]Version  Assessment Version
    date/year   GreenVerification[Type]Year     Assessment Year
    target_date n/a                             Assessment Recognition Target Date
    eligibility n/a                             Assessment Eligibility
    @properties:
    name        GreenBuildingVerificationType   Assessment Program
    body        GreenVerification[Type]Body     Assessment Program Organization
    """
    # pylint:disable=no-member

    MAPPING = {
        # attribute: RESO field, BEDES field
        'name': ('GreenBuildingVerificationType', 'Assessment Program'),
        'body': (
            'GreenVerification{}Body', 'Assessment Program Organization'
        ),
        'recognition_description': (None, 'Assessment Recognition Type'),
        'source': ('GreenVerification{}Source', None),
        'status': (
            'GreenVerification{}Status', 'Assessment Recognition Status'
        ),
        'status_date': (None, 'Assessment Recognition Status Date'),
        'metric': ('GreenVerification{}Metric', 'Assessment Value'),
        'rating': ('GreenVerification{}Rating', 'Assessment Level'),
        'version': (
            'GreenVerification{}Version', 'Assessment Version'
        ),
        'year': ('GreenVerification{}Year', 'Assessment Year'),
        'target_date': (None, 'Assessment Recognition Target Date'),
        'eligibility': (None, 'Assessment Eligibility'),
    }

    def __unicode__(self):
        return u"{}, {}: {}".format(
            self.body, self.name, self.metric if self.metric else self.rating
        )

    view = models.ForeignKey(PropertyView)
    # Describes certification
    assessment = models.ForeignKey(GreenAssessment, on_delete=models.PROTECT)
    # Source of this certification e.g. assessor
    source = models.CharField(max_length=50, null=True, blank=True)
    # optional field  to indicate status for multi-step processes
    status = models.CharField(max_length=50, null=True, blank=True)
    # date status first applied
    status_date = models.DateField(null=True, blank=True)
    # Used for numeric scores
    _metric = models.FloatField(null=True, blank=True)
    # Scores *not* expressed as a number
    _rating = models.CharField(max_length=100, null=True, blank=True)
    # version of certification issued
    version = models.CharField(max_length=50, null=True, blank=True)
    # date cert issued (year in RESO)
    date = models.DateField(null=True, blank=True)
    # date property is expected to achieve certification/3rd party verification
    target_date = models.DateField(null=True, blank=True)
    # BEDES only (Eligible/Not eligible)
    eligibility = models.NullBooleanField()
    # not BEDES/RESO.
    # optional expiration date
    _expiration_date = models.DateField(null=True, blank=True)
    # Allow for use defined fields
    extra_data = JSONField(default=dict, blank=True)

    @property
    def expiration_date(self):
        """Return expiration date"""
        expiration_date = self._expiration_date
        if (not expiration_date
                and self.assessment.validity_duration and self.date):
            expiration_date = self.date + self.assessment.validity_duration
        return expiration_date

    @expiration_date.setter
    def expiration_date(self, date):
        """Set expiration date"""
        self._expiration_date = date

    @property
    def is_valid(self):
        """Check if cert is still valid."""
        validity = True
        if self.expiration_date:
            validity = self.expiration_date > datetime.date.today()
        return validity

    @property
    def year(self):
        """Return year awarded"""
        return self.date.year if self.date else None

    @property
    def name(self):
        """Assessment name"""
        return self.assessment.name

    @property
    def body(self):
        """Assessment body"""
        return self.assessment.award_body

    @property
    def metric(self):
        """"Numeric assessment score"""
        return int(self._metric) if (
            self.assessment.is_integer_score and self._metric
        ) else self._metric

    @metric.setter
    def metric(self, value):
        """"Set numeric assessment score/metric"""
        if value:
            if self.assessment and not self.assessment.is_numeric_score:
                msg = "{} uses a rating (non numeric score)".format(self.name)
                raise ValidationError(msg)
            self._metric = float(value)

    @property
    def organization(self):
        """Set by property assessment."""
        return self.assessment.organization

    @property
    def rating(self):
        """"Non numeric assessment score"""
        return self._rating

    @rating.setter
    def rating(self, value):
        """"Set non numeric assessment score/rating"""
        if value:
            if self.assessment.is_numeric_score:
                msg = "{} uses a metric (numeric score)".format(self.name)
                raise ValidationError(msg)
            self._rating = value

    @property
    def recognition_type(self):
        """Assessment Recognition Type"""
        # BEDES only (Enumerated)
        return self.assessment.recognition_type

    @property
    def recognition_description(self):
        """Assessment Recognition Type (human readable)"""
        # BEDES only (Enumerated)
        return self.assessment.get_recognition_type_display()

    @property
    def score(self):
        """
        Rating or metric: determined by self.assessment.is_numeric_score.
        """
        return self.metric if self.assessment.is_numeric_score else self.rating

    @score.setter
    def score(self, value):
        """
        Set rating or metric
        """
        if self.assessment.is_numeric_score:
            self.metric = float(value)
        else:
            self.rating = value

    def initialize_audit_logs(self, **kwargs):
        """Set up inital log."""
        kwargs.update({
            'organization': self.assessment.organization,
            'property_view': self.view,
            'greenassessmentproperty': self,
            'record_type': AUDIT_USER_CREATE
        })
        kwargs.setdefault('name', 'New record')
        kwargs.setdefault('description', 'New audit log added on creation.')
        return GreenAssessmentPropertyAuditLog.objects.create(**kwargs)

    def log(self, **kwargs):
        """Add a log to record changes."""
        kwargs.update({
            'organization': self.assessment.organization,
            'property_view': self.view,
            'greenassessmentproperty': self,
        })
        kwargs.setdefault('record_type', AUDIT_USER_EDIT)
        kwargs.setdefault('name', 'Update log')
        kwargs.setdefault('description', 'New audit log added.')
        if 'parent' not in kwargs or 'ancestor' not in kwargs:
            previous_log = GreenAssessmentPropertyAuditLog.objects.filter(
                greenassessmentproperty=self
            ).order_by('created').last()
            if previous_log:
                kwargs.setdefault('ancestor', previous_log.ancestor)
                kwargs.setdefault('parent', previous_log)
        return GreenAssessmentPropertyAuditLog.objects.create(**kwargs)

    def to_bedes_dict(self):
        """
        Return a dict where keys are BEDES compatible names.
        """
        bedes_dict = {}
        for key, val in self.MAPPING.iteritems():
            field = val[1]
            if field:
                bedes_dict[field] = getattr(self, key)

        urls = [url.url for url in self.urls.all()]
        bedes_dict['Assessment Program URL'] = urls
        return bedes_dict

    def to_reso_dict(self, sub_name=False):
        """
        Return a dict where keys are RESO Green Verification compatible names.
        RESO Green Verification field names may optionally contain the type
        (i.e. name). e.g. GreenVerification[Type]Body
        :param sub_name: add name to key
        :type sub_name: bool
        """
        if isinstance(sub_name, basestring):
            sub = sub_name
        elif sub_name:
            sub = sub = "".join([word.title() for word in self.name.split()])
        else:
            sub = ''
        url_field = 'GreenVerification{}URL'.format(sub)
        reso_dict = {}
        for key, val in self.MAPPING.iteritems():
            field = val[0]
            if field == 'GreenBuildingVerificationType':
                reso_dict[field] = self.name
            elif field:
                field = field.format(sub)
                reso_dict[field] = getattr(self, key)
        reso_dict[url_field] = [url.url for url in self.urls.all()]
        return reso_dict


class GreenAssessmentURL(models.Model):
    """
    A link to the specific rating or scoring details for the premises
    directly from and hosted by the sponsoring body of the program.
    """
    # pylint:disable=no-member
    url = models.URLField()
    property_assessment = models.ForeignKey(
        GreenAssessmentProperty, on_delete=models.CASCADE,
        related_name='urls'
    )
    # field for link text etc
    description = models.CharField(max_length=255, null=True, blank=True)

    @property
    def organization(self):
        """Set by property assessment."""
        return self.property_assessment.organization


class GreenAssessmentPropertyAuditLog(models.Model):
    """Log changes to GreenAssessmentProperty"""
    organization = models.ForeignKey(Organization)
    user = models.ForeignKey(SEEDUser, blank=True, null=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    changed_fields = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    record_type = models.IntegerField(choices=DATA_UPDATE_TYPE, null=True,
                                      blank=True)
    created = models.DateTimeField(auto_now_add=True, null=True)
    greenassessmentproperty = models.ForeignKey(
        GreenAssessmentProperty,
        related_name="gapauditlog__assessment"
    )
    property_view = models.ForeignKey(
        PropertyView, related_name='gapauditlog__view', null=True
    )
    ancestor = models.ForeignKey(
        'GreenAssessmentPropertyAuditLog', blank=True, null=True,
        related_name='gapauditlog__ancestor'
    )
    parent = models.ForeignKey(
        'GreenAssessmentPropertyAuditLog', blank=True, null=True,
        related_name='gapauditlog__parent'
    )

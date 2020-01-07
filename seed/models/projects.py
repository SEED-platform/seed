# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from autoslug import AutoSlugField
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.models import TimeStampedModel

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.utils.generic import obj_to_dict


class Project(TimeStampedModel):
    PROJECT_NAME_MAX_LENGTH = 255

    INACTIVE_STATUS = 0
    ACTIVE_STATUS = 1
    STATUS_CHOICES = (
        (INACTIVE_STATUS, _('Inactive')),
        (ACTIVE_STATUS, _('Active')),
    )

    name = models.CharField(_('name'), max_length=PROJECT_NAME_MAX_LENGTH)
    slug = AutoSlugField(
        _('slug'), populate_from='name', unique=True, editable=True
    )
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name=_('User'), blank=True, null=True
    )
    last_modified_by = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True, related_name='last_modified_user'
    )
    super_organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        verbose_name=_('SeedOrg'),
        blank=True,
        null=True,
        related_name='projects'
    )
    description = models.TextField(_('description'), blank=True, null=True)
    status = models.IntegerField(
        _('status'), choices=STATUS_CHOICES, default=ACTIVE_STATUS
    )
    property_views = models.ManyToManyField(
        'PropertyView', through="ProjectPropertyView", blank=True
    )
    taxlot_views = models.ManyToManyField(
        'TaxLotView', through="ProjectTaxLotView", blank=True
    )

    @property
    def property_count(self):
        return self.property_views.count()

    @property
    def taxlot_count(self):
        return self.taxlot_views.count()

    @property
    def adding_buildings_status_percentage_cache_key(self):
        return "SEED_PROJECT_ADDING_BUILDINGS_PERCENTAGE_%s" % self.slug

    @property
    def removing_buildings_status_percentage_cache_key(self):
        return "SEED_PROJECT_REMOVING_BUILDINGS_PERCENTAGE_%s" % self.slug

    @property
    def has_compliance(self):
        return self.compliance_set.exists()

    @property
    def organization(self):
        """For compliance with organization names in new data model."""
        return self.super_organization

    def __str__(self):
        return "Project %s" % (self.name,)

    def get_compliance(self):
        if self.has_compliance:
            return self.compliance_set.all()[0]
        else:
            return None

    def to_dict(self):
        return obj_to_dict(self)


class ProjectPropertyView(TimeStampedModel):
    property_view = models.ForeignKey(
        'PropertyView', on_delete=models.CASCADE, related_name='project_property_views'
    )
    project = models.ForeignKey(
        'Project', on_delete=models.CASCADE, related_name='project_property_views'
    )
    compliant = models.NullBooleanField(null=True, )
    approved_date = models.DateField(
        _("approved_date"), null=True, blank=True
    )
    approver = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name=_('User'), blank=True, null=True
    )

    class Meta:
        ordering = ['project', 'property_view']
        unique_together = ('property_view', 'project')
        verbose_name = _("project property view")
        verbose_name_plural = _("project property views")

    def __str__(self):
        return u"{0} - {1}".format(self.property_view, self.project.name)


class ProjectTaxLotView(TimeStampedModel):
    taxlot_view = models.ForeignKey(
        'TaxLotView', on_delete=models.CASCADE, related_name='project_taxlot_views'
    )
    project = models.ForeignKey(
        'Project', on_delete=models.CASCADE, related_name='project_taxlot_views'
    )
    compliant = models.NullBooleanField(null=True, )
    approved_date = models.DateField(
        _("approved_date"), null=True, blank=True
    )
    approver = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name=_('User'), blank=True, null=True
    )

    class Meta:
        ordering = ['project', 'taxlot_view']
        unique_together = ('taxlot_view', 'project')
        verbose_name = _('project taxlot view')
        verbose_name_plural = _('project taxlot views')

    def __str__(self):
        return '{0} - {1}'.format(self.taxlot_view, self.project.name)

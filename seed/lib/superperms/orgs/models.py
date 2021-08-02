# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models.signals import pre_delete

from seed.lib.superperms.orgs.exceptions import TooManyNestedOrgs

_log = logging.getLogger(__name__)

USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', User)

# Role Levels
ROLE_VIEWER = 0
ROLE_MEMBER = 10
ROLE_OWNER = 20

ROLE_LEVEL_CHOICES = (
    (ROLE_VIEWER, 'Viewer'),
    (ROLE_MEMBER, 'Member'),
    (ROLE_OWNER, 'Owner'),
)

# Invite status
STATUS_PENDING = 'pending'
STATUS_ACCEPTED = 'accepted'
STATUS_REJECTED = 'rejected'

STATUS_CHOICES = (
    (STATUS_PENDING, 'Pending'),
    (STATUS_ACCEPTED, 'Accepted'),
    (STATUS_REJECTED, 'Rejected'),
)


# This should be cleaned/DRYed up with Organization._default_display_meter_units
def _get_default_display_meter_units():
    return {
        'Coal (anthracite)': 'kBtu (thousand Btu)',
        'Coal (bituminous)': 'kBtu (thousand Btu)',
        'Coke': 'kBtu (thousand Btu)',
        'Diesel': 'kBtu (thousand Btu)',
        'District Chilled Water - Absorption': 'kBtu (thousand Btu)',
        'District Chilled Water - Electric': 'kBtu (thousand Btu)',
        'District Chilled Water - Engine': 'kBtu (thousand Btu)',
        'District Chilled Water - Other': 'kBtu (thousand Btu)',
        'District Hot Water': 'kBtu (thousand Btu)',
        'District Steam': 'kBtu (thousand Btu)',
        'Electric - Grid': 'kWh (thousand Watt-hours)',
        'Electric - Solar': 'kWh (thousand Watt-hours)',
        'Electric - Wind': 'kWh (thousand Watt-hours)',
        'Electric - Unknown': 'kWh (thousand Watt-hours)',
        'Fuel Oil (No. 1)': 'kBtu (thousand Btu)',
        'Fuel Oil (No. 2)': 'kBtu (thousand Btu)',
        'Fuel Oil (No. 4)': 'kBtu (thousand Btu)',
        'Fuel Oil (No. 5 and No. 6)': 'kBtu (thousand Btu)',
        'Kerosene': 'kBtu (thousand Btu)',
        'Natural Gas': 'kBtu (thousand Btu)',
        'Other:': 'kBtu (thousand Btu)',
        'Propane': 'kBtu (thousand Btu)',
        'Wood': 'kBtu (thousand Btu)'
    }


class OrganizationUser(models.Model):
    class Meta:
        ordering = ['organization', '-role_level']

    user = models.ForeignKey(USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE)
    status = models.CharField(
        max_length=12, default=STATUS_PENDING, choices=STATUS_CHOICES
    )
    role_level = models.IntegerField(
        default=ROLE_OWNER, choices=ROLE_LEVEL_CHOICES
    )

    def delete(self, *args, **kwargs):
        """Ensure we preserve at least one Owner for this org."""
        # If we're removing an owner
        if self.role_level == ROLE_OWNER:
            # If there are users, but no other owners in this organization.
            all_org_users = OrganizationUser.objects.filter(
                organization=self.organization,
            ).exclude(pk=self.pk)
            if (all_org_users.exists() and all_org_users.filter(
                    role_level=ROLE_OWNER).count() == 0):
                # Make next most high ranking person the owner.
                other_user = all_org_users.order_by('-role_level', '-pk')[0]
                if other_user.role_level > ROLE_VIEWER:
                    other_user.role_level = ROLE_OWNER
                    other_user.save()
                else:
                    raise UserWarning('Did not find suitable user to promote')
        super().delete(*args, **kwargs)

    def __str__(self):
        return 'OrganizationUser: {0} <{1}> ({2})'.format(
            self.user.username, self.organization.name, self.pk
        )


class Organization(models.Model):
    """A group of people that optionally contains another sub group."""

    MEASUREMENT_CHOICES_AREA = (
        ('ft**2', 'square feet'),
        ('m**2', 'square metres'),
    )

    MEASUREMENT_CHOICES_EUI = (
        ('kBtu/ft**2/year', 'kBtu/sq. ft./year'),
        ('kWh/m**2/year', 'kWh/m²/year'),
        ('GJ/m**2/year', 'GJ/m²/year'),
        ('MJ/m**2/year', 'MJ/m²/year'),
        ('kBtu/m**2/year', 'kBtu/m²/year'),  # really, Toronto?
    )

    US = 1
    CAN = 2

    THERMAL_CONVERSION_ASSUMPTION_CHOICES = (
        (US, 'US'),
        (CAN, 'CAN'),
    )

    # This should be cleaned/DRYed up with the ._get_default_display_meter_units method
    _default_display_meter_units = {
        'Coal (anthracite)': 'kBtu (thousand Btu)',
        'Coal (bituminous)': 'kBtu (thousand Btu)',
        'Coke': 'kBtu (thousand Btu)',
        'Diesel': 'kBtu (thousand Btu)',
        'District Chilled Water - Absorption': 'kBtu (thousand Btu)',
        'District Chilled Water - Electric': 'kBtu (thousand Btu)',
        'District Chilled Water - Engine': 'kBtu (thousand Btu)',
        'District Chilled Water - Other': 'kBtu (thousand Btu)',
        'District Hot Water': 'kBtu (thousand Btu)',
        'District Steam': 'kBtu (thousand Btu)',
        'Electric - Grid': 'kWh (thousand Watt-hours)',
        'Electric - Solar': 'kWh (thousand Watt-hours)',
        'Electric - Wind': 'kWh (thousand Watt-hours)',
        'Electric - Unknown': 'kWh (thousand Watt-hours)',
        'Fuel Oil (No. 1)': 'kBtu (thousand Btu)',
        'Fuel Oil (No. 2)': 'kBtu (thousand Btu)',
        'Fuel Oil (No. 4)': 'kBtu (thousand Btu)',
        'Fuel Oil (No. 5 and No. 6)': 'kBtu (thousand Btu)',
        'Kerosene': 'kBtu (thousand Btu)',
        'Natural Gas': 'kBtu (thousand Btu)',
        'Other:': 'kBtu (thousand Btu)',
        'Propane': 'kBtu (thousand Btu)',
        'Wood': 'kBtu (thousand Btu)'
    }

    class Meta:
        ordering = ['name']

    name = models.CharField(max_length=100)
    users = models.ManyToManyField(
        USER_MODEL,
        through=OrganizationUser,
        related_name='orgs',
    )

    parent_org = models.ForeignKey('Organization', on_delete=models.CASCADE, blank=True, null=True, related_name='child_orgs')

    display_units_eui = models.CharField(max_length=32,
                                         choices=MEASUREMENT_CHOICES_EUI,
                                         blank=False,
                                         default='kBtu/ft**2/year')
    display_units_area = models.CharField(max_length=32,
                                          choices=MEASUREMENT_CHOICES_AREA,
                                          blank=False,
                                          default='ft**2')
    display_significant_figures = models.PositiveSmallIntegerField(blank=False, default=2)

    created = models.DateTimeField(auto_now_add=True, null=True)
    modified = models.DateTimeField(auto_now=True, null=True)

    # Default preferred all meter units to kBtu
    display_meter_units = JSONField(default=_get_default_display_meter_units)

    # If below this threshold, we don't show results from this Org
    # in exported views of its data.
    query_threshold = models.IntegerField(blank=True, null=True)

    # geolocation
    mapquest_api_key = models.CharField(blank=True, max_length=128, default='')
    geocoding_enabled = models.BooleanField(default=True)

    # new user email fields
    new_user_email_from = models.CharField(max_length=128, blank=False, default="info@seed-platform.org")
    new_user_email_subject = models.CharField(max_length=128, blank=False, default="New SEED account")
    new_user_email_content = models.CharField(max_length=1024, blank=False, default="Hello {{first_name}},\nYou are receiving this e-mail because you have been registered for a SEED account.\nSEED is easy, flexible, and cost effective software designed to help organizations clean, manage and share information about large portfolios of buildings. SEED is a free, open source web application that you can use privately.  While SEED was originally designed to help cities and States implement benchmarking programs for public or private buildings, it has the potential to be useful for many other activities by public entities, efficiency programs and private companies.\nPlease go to the following page and setup your account:\n{{sign_up_link}}")
    new_user_email_signature = models.CharField(max_length=128, blank=False, default="The SEED Team")

    # display settings
    property_display_field = models.CharField(max_length=32, blank=False, default="address_line_1")
    taxlot_display_field = models.CharField(max_length=32, blank=False, default="address_line_1")

    thermal_conversion_assumption = models.IntegerField(choices=THERMAL_CONVERSION_ASSUMPTION_CHOICES, default=US)

    comstock_enabled = models.BooleanField(default=False)

    # API Token for communicating with BETTER
    better_analysis_api_key = models.CharField(blank=True, max_length=128, default='')

    def save(self, *args, **kwargs):
        """Perform checks before saving."""
        # There can only be one.
        if self.parent_org is not None and self.parent_org.parent_org is not None:
            raise TooManyNestedOrgs

        super().save(*args, **kwargs)

        # Create a default cycle for the organization if there isn't one already
        from seed.models import Cycle
        Cycle.get_or_create_default(self)
        from seed.models import Measure
        Measure.populate_measures(self.id)

    def is_member(self, user):
        """Return True if user object has a relation to this organization."""
        return user in self.users.all()

    def add_member(self, user, role=ROLE_OWNER):
        """Add a user to an organization."""
        # Ensure that the user can login in case they had previously been deactivated due to no org associations
        user.is_active = True
        user.save()
        return OrganizationUser.objects.get_or_create(user=user, organization=self, role_level=role)

    def remove_member(self, user):
        """Remove user from organization."""
        try:
            user = OrganizationUser.objects.get(user=user, organization=self)
        except OrganizationUser.DoesNotExist:
            _log.info("Could not find user in organization")
            return None

        return user.delete()

    def is_owner(self, user):
        """
        Return True if the user has a relation to this org, with a role of
        owner.
        """
        return OrganizationUser.objects.filter(
            user=user, role_level=ROLE_OWNER, organization=self,
        ).exists()

    def get_exportable_fields(self):
        """Default to parent definition of exportable fields."""
        if self.parent_org:
            return self.parent_org.get_exportable_fields()
        return self.exportable_fields.all()

    def get_query_threshold(self):
        """Default to parent definition of query threshold."""
        if self.parent_org:
            return self.parent_org.get_query_threshold()
        return self.query_threshold

    @property
    def is_parent(self):
        return not self.parent_org

    def get_parent(self):
        """
        Returns the top-most org in this org's tree.
        That could be this org, or it could be this org's parent.
        """
        if self.is_parent:
            return self
        return self.parent_org

    @property
    def parent_id(self):
        """
        The id of the  top-most org in this org's tree.
        That could be this org, or it could be this org's parent.
        """
        if self.is_parent:
            return self.id
        return self.parent_org.id

    def __str__(self):
        return 'Organization: {0}({1})'.format(self.name, self.pk)


def organization_pre_delete(sender, instance, **kwargs):
    from seed.data_importer.models import ImportFile, ImportRecord

    # Use raw_objects here because objects can't access records where deleted=True.
    ImportFile.raw_objects.filter(import_record__super_organization_id=instance.pk).delete()
    ImportRecord.raw_objects.filter(super_organization_id=instance.pk).delete()


pre_delete.connect(organization_pre_delete, sender=Organization)

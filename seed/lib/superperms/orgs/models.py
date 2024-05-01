# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError, models, transaction
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from treebeard.ns_tree import NS_Node

from seed.lib.superperms.orgs.exceptions import TooManyNestedOrgsError

_log = logging.getLogger(__name__)

USER_MODEL = getattr(settings, "AUTH_USER_MODEL", User)

# Role Levels
ROLE_VIEWER = 0
ROLE_MEMBER = 10
ROLE_OWNER = 20

ROLE_LEVEL_CHOICES = (
    (ROLE_VIEWER, "Viewer"),
    (ROLE_MEMBER, "Member"),
    (ROLE_OWNER, "Owner"),
)

# Invite status
STATUS_PENDING = "pending"
STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"

STATUS_CHOICES = (
    (STATUS_PENDING, "Pending"),
    (STATUS_ACCEPTED, "Accepted"),
    (STATUS_REJECTED, "Rejected"),
)


def _get_default_meter_units():
    """Returns the default meter units for an organization. This method
    is used only to set the default units for a new organization.

    Do not use this method otherwise, simply call
    `Organization._default_display_meter_units` directly."""
    return Organization._default_display_meter_units


class OrganizationUser(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "organization"], name="unique_user_for_organization"),
        ]
        ordering = ["organization", "-role_level"]

    user = models.ForeignKey(USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey("Organization", on_delete=models.CASCADE)
    status = models.CharField(max_length=12, default=STATUS_PENDING, choices=STATUS_CHOICES)
    role_level = models.IntegerField(default=ROLE_OWNER, choices=ROLE_LEVEL_CHOICES)
    access_level_instance = models.ForeignKey("AccessLevelInstance", on_delete=models.CASCADE, null=False, related_name="users")

    def delete(self, *args, **kwargs):
        """Ensure we preserve at least one Owner for this org."""
        # If we're removing an owner
        if self.role_level == ROLE_OWNER:
            # If there are users, but no other owners in this organization.
            all_org_users = OrganizationUser.objects.filter(
                organization=self.organization,
            ).exclude(pk=self.pk)
            if all_org_users.exists() and all_org_users.filter(role_level=ROLE_OWNER).count() == 0:
                # Make next most high ranking person the owner.
                other_user = all_org_users.order_by("-role_level", "-pk")[0]
                if other_user.role_level > ROLE_VIEWER:
                    other_user.role_level = ROLE_OWNER
                    other_user.save()
                else:
                    raise UserWarning("Did not find suitable user to promote")
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"OrganizationUser: {self.user.username} <{self.organization.name}> ({self.pk})"


@receiver(pre_save, sender=OrganizationUser)
def presave_organization_user(sender, instance, **kwargs):
    if instance.role_level == ROLE_OWNER and instance.access_level_instance != instance.organization.root:
        raise IntegrityError("Owners must be member of the organization's root.")


class AccessLevelInstance(NS_Node):
    """Node in the Accountability Hierarchy tree"""

    name = models.CharField(max_length=100, null=False)
    organization = models.ForeignKey("Organization", on_delete=models.CASCADE)
    # path automatically maintained dict of ancestors names by access level names.
    # See get_path and set_path.
    path = models.JSONField(null=False)

    node_order_by = ["name"]

    # TODO: Add constraint that siblings cannot have same name.

    def get_path(self):
        """get a dictionary detailing the ancestors of this Access Level Instance"""
        level_names = self.organization.access_level_names
        ancestors = {level_names[depth - 1]: name for depth, name in self.get_ancestors().values_list("depth", "name")}
        ancestors[level_names[self.depth - 1]] = self.name

        return ancestors

    def __str__(self):
        access_level_name = self.organization.access_level_names[self.depth - 1]
        return f"{self.name}: {self.organization.name} Access Level {access_level_name}"


@receiver(pre_save, sender=AccessLevelInstance)
def set_path(sender, instance, **kwargs):
    # if instance is new, set path
    if instance.id is None:
        instance.path = instance.get_path()

    # else, if we updated the name...
    else:
        previous = AccessLevelInstance.objects.get(pk=instance.id)
        if instance.name != previous.name:
            level_name = instance.organization.access_level_names[instance.depth - 1]
            with transaction.atomic():
                # update our path
                instance.path[level_name] = instance.name
                # update our children's path
                for ali in instance.get_descendants():
                    ali.path[level_name] = instance.name
                    ali.save()


class Organization(models.Model):
    """A group of people that optionally contains another sub group."""

    MEASUREMENT_CHOICES_AREA = (
        ("ft**2", "square feet"),
        ("m**2", "square metres"),
    )

    MEASUREMENT_CHOICES_EUI = (
        ("kBtu/ft**2/year", "kBtu/sq. ft./year"),
        ("kWh/m**2/year", "kWh/m²/year"),
        ("GJ/m**2/year", "GJ/m²/year"),
        ("MJ/m**2/year", "MJ/m²/year"),
        ("kBtu/m**2/year", "kBtu/m²/year"),  # really, Toronto?
    )

    MEASUREMENT_CHOICES_GHG = (
        ("kgCO2e/year", "kgCO2e/year"),
        ("MtCO2e/year", "MtCO2e/year"),
    )

    MEASUREMENT_CHOICES_GHG_INTENSITY = (
        ("kgCO2e/ft**2/year", "kgCO2e/ft²/year"),
        ("MtCO2e/ft**2/year", "MtCO2e/ft²/year"),
        ("kgCO2e/m**2/year", "kgCO2e/m²/year"),
        ("MtCO2e/m**2/year", "MtCO2e/m²/year"),
    )

    US = 1
    CAN = 2

    THERMAL_CONVERSION_ASSUMPTION_CHOICES = (
        (US, "US"),
        (CAN, "CAN"),
    )

    _default_display_meter_units = {
        "Coal (anthracite)": "kBtu (thousand Btu)",
        "Coal (bituminous)": "kBtu (thousand Btu)",
        "Coke": "kBtu (thousand Btu)",
        "Default": "kBtu (thousand Btu)",
        "Diesel": "kBtu (thousand Btu)",
        "District Chilled Water": "kBtu (thousand Btu)",
        "District Chilled Water - Absorption": "kBtu (thousand Btu)",
        "District Chilled Water - Electric": "kBtu (thousand Btu)",
        "District Chilled Water - Engine": "kBtu (thousand Btu)",
        "District Chilled Water - Other": "kBtu (thousand Btu)",
        "District Hot Water": "kBtu (thousand Btu)",
        "District Steam": "kBtu (thousand Btu)",
        "Electric": "kWh (thousand Watt-hours)",
        "Electric - Grid": "kWh (thousand Watt-hours)",
        "Electric - Solar": "kWh (thousand Watt-hours)",
        "Electric - Wind": "kWh (thousand Watt-hours)",
        "Electric - Unknown": "kWh (thousand Watt-hours)",
        "Fuel Oil (No. 1)": "kBtu (thousand Btu)",
        "Fuel Oil (No. 2)": "kBtu (thousand Btu)",
        "Fuel Oil (No. 4)": "kBtu (thousand Btu)",
        "Fuel Oil (No. 5 and No. 6)": "kBtu (thousand Btu)",
        "Kerosene": "kBtu (thousand Btu)",
        "Natural Gas": "kBtu (thousand Btu)",
        "Other:": "kBtu (thousand Btu)",  # yes, other has a colon at the end.
        "Propane": "kBtu (thousand Btu)",
        "Wood": "kBtu (thousand Btu)",
    }

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                name="ubid_threshold_range",
                check=models.Q(ubid_threshold__range=(0, 1)),
            ),
        ]

    name = models.CharField(max_length=100)
    users = models.ManyToManyField(
        USER_MODEL,
        through=OrganizationUser,
        related_name="orgs",
    )

    parent_org = models.ForeignKey("Organization", on_delete=models.CASCADE, blank=True, null=True, related_name="child_orgs")

    display_units_eui = models.CharField(max_length=32, choices=MEASUREMENT_CHOICES_EUI, blank=False, default="kBtu/ft**2/year")
    display_units_area = models.CharField(max_length=32, choices=MEASUREMENT_CHOICES_AREA, blank=False, default="ft**2")
    display_units_ghg = models.CharField(max_length=32, choices=MEASUREMENT_CHOICES_GHG, blank=False, default="MtCO2e/year")
    display_units_ghg_intensity = models.CharField(
        max_length=32, choices=MEASUREMENT_CHOICES_GHG_INTENSITY, blank=False, default="kgCO2e/ft**2/year"
    )
    display_decimal_places = models.PositiveSmallIntegerField(blank=False, default=2)

    created = models.DateTimeField(auto_now_add=True, null=True)
    modified = models.DateTimeField(auto_now=True, null=True)

    # Default preferred all meter units to kBtu
    display_meter_units = models.JSONField(default=_get_default_meter_units)

    # If below this threshold, we don't show results from this Org
    # in exported views of its data.
    query_threshold = models.IntegerField(blank=True, null=True)

    # geolocation
    mapquest_api_key = models.CharField(blank=True, max_length=128, default="")
    geocoding_enabled = models.BooleanField(default=True)

    # new user email fields
    new_user_email_from = models.CharField(max_length=128, blank=False, default="info@seed-platform.org")
    new_user_email_subject = models.CharField(max_length=128, blank=False, default="New SEED account")
    new_user_email_content = models.CharField(
        max_length=1024,
        blank=False,
        default="Hello {{first_name}},\nYou are receiving this e-mail because you have been registered for a SEED account.\nSEED is easy, flexible, and cost effective software designed to help organizations clean, manage and share information about large portfolios of buildings. SEED is a free, open source web application that you can use privately.  While SEED was originally designed to help cities and States implement benchmarking programs for public or private buildings, it has the potential to be useful for many other activities by public entities, efficiency programs and private companies.\nPlease go to the following page and setup your account:\n{{sign_up_link}}",
    )
    new_user_email_signature = models.CharField(max_length=128, blank=False, default="The SEED Team")

    # display settings
    property_display_field = models.CharField(max_length=32, blank=False, default="address_line_1")
    taxlot_display_field = models.CharField(max_length=32, blank=False, default="address_line_1")

    thermal_conversion_assumption = models.IntegerField(choices=THERMAL_CONVERSION_ASSUMPTION_CHOICES, default=US)

    comstock_enabled = models.BooleanField(default=False)

    # API Tokens
    better_analysis_api_key = models.CharField(blank=True, max_length=128, default="")
    at_organization_token = models.CharField(blank=True, max_length=128, default="")
    audit_template_user = models.EmailField(blank=True, max_length=128, default="")
    audit_template_password = models.CharField(blank=True, max_length=128, default="")
    audit_template_report_type = models.CharField(blank=True, max_length=128, default="Demo City Report")

    # Salesforce Functionality
    salesforce_enabled = models.BooleanField(default=False)

    access_level_names = models.JSONField(default=list)

    # UBID Threshold
    ubid_threshold = models.FloatField(default=1.0)

    def save(self, *args, **kwargs):
        """Perform checks before saving."""
        # There can only be one.
        if self.parent_org is not None and self.parent_org.parent_org is not None:
            raise TooManyNestedOrgsError

        super().save(*args, **kwargs)

        # Create a default cycle for the organization if there isn't one already
        from seed.models import Cycle

        Cycle.get_or_create_default(self)
        from seed.models import Measure

        Measure.populate_measures(self.id)

    def is_member(self, user):
        """Return True if user object has a relation to this organization."""
        return user in self.users.all()

    def add_member(self, user, access_level_instance_id, role=ROLE_OWNER):
        """Add a user to an organization. Returns a boolean if a new OrganizationUser record was created"""
        if OrganizationUser.objects.filter(user=user, organization=self).exists():
            return False

        # Ensure that the user can login in case they had previously been deactivated due to no org associations
        if not user.is_active:
            user.is_active = True
            user.save()

        _, created = OrganizationUser.objects.get_or_create(
            user=user, organization=self, access_level_instance_id=access_level_instance_id, role_level=role
        )

        return created

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
            user=user,
            role_level=ROLE_OWNER,
            organization=self,
        ).exists()

    def has_role_member(self, user):
        """
        Return True if the user has a relation to this org, with a role of
        member.
        """
        return OrganizationUser.objects.filter(
            user=user,
            role_level=ROLE_MEMBER,
            organization=self,
        ).exists()

    def is_user_ali_root(self, user):
        """
        Return True if the user's ali is at the root of the organization
        """
        is_root = False

        ou = OrganizationUser.objects.filter(
            user=user,
            organization=self,
        )
        if ou.count() > 0:
            ou = ou.first()
            if ou.access_level_instance == self.root:
                is_root = True
        return is_root

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

    def add_new_access_level_instance(self, parent_id: int, name: str) -> AccessLevelInstance:
        parent = AccessLevelInstance.objects.get(pk=parent_id)

        if len(self.access_level_names) < parent.depth + 1:
            raise UserWarning("Cannot create child at an unnamed level")

        new_access_level_instance = parent.add_child(organization=self, name=name)

        return new_access_level_instance

    def get_access_tree(self, from_ali=None) -> list:
        if from_ali is None:
            from_ali = self.root

        alis_ordered_by_lft = list(
            AccessLevelInstance.objects.filter(organization=from_ali.organization, lft__gte=from_ali.lft, rgt__lte=from_ali.rgt)
            .order_by("-lft")
            .values("id", "name", "organization", "path", "lft", "rgt")
        )

        def populate_children(curr):
            curr["children"] = []
            lft, rgt = curr["lft"], curr["rgt"]
            del curr["lft"]
            del curr["rgt"]

            while len(alis_ordered_by_lft) > 0:
                nxt = alis_ordered_by_lft[-1]
                if lft < nxt["lft"] and rgt > nxt["rgt"]:  # is descendant
                    child = alis_ordered_by_lft.pop()
                    curr["children"].append(child)
                    populate_children(nxt)
                else:
                    break

            if curr["children"] == []:
                del curr["children"]

        root = alis_ordered_by_lft.pop()
        populate_children(root)

        return [root]

    def __str__(self):
        return f"Organization: {self.name}({self.pk})"

    @property
    def root(self):
        return AccessLevelInstance.objects.get(organization=self, depth=1)


def organization_pre_delete(sender, instance, **kwargs):
    from seed.data_importer.models import ImportFile, ImportRecord

    # Use raw_objects here because objects can't access records where deleted=True.
    ImportFile.raw_objects.filter(import_record__super_organization_id=instance.pk).delete()
    ImportRecord.raw_objects.filter(super_organization_id=instance.pk).delete()


pre_delete.connect(organization_pre_delete, sender=Organization)


@receiver(pre_save, sender=Organization)
def presave_organization(sender, instance, **kwargs):
    from seed.models import Column

    if instance.id is None:
        return

    previous = Organization.objects.get(pk=instance.id)
    previous_access_level_names = previous.access_level_names

    if previous_access_level_names != instance.access_level_names:
        _assert_alns_are_valid(instance)
        _update_alis_path_keys(instance, previous_access_level_names)

    taken_names = Column.objects.filter(organization=instance, display_name__in=instance.access_level_names).values_list(
        "display_name", flat=True
    )
    if len(taken_names) > 0:
        raise ValueError(f"{taken_names} are column names.")


def _assert_alns_are_valid(org):
    from seed.models import Column

    alns = org.access_level_names

    if len(set(alns)) != len(alns):  # if not unique
        raise ValueError("Organization's access_level_names must be unique.")

    columns_with_same_names = Column.objects.filter(organization=org, display_name__in=alns)
    if columns_with_same_names.count() > 0:
        repeated_names = set(columns_with_same_names.values_list("display_name", flat=True))
        raise ValueError(f"Access level names cannot match SEED column names: {list(repeated_names)}")


def _update_alis_path_keys(org, previous_access_level_names):
    """For each instance.access_level_names item changed, update the ali.paths"""
    alis = AccessLevelInstance.objects.filter(organization=org)
    min_len = min(len(previous_access_level_names), len(org.access_level_names))

    with transaction.atomic():
        # for each name in access_level_name...
        for i in range(min_len):
            previous_access_level_name = previous_access_level_names[i]
            current_access_level_name = org.access_level_names[i]

            # If the name was changed, alter the paths of the ALIs.
            if previous_access_level_name != current_access_level_name:
                for ali in alis:
                    if previous_access_level_name in ali.path:
                        ali.path[current_access_level_name] = ali.path[previous_access_level_name]
                        del ali.path[previous_access_level_name]
                        ali.save()


@receiver(post_save, sender=Organization)
def post_save_organization(sender, instance, created, **kwargs):
    """
    Give new Orgs a Accountability Hierarchy root.
    """
    if created:
        if not instance.access_level_names:
            instance.access_level_names = [instance.name]

        root = AccessLevelInstance.add_root(organization=instance, name="root")
        root.save()
        instance.save()

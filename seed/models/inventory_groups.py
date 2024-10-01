from django.db import IntegrityError, models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from seed.lib.superperms.orgs.models import AccessLevelInstance, Organization
from seed.models.properties import Property
from seed.models.tax_lots import TaxLot

VIEW_LIST_PROPERTY = 0
VIEW_LIST_TAXLOT = 1
VIEW_LIST_INVENTORY_TYPE = [
    (VIEW_LIST_PROPERTY, "Property"),
    (VIEW_LIST_TAXLOT, "Tax Lot"),
]


class InventoryGroup(models.Model):
    name = models.CharField(max_length=255)
    inventory_type = models.IntegerField(choices=VIEW_LIST_INVENTORY_TYPE, default=VIEW_LIST_PROPERTY)
    access_level_instance = models.ForeignKey(AccessLevelInstance, on_delete=models.CASCADE, null=False, related_name="groups")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=False, related_name="groups")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "organization"], name="unique_group_name_for_organization"),
        ]


@receiver(pre_save, sender=InventoryGroup)
def presave_inventory_group(sender, instance, **kwargs):
    if instance.access_level_instance.organization != instance.organization:
        raise IntegrityError("access_level_instance must be in organization")


class InventoryGroupMapping(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, blank=True, null=True, related_name="group_mappings")
    taxlot = models.ForeignKey(TaxLot, on_delete=models.CASCADE, blank=True, null=True, related_name="group_mappings")
    group = models.ForeignKey(InventoryGroup, on_delete=models.CASCADE, related_name="group_mappings")

    def clean(self):
        inventory = self.property or self.taxlot

        for i in inventory:
            if i.access_level_instance != self.group.access_level_instance:
                raise IntegrityError("Access Level mismatch between group and inventory.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


@receiver(pre_save, sender=InventoryGroupMapping)
def presave_inventory_group_mapping(sender, instance, **kwargs):
    property = instance.property
    taxlot = instance.taxlot
    group = instance.group

    # must be xor property/taxlot
    if property and taxlot:
        raise IntegrityError("instance of InventoryGroupMapping has both property and taxlot")
    if not property and not taxlot:
        raise IntegrityError("instance of InventoryGroupMapping has neither property nor taxlot")

    # must be right type of group
    if property and group.inventory_type == VIEW_LIST_TAXLOT:
        raise IntegrityError(f"Property {property} in TaxLot Group")
    if taxlot and group.inventory_type == VIEW_LIST_PROPERTY:
        raise IntegrityError(f"Taxlot {property} in Property Group")

    # must be in group ali
    inventory_item = property or taxlot
    if not (
        group.access_level_instance == inventory_item.access_level_instance
        or inventory_item.access_level_instance.is_descendant_of(group.access_level_instance)
    ):
        raise IntegrityError("Group does not have access to this property/taxlot")

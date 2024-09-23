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

    def lowest_common_ancestor(self):
        """
        Find the least common ancestor between multiple properties within a group

        Example ALI tree:
             A
           /   \
          B     C
         /\
        D  E
        
        least common ancestor:
        if A and D -> A
        if B and C -> A
        if B and D -> B
        if D and E -> B
        """
        lookup = {0: ('property', Property), 1: ('taxlot', TaxLot)}
        inventory_type, InventoryClass = lookup.get(self.inventory_type, ('property', Property))
        mappings = self.inventorygroupmapping_set.all()
        inventory = InventoryClass.objects.filter(id__in=mappings.values_list(inventory_type, flat=True))
        alis = [i.access_level_instance for i in list(inventory)]

        # generate a list of property ancestor lists
        ancestor_lists = [
            list(instance.get_ancestors()) + [instance] for instance in alis
        ]

        base_ancestors = min(ancestor_lists, key=len)
        lowest_common = None
        # starting with lowest node, determine if the node exists in all other ancestor lists. If it does, return the node.
        for base in reversed(base_ancestors):
            in_all = all(base in sublist for sublist in ancestor_lists)
            if in_all:
                lowest_common = base 
                break
            
        return lowest_common


@receiver(pre_save, sender=InventoryGroup)
def presave_inventory_group(sender, instance, **kwargs):
    

    if instance.access_level_instance.organization != instance.organization:
        raise IntegrityError("access_level_instance must be in organization")


class InventoryGroupMapping(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, blank=True, null=True, related_name="group_mappings")
    taxlot = models.ForeignKey(TaxLot, on_delete=models.CASCADE, blank=True, null=True, related_name="group_mappings")
    group = models.ForeignKey(InventoryGroup, on_delete=models.CASCADE)


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

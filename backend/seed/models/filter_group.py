"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Exists, OuterRef

from seed.lib.superperms.orgs.models import Organization
from seed.models.column_list_profiles import VIEW_LIST_INVENTORY_TYPE, VIEW_LIST_PROPERTY, VIEW_LIST_TAXLOT
from seed.models.columns import Column
from seed.models.models import StatusLabel
from seed.models.properties import PropertyView
from seed.models.tax_lots import TaxLotView
from seed.utils.search import FilterError


class FilterGroup(models.Model):
    name = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="filter_groups", null=False)
    inventory_type = models.IntegerField(choices=VIEW_LIST_INVENTORY_TYPE, default=VIEW_LIST_PROPERTY)
    query_dict = models.JSONField(null=False, default=dict)
    and_labels = models.ManyToManyField(StatusLabel, related_name="and_filter_groups")
    or_labels = models.ManyToManyField(StatusLabel, related_name="or_filter_groups")
    exclude_labels = models.ManyToManyField(StatusLabel, related_name="exclude_filter_groups")

    def views(self, views=None):
        """
        The given property or tax lot views (by default, all the organization's views of the filter group's inventory type)
        that match the filter group's filters and labels. Views of the other inventory type match when a related view does
        (e.g., the properties of a tax lot filter group's tax lots, in a property report). Raises FilterError for invalid filters.
        """
        inventory_type, other_type = ("taxlot", "property") if self.inventory_type == VIEW_LIST_TAXLOT else ("property", "taxlot")
        ViewClass = TaxLotView if inventory_type == "taxlot" else PropertyView
        # Only default to all the organization's views when none are given; an empty (e.g., access level scoped) queryset stays empty
        if views is None:
            views = ViewClass.objects.select_related(inventory_type, "state").filter(
                **{f"{inventory_type}__organization_id": self.organization_id}
            )
        elif views.model is not ViewClass:
            return views.filter(Exists(self.views().filter(**{f"taxlotproperty__{other_type}_view": OuterRef("pk")})))

        matches = self._filter(views, inventory_type) if self.query_dict else views

        and_labels = self.and_labels.all()
        or_labels = self.or_labels.all()
        exclude_labels = self.exclude_labels.all()

        for label in and_labels:
            matches = matches.filter(labels=label)
        if or_labels.exists():  # or
            matches = matches.filter(labels__in=or_labels)
        if exclude_labels.exists():  # exclude
            matches = matches.exclude(labels__in=exclude_labels)

        # A view can match more than one OR label or related record, so select each matching view once
        return views.filter(pk__in=matches.values("pk"))

    def _filter(self, views, inventory_type):
        """
        Filter views by `query_dict`, which can mix the inventory grid's AG Grid filter models (dict values keyed by
        `{column_name}_{id}` or access level name) and legacy filters (`{column_name}_{id}__{lookup}` keys)
        """
        # Imported here, as it imports seed.models
        from seed.utils.v4.inventory_filter import InventoryFilter

        if not isinstance(self.query_dict, dict):
            raise FilterError("Invalid filter group filters")

        # Retrieve all columns for the org so the filter query can reference any column,
        # regardless of which data columns were passed in for compliance evaluation.
        columns = Column.retrieve_all(org_id=self.organization_id, inventory_type=inventory_type, only_used=False, include_related=True)
        access_level_names = self.organization.access_level_names

        filters, annotations = InventoryFilter.filters_to_q(self.query_dict, columns, inventory_type, access_level_names, self.organization)

        try:
            return views.annotate(**annotations).filter(filters)
        except (ValueError, ValidationError) as e:
            # e.g., text filter values on number or date columns
            raise FilterError(f"Error filtering - your data might not match the column settings data type: {e!s}") from e

    class Meta:
        ordering = ["id"]
        unique_together = ("name", "organization")

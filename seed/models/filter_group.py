"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db import models
from django.http import QueryDict

from seed.lib.superperms.orgs.models import Organization
from seed.models.column_list_profiles import VIEW_LIST_INVENTORY_TYPE, VIEW_LIST_PROPERTY
from seed.models.columns import Column
from seed.models.models import StatusLabel
from seed.models.properties import PropertyView
from seed.models.tax_lots import TaxLotView
from seed.utils.search import build_view_filters_and_sorts


class FilterGroup(models.Model):
    name = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="filter_groups", null=False)
    inventory_type = models.IntegerField(choices=VIEW_LIST_INVENTORY_TYPE, default=VIEW_LIST_PROPERTY)
    query_dict = models.JSONField(null=False, default=dict)
    and_labels = models.ManyToManyField(StatusLabel, related_name="and_filter_groups")
    or_labels = models.ManyToManyField(StatusLabel, related_name="or_filter_groups")
    exclude_labels = models.ManyToManyField(StatusLabel, related_name="exclude_filter_groups")

    def views(self, views, columns=[]):
        if VIEW_LIST_INVENTORY_TYPE[self.inventory_type][1] == "Property":
            return self._filtered_property_views(views, columns)
        elif VIEW_LIST_INVENTORY_TYPE[self.inventory_type][1] == "Tax Lot":
            return self._filtered_taxlot_views(views, columns)

    def _filtered_taxlot_views(self, views, columns=[]):
        if not views:
            views = TaxLotView.objects.select_related("taxlot", "state").filter(taxlot__organization_id=self.organization_id)
        if not columns:
            columns = Column.retrieve_all(org_id=self.organization_id, inventory_type="taxlot", only_used=False, include_related=False)

        if self.query_dict:
            qd = QueryDict(mutable=True)
            qd.update(self.query_dict)

            filters, _annotations, _order_by = build_view_filters_and_sorts(qd, columns, "taxlot")
            filtered_views = views.filter(filters)
        else:
            filtered_views = views

        return self._filter_with_labels(filtered_views)

    def _filtered_property_views(self, views, columns=[]):
        if not views:
            views = PropertyView.objects.select_related("property", "state").filter(property__organization_id=self.organization_id)
        if not columns:
            columns = Column.retrieve_all(org_id=self.organization_id, inventory_type="property", only_used=False, include_related=False)

        if self.query_dict:
            qd = QueryDict(mutable=True)
            qd.update(self.query_dict)

            filters, _annotations, _order_by = build_view_filters_and_sorts(qd, columns, "property")
            filtered_views = views.filter(filters)
        else:
            filtered_views = views

        return self._filter_with_labels(filtered_views)

    def _filter_with_labels(self, filtered_views):
        and_labels = self.and_labels.all()
        or_labels = self.or_labels.all()
        exclude_labels = self.exclude_labels.all()

        for label in and_labels:
            filtered_views = filtered_views.filter(labels=label)
        if or_labels.exists():  # or
            filtered_views = filtered_views.filter(labels__in=or_labels)
        if exclude_labels.exists():  # exclude
            filtered_views = filtered_views.exclude(labels__in=exclude_labels)

        return filtered_views

    class Meta:
        ordering = ["id"]
        unique_together = ("name", "organization")

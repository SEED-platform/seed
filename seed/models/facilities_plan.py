"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import BooleanField, Case, F, FloatField, Sum, Value, When
from django.db.models.functions import Cast
from django.utils import timezone as tz

from seed.lib.superperms.orgs.models import AccessLevelInstance, Organization
from seed.models import Column, Cycle, PropertyView

logger = logging.getLogger(__name__)


class FacilitiesPlan(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    energy_running_sum_percentage = models.FloatField(default=0.75, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    compliance_cycle_year_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    include_in_total_denominator_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    exclude_from_plan_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    require_in_plan_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")

    electric_energy_usage_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    gas_energy_usage_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    steam_energy_usage_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_name_for_plan"),
        ]


def _get_column_or_zero(column):
    c = _get_column_model_field(column)

    return Case(
        # regex to see if field is present and numeric
        When(**{f"{c}__regex": r"^\d+(\.\d+)?$"}, then=Cast(F(c), FloatField())),
        default=Value(0.0),
        output_field=FloatField(),
    )


def _get_column_model_field(column):
    if column.is_extra_data:
        return "state__extra_data__" + column.column_name
    elif column.derived_column:
        return "state__derived_data__" + column.column_name
    else:
        return "state__" + column.column_name


class FacilitiesPlanRun(models.Model):
    facilities_plan = models.ForeignKey(FacilitiesPlan, on_delete=models.CASCADE, related_name="runs")
    cycle = models.ForeignKey(Cycle, on_delete=models.SET_NULL, null=True)
    ali = models.ForeignKey(AccessLevelInstance, on_delete=models.SET_NULL, null=True)
    run_at = models.DateTimeField(auto_now=False, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    display_columns = models.ManyToManyField(Column)

    def _calculate_properties_percentage_of_total_energy_usage(self, ali: AccessLevelInstance, cycle: Cycle):
        # check that we have all the required columns
        required_columns = [
            "electric_energy_usage_column",
            "gas_energy_usage_column",
            "steam_energy_usage_column",
            "include_in_total_denominator_column",
            "require_in_plan_column",
            "exclude_from_plan_column",
        ]
        missing_columns = [c for c in required_columns if getattr(self.facilities_plan, c) is None]
        if missing_columns:
            raise ValueError(f"`calculate_properties_selected_by_plan` requires the following null columns: {missing_columns}")

        # get relevant properties
        properties = PropertyView.objects.filter(
            property__access_level_instance__lft__gte=ali.lft, property__access_level_instance__rgt__lte=ali.rgt, cycle=cycle
        ).exclude(**{_get_column_model_field(self.facilities_plan.include_in_total_denominator_column): False})

        # calculate properties total energy usage
        properties = properties.annotate(
            total_energy_usage=_get_column_or_zero(self.facilities_plan.electric_energy_usage_column)
            + _get_column_or_zero(self.facilities_plan.gas_energy_usage_column)
            + _get_column_or_zero(self.facilities_plan.steam_energy_usage_column)
        )

        # calculate properties percentage of total energy usage
        denominator = properties.aggregate(Sum("total_energy_usage"))["total_energy_usage__sum"]
        properties = properties.annotate(
            percentage_of_total_energy_usage=Cast(F("total_energy_usage"), FloatField()) / denominator,
        )

        # calculate required_in_plan (We're weeding out the nones, which mess up ordering later)
        properties = properties.annotate(
            required_in_plan=Case(
                When(**{_get_column_model_field(self.facilities_plan.require_in_plan_column): True}, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )
        properties = properties.annotate(
            exclude_from_plan_column=Case(
                When(**{_get_column_model_field(self.facilities_plan.exclude_from_plan_column): True}, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )

        return properties

    def run(self):
        FacilitiesPlanRunProperty.objects.filter(run=self).all().delete()
        self.run_at = tz.now()
        self.save()

        all_properties = self._calculate_properties_percentage_of_total_energy_usage(self.ali, self.cycle).order_by(
            "exclude_from_plan_column", "-required_in_plan", "-percentage_of_total_energy_usage"
        )
        energy_running_sum_percentage = 0

        for rank, p in enumerate(all_properties):
            energy_running_sum_percentage += p.percentage_of_total_energy_usage

            FacilitiesPlanRunProperty.objects.create(
                run=self,
                view=p,
                total_energy_usage=p.total_energy_usage,
                percentage_of_total_energy_usage=p.percentage_of_total_energy_usage,
                rank=rank,
                running_percentage=energy_running_sum_percentage,
                running_square_footage=0,
            )


class FacilitiesPlanRunProperty(models.Model):
    run = models.ForeignKey(FacilitiesPlanRun, on_delete=models.SET_NULL, null=True, related_name="property_rankings")
    view = models.ForeignKey(PropertyView, on_delete=models.SET_NULL, null=True, related_name="facility_plan_runs")

    total_energy_usage = models.FloatField()
    percentage_of_total_energy_usage = models.FloatField()
    rank = models.IntegerField()
    running_percentage = models.FloatField()
    running_square_footage = models.FloatField()

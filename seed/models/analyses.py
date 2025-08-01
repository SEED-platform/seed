"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.db import models

from seed.analysis_pipelines.utils import get_json_path
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import AccessLevelInstance, Organization

logger = logging.getLogger(__name__)


class Analysis(models.Model):
    """
    The Analysis represents an analysis performed on one or more properties.
    """

    BSYNCR = 1
    BETTER = 2
    EUI = 3
    CO2 = 4
    EEEJ = 5
    ELEMENTSTATISTICS = 6
    UPGRADERECOMMENDATION = 7
    CUSTOM_ANALYSIS = 100
    ADD_HELLO_COLUMN = 101
    GEOPANDAS_TEST = 102
    BUILDINGS_ANALYSIS = 103

    SERVICE_TYPES = (
        (BSYNCR, "BSyncr"),
        (BETTER, "BETTER"),
        (EUI, "EUI"),
        (CO2, "CO2"),
        (EEEJ, "EEEJ"),
        (ELEMENTSTATISTICS, "Element Statistics"),
        (UPGRADERECOMMENDATION, "Building Upgrade Recommendation"),
        (CUSTOM_ANALYSIS, "Custom Analysis"),
        (ADD_HELLO_COLUMN, "Add Hello Column"),
        (GEOPANDAS_TEST, "Geopandas Test"),
        (BUILDINGS_ANALYSIS, "Buildings Analysis"),
    )

    PENDING_CREATION = 8
    CREATING = 10
    READY = 20
    QUEUED = 30
    RUNNING = 40
    FAILED = 50
    STOPPED = 60
    COMPLETED = 70

    STATUS_TYPES = (
        (PENDING_CREATION, "Pending Creation"),
        (CREATING, "Creating"),
        (READY, "Ready"),
        (QUEUED, "Queued"),
        (RUNNING, "Running"),
        (FAILED, "Failed"),
        (STOPPED, "Stopped"),
        (COMPLETED, "Completed"),
    )

    name = models.CharField(max_length=255, blank=False, default=None)
    service = models.IntegerField(choices=SERVICE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(default=PENDING_CREATION, choices=STATUS_TYPES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    access_level_instance = models.ForeignKey(
        AccessLevelInstance, on_delete=models.CASCADE, null=False, related_name="analyses", blank=False
    )
    configuration = models.JSONField(default=dict, blank=True)
    # parsed_results can contain any results gathered from the resulting file(s)
    # that are applicable to the entire analysis (i.e., all properties involved).
    # For property-specific results, use the AnalysisPropertyView's parsed_results
    parsed_results = models.JSONField(default=dict, blank=True)

    def get_property_view_info(self, property_id=None):
        if property_id is not None:
            analysis_property_views = self.analysispropertyview_set.filter(property=property_id)
        else:
            analysis_property_views = self.analysispropertyview_set

        return {
            "number_of_analysis_property_views": self.analysispropertyview_set.count(),
            "views": list(analysis_property_views.values_list("id", flat=True).distinct()),
            "cycles": list(analysis_property_views.values_list("cycle", flat=True).distinct()),
        }

    def get_highlights(self, property_id=None):
        """Get analysis highlights for the overall analysis or for a specific property

        :param property_id: int | None, if provided property-specific highlights
            from the analysis results are returned. Otherwise highlights from the
            overall analysis are returned.
        :return: list[dict{}], a list of highlights as dictionaries, each including
            a `name` and `value`
        """
        if self.status < self.COMPLETED:
            return []

        results = {}
        if property_id is not None:
            try:
                results = self.analysispropertyview_set.get(property=property_id).parsed_results
            except models.Model.DoesNotExist:
                return []
        else:
            results = self.parsed_results

        # BSyncr
        if self.service == self.BSYNCR:
            return [{"name": "Completed", "value": ""}]
        # EEEJ
        elif self.service == self.EEEJ:
            tract = results.get("2010 Census Tract")
            tract = "N/A" if tract is None else tract

            dac = results.get("DAC")
            dac = "N/A" if dac is None else dac

            low_income = results.get("Low Income")
            low_income = "N/A" if low_income is None else low_income
            return [{"name": "Census Tract", "value": tract}, {"name": "DAC", "value": dac}, {"name": "Low Income?", "value": low_income}]

        # BETTER
        elif self.service == self.BETTER:
            highlights = [
                {
                    "name": ["Potential Cost Savings (USD)"],
                    "value_template": ["${json_value:,.2f}"],
                    "json_path": ["assessment.assessment_results.assessment_energy_use.cost_savings_combined"],
                },
                {
                    "name": ["Potential Energy Savings"],
                    "value_template": ["{json_value:,.2f} kWh"],
                    "json_path": ["assessment.assessment_results.assessment_energy_use.energy_savings_combined"],
                },
                {
                    "name": ["BETTER Inverse Model R^2 (Electricity", "Fossil Fuel)"],
                    "value_template": ["{json_value:,.2f}", "{json_value:,.2f}"],
                    "json_path": ["inverse_model.ELECTRICITY.r2", "inverse_model.FOSSIL_FUEL.r2"],
                },
            ]

            ret = []
            for highlight in highlights:
                full_name = []
                full_value = []
                for i, name in enumerate(highlight["name"]):
                    parsed_result = get_json_path(highlight["json_path"][i], results)
                    value = "N/A"
                    if parsed_result is not None:
                        value = highlight["value_template"][i].format(json_value=parsed_result)
                    full_name.append(name)
                    full_value.append(value)
                ret.append({"name": ", ".join(full_name), "value": ", ".join(full_value)})

            return ret

        # EUI
        elif self.service == self.EUI:
            eui_result = results.get("Fractional EUI (kBtu/sqft)")
            value = "N/A"
            if eui_result is not None:
                value = f"{eui_result:,.2f}"
            coverage = results.get("Annual Coverage %")
            if coverage is None:
                coverage = "N/A"

            return [{"name": "Fractional EUI", "value": f"{value} kBtu/sqft"}, {"name": "Annual Coverage", "value": f"{coverage}%"}]

        # CO2
        elif self.service == self.CO2:
            co2_result = results.get("Average Annual CO2 (kgCO2e)")
            value = "N/A"
            if co2_result is not None:
                value = f"{co2_result:,.0f}"
            coverage = results.get("Annual Coverage %")
            if coverage is None:
                coverage = "N/A"

            return [{"name": "Average Annual CO2", "value": f"{value} kgCO2e"}, {"name": "Annual Coverage", "value": f"{coverage}%"}]

        # Element Statistics
        elif self.service == self.ELEMENTSTATISTICS:
            res = []
            for k, v in results.items():
                if isinstance(v, str):
                    res.append({"name": k, "value": v})
                else:
                    res.append({"name": k, "value": round(v, 2)})
            return res
        # Building Upgrade Recommendation
        elif self.service == self.UPGRADERECOMMENDATION:
            recommendation = results.get("Building Upgrade Recommendation")

            return [
                {"name": "Building Upgrade Recommendation", "value": recommendation},
            ]

        # Add Hello Column
        elif self.service == self.ADD_HELLO_COLUMN:
            return [{"name": "Hello", "value": "Hello"}]    

        # Geopandas Test
        elif self.service == self.GEOPANDAS_TEST:
            lat = results.get("lat", "N/A")
            lon = results.get("lon", "N/A")
            city = results.get("city", "N/A")
            return [
                {"name": "Latitude", "value": f"{lat}"},
                {"name": "Longitude", "value": f"{lon}"},
                {"name": "City", "value": f"{city}"}
            ]

        # Buildings Analysis
        elif self.service == self.BUILDINGS_ANALYSIS:
            building_count = results.get("building_count", 0)
            avg_height = results.get("avg_height")
            building_density = results.get("building_density", 0)
            mean_setback = results.get("mean_setback")
            h3_hex = results.get("h3_hex", "N/A")
            
            highlights = [
                {"name": "Building Count", "value": f"{building_count}"},
                {"name": "Building Density", "value": f"{building_density:.2f} buildings/km²"},
                {"name": "H3 Hexagon", "value": f"{h3_hex}"}
            ]
            
            if avg_height is not None:
                highlights.append({"name": "Average Height", "value": f"{avg_height:.2f} meters"})
            else:
                highlights.append({"name": "Average Height", "value": "No height data"})
                
            if mean_setback is not None:
                highlights.append({"name": "Mean Setback", "value": f"{mean_setback:.2f} meters"})
            else:
                highlights.append({"name": "Mean Setback", "value": "Insufficient data"})
            
            return highlights

        # Unexpected
        return [{"name": "Unexpected Analysis Type", "value": "Oops!"}]

    def in_terminal_state(self):
        """Returns True if the analysis has finished, e.g., stopped, failed,
        completed, etc

        :returns: bool
        """
        return self.status in {self.FAILED, self.STOPPED, self.COMPLETED}

    def can_create(self):
        return self.organization.is_user_ali_root(self.user.id) and (
            self.organization.is_owner(self.user.id) or self.organization.has_role_member(self.user.id)
        )

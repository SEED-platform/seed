# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import logging

from django.db import models

from seed.analysis_pipelines.utils import get_json_path
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization

logger = logging.getLogger(__name__)


class Analysis(models.Model):
    """
    The Analysis represents an analysis performed on one or more properties.
    """
    BSYNCR = 1
    BETTER = 2
    EUI = 3
    CO2 = 4

    SERVICE_TYPES = (
        (BSYNCR, 'BSyncr'),
        (BETTER, 'BETTER'),
        (EUI, 'EUI'),
        (CO2, 'CO2')
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
        (PENDING_CREATION, 'Pending Creation'),
        (CREATING, 'Creating'),
        (READY, 'Ready'),
        (QUEUED, 'Queued'),
        (RUNNING, 'Running'),
        (FAILED, 'Failed'),
        (STOPPED, 'Stopped'),
        (COMPLETED, 'Completed'),
    )

    name = models.CharField(max_length=255, blank=False, default=None)
    service = models.IntegerField(choices=SERVICE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(default=PENDING_CREATION, choices=STATUS_TYPES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
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
            'number_of_analysis_property_views': self.analysispropertyview_set.count(),
            'views': list(analysis_property_views.values_list('id', flat=True).distinct()),
            'cycles': list(analysis_property_views.values_list('cycle', flat=True).distinct())
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
            return [{'name': 'Completed', 'value': ''}]

        # BETTER
        elif self.service == self.BETTER:
            highlights = [
                {
                    'name': ['Potential Cost Savings (USD)'],
                    'value_template': ['${json_value:,.2f}'],
                    'json_path': ['assessment.assessment_energy_use.cost_savings_combined'],
                }, {
                    'name': ['Potential Energy Savings'],
                    'value_template': ['{json_value:,.2f} kWh'],
                    'json_path': ['assessment.assessment_energy_use.energy_savings_combined'],
                }, {
                    'name': ['BETTER Inverse Model R^2 (Electricity', 'Fossil Fuel)'],
                    'value_template': ['{json_value:,.2f}', '{json_value:,.2f}'],
                    'json_path': ['inverse_model.ELECTRICITY.r2', 'inverse_model.FOSSIL_FUEL.r2'],
                }
            ]

            ret = []
            for highlight in highlights:
                full_name = []
                full_value = []
                for i, name in enumerate(highlight['name']):
                    parsed_result = get_json_path(highlight['json_path'][i], results)
                    value = 'N/A'
                    if parsed_result is not None:
                        value = highlight['value_template'][i].format(json_value=parsed_result)
                    full_name.append(name)
                    full_value.append(value)
                ret.append({
                    'name': ', '.join(full_name),
                    'value': ', '.join(full_value)
                })

            return ret

        # EUI
        elif self.service == self.EUI:
            eui_result = results.get('Fractional EUI (kBtu/sqft)')
            value = 'N/A'
            if eui_result is not None:
                value = f'{eui_result:,.2f}'
            coverage = results.get('Annual Coverage %')
            if coverage is None:
                coverage = 'N/A'

            return [
                {'name': 'Fractional EUI', 'value': f'{value} kBtu/sqft'},
                {'name': 'Annual Coverage', 'value': f'{coverage}%'}
            ]

        # CO2
        elif self.service == self.CO2:
            co2_result = results.get('Average Annual CO2 (kgCO2e)')
            value = 'N/A'
            if co2_result is not None:
                value = f'{co2_result:,.0f}'
            coverage = results.get('Annual Coverage %')
            if coverage is None:
                coverage = 'N/A'

            return [
                {'name': 'Average Annual CO2', 'value': f'{value} kgCO2e'},
                {'name': 'Annual Coverage', 'value': f'{coverage}%'}
            ]

        # Unexpected
        return [{'name': 'Unexpected Analysis Type', 'value': 'Oops!'}]

    def in_terminal_state(self):
        """Returns True if the analysis has finished, e.g., stopped, failed,
        completed, etc

        :returns: bool
        """
        return self.status in [self.FAILED, self.STOPPED, self.COMPLETED]

# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
from collections import Counter

from celery import chain, shared_task
from django.db.models import F

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    AnalysisPipelineError,
    analysis_pipeline_task,
    task_create_analysis_property_views,
)
from seed.models import Analysis, AnalysisMessage, AnalysisPropertyView, Column, Element, PropertyView
from quantityfield.units import ureg

logger = logging.getLogger(__name__)


class HVACMetricsPipeline(AnalysisPipeline):
    def _prepare_analysis(self, property_view_ids, start_analysis=True):
        # if theres not elements, just exit
        views = PropertyView.objects.filter(id__in=property_view_ids)
        analysis = Analysis.objects.get(id=self._analysis_id)
        if not Element.objects.filter(property__in=views.values_list("property", flat=True)).exists():
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=self._analysis_id,
                analysis_property_view_id=None,
                user_message="None of the selected properties have elements, which are requied for this analysis.",
                debug_message="",
            )
            analysis.status = Analysis.FAILED
            analysis.save()
            raise AnalysisPipelineError("None of the selected properties have elements, which are requied for this analysis.")

        progress_data = self.get_progress_data()
        progress_data.total = 3
        progress_data.save()

        chain(
            task_create_analysis_property_views.si(self._analysis_id, property_view_ids),
            _finish_preparation.s(self._analysis_id),
            _run_analysis.s(self._analysis_id, analysis.configuration),
        ).apply_async()

    def _start_analysis(self):
        return None


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _finish_preparation(self, analysis_view_ids_by_property_view_id, analysis_id):
    pipeline = HVACMetricsPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready("Ready to run HVAC Metrics analysis")

    # here is where errors would be filtered out

    return list(analysis_view_ids_by_property_view_id.values())


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, analysis_property_view_ids, analysis_id, config):
    pipeline = HVACMetricsPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Generating Numbers")
    analysis = Analysis.objects.get(id=analysis_id)

    # get/create relevant columns
    existing_columns = _create_analysis_columns(analysis)
    gfa_column = Column.objects.filter(id=config.get("floor_area_column")).first()

    def get_gfa(view):
        if gfa_column is None:
            return None
        if gfa_column.is_extra_data:
            gfa = view.state.extra_data.get(gfa_column.column_name)
        else:
            gfa = getattr(view.state, gfa_column.column_name)
        
        return float(gfa) if not isinstance(gfa, ureg.Quantity) else gfa.magnitude

    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)
    for analysis_property_view in analysis_property_views:
        # get property view and its elements
        property_view = property_views_by_apv_id[analysis_property_view.id]
        elements = Element.objects.filter(property=property_view.property)

        # Calculate total cooling cap
        cooling_caps = elements.annotate(cooling_cap=F("extra_data__Nominal Cooling Cap. (Tons)")).values_list("cooling_cap", flat=True)
        total_cooling_cap = sum([c for c in cooling_caps if c is not None])

        # Calculate most common refrigeration type
        refrigeration_on_types = elements.annotate(refrigeration_on_type=F("extra_data__Refrigeration on Type")).values_list(
            "refrigeration_on_type", flat=True
        )
        most_common_refrigeration_on_type = Counter(refrigeration_on_types).most_common(1)[0][0] if refrigeration_on_types else None

        # Calculate Total Electric Data Max Fuse
        gfa = get_gfa(property_view)
        if gfa:
            max_fuses = elements.annotate(max_fuse=F("extra_data__Eletrical Data - Max Fuse")).values_list("max_fuse", flat=True)
            max_fuse = sum([f for f in max_fuses if f is not None]) / gfa
        else:
            max_fuse = "NA"

        # Calculate Airflow Rate per unit Area
        if gfa:
            airflow_rates = elements.annotate(air_flow_rate=F("extra_data__Supply - SA (CFM)")).values_list("air_flow_rate", flat=True)
            airflow_rate_per_unit_area = sum([f for f in airflow_rates if f is not None]) / gfa
        else:
            airflow_rate_per_unit_area = "NA"

        # update the analysis_property_view
        analysis_property_view.parsed_results = {
            "Total Nominal Cooling Cap. (Tons)": total_cooling_cap,
            "Most Common Refrigeration On Type": most_common_refrigeration_on_type,
            "Total Electric Data Max Fuse": max_fuse,
            "Airflow Rate per unit Area": airflow_rate_per_unit_area,
        }
        analysis_property_view.save()

        # write to property columns
        if "total_nominal_cooling_cap" in existing_columns:
            property_view.state.extra_data.update({"total_nominal_cooling_cap": total_cooling_cap})
        if "most_common_refrigeration_on_type" in existing_columns:
            property_view.state.extra_data.update({"most_common_refrigeration_on_type": most_common_refrigeration_on_type})
        if "airflow_rate_per_unit_area" in existing_columns:
            property_view.state.extra_data.update({"airflow_rate_per_unit_area": airflow_rate_per_unit_area})
        if "total_electric_data_max_fuse" in existing_columns:
            property_view.state.extra_data.update({"total_electric_data_max_fuse": max_fuse})

        property_view.state.save()

    # all done!
    pipeline.set_analysis_status_to_completed()


def _create_analysis_columns(analysis):
    existing_columns = []
    column_meta = [
        {
            "column_name": "total_nominal_cooling_cap",
            "display_name": "Total Nominal Cooling Cap.",
            "description": "created by HVAC Metric analysis",
        },
        {
            "column_name": "most_common_refrigeration_on_type",
            "display_name": "Most Common Refrigeration On Type",
            "description": "created by HVAC Metric analysis",
        },
        {
            "column_name": " airflow_rate_per_unit_area",
            "display_name": "Airflow Rate per unit Area",
            "description": " Airflow Rate per unit Area",
        },
        {
            "column_name": "total_electric_data_max_fuse",
            "display_name": "Total Electric Data Max Fuse",
            "description": "Total Electric Data Max Fuse",
        },
    ]

    for col in column_meta:
        try:
            Column.objects.get(
                column_name=col["column_name"],
                organization=analysis.organization,
                table_name="PropertyState",
            )
            existing_columns.append(col["column_name"])
        except Exception:
            if analysis.can_create():
                column = Column.objects.create(
                    is_extra_data=True,
                    column_name=col["column_name"],
                    organization=analysis.organization,
                    table_name="PropertyState",
                )
                column.display_name = col["display_name"]
                column.column_description = col["description"]
                column.save()
                existing_columns.append(col["column_name"])

    return existing_columns

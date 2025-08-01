"""
SEED Platform Hello World Analysis Example
A minimal analysis that demonstrates the basic structure and workflow.
"""

import logging
from celery import chain, shared_task

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    AnalysisPipelineError,
    analysis_pipeline_task,
    task_create_analysis_property_views,
)


logger = logging.getLogger(__name__)

# Simple error/message constants
ERROR_NO_PROPERTIES = 0
WARNING_DEMO_ANALYSIS = 1

HELLO_WORLD_MESSAGES = {
    ERROR_NO_PROPERTIES: "No properties found for Hello World analysis.",
    WARNING_DEMO_ANALYSIS: "This is a demonstration analysis only.",
}


def _validate_properties(property_view_ids):
    """Simple validation - just check if we have any properties."""
    from seed.models import PropertyView

    property_views = PropertyView.objects.filter(id__in=property_view_ids)
    
    if not property_views.exists():
        return [], {"general": [HELLO_WORLD_MESSAGES[ERROR_NO_PROPERTIES]]}
    
    # Return all property views as "valid"
    valid_property_view_ids = [pv.id for pv in property_views]
    return valid_property_view_ids, {}


def _calculate_hello_world_result(property_view):
    """Calculate a simple result - just return property name length."""
    property_name = property_view.state.property_name or "Unnamed Property"
    name_length = len(property_name)
    
    return {
        "property_name": property_name,
        "name_length": name_length,
        "greeting": f"Hello {property_name}!",
        "analysis_timestamp": property_view.state.updated.isoformat() if property_view.state.updated else None
    }


class HelloWorldPipeline(AnalysisPipeline):
    """
    A minimal analysis pipeline that demonstrates the basic structure.
    This analysis simply counts the characters in each property's name.
    """
    
    def _prepare_analysis(self, property_view_ids, start_analysis=True):
        """Prepare the Hello World analysis."""
        
        # Step 1: Validate inputs
        valid_property_view_ids, errors = _validate_properties(property_view_ids)
        
        # Step 2: Handle validation errors
        if not valid_property_view_ids:
            from seed.models import Analysis, AnalysisMessage

            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=self._analysis_id,
                analysis_property_view_id=None,
                user_message=HELLO_WORLD_MESSAGES[ERROR_NO_PROPERTIES],
                debug_message="No valid properties provided for analysis",
            )
            
            analysis = Analysis.objects.get(id=self._analysis_id)
            analysis.status = Analysis.FAILED
            analysis.save()
            raise AnalysisPipelineError(HELLO_WORLD_MESSAGES[ERROR_NO_PROPERTIES])
        
        # Step 3: Log a demo warning
        from seed.models import AnalysisMessage

        AnalysisMessage.log_and_create(
            logger=logger,
            type_=AnalysisMessage.WARNING,
            analysis_id=self._analysis_id,
            analysis_property_view_id=None,
            user_message=HELLO_WORLD_MESSAGES[WARNING_DEMO_ANALYSIS],
            debug_message="Hello World analysis starting",
        )
        
        # Step 4: Set up progress tracking (2 steps: prepare + run)
        progress_data = self.get_progress_data()
        progress_data.total = 2
        progress_data.save()
        
        # Step 5: Start the Celery task chain
        chain(
            task_create_analysis_property_views.si(self._analysis_id, valid_property_view_ids),
            _finish_hello_world_preparation.s(self._analysis_id),
            _run_hello_world_analysis.s(self._analysis_id),
        ).apply_async()

    def _start_analysis(self):
        """Start method - not used in this simple example."""
        return None


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _finish_hello_world_preparation(self, analysis_view_ids_by_property_view_id, analysis_id):
    """Finish the preparation phase and transition to READY status."""
    
    pipeline = HelloWorldPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready("Ready to run Hello World analysis")
    
    # Just pass through the analysis property view IDs
    analysis_property_view_ids = list(analysis_view_ids_by_property_view_id.values())
    return analysis_property_view_ids


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_hello_world_analysis(self, analysis_property_view_ids, analysis_id):
    """Run the actual Hello World analysis."""
    
    pipeline = HelloWorldPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Running Hello World calculations")

    from seed.models import Analysis, AnalysisPropertyView, Column

    analysis = Analysis.objects.get(id=analysis_id)
    
    # Step 1: Create result column if it doesn't exist
    column_name = "hello_world_name_length"
    try:
        Column.objects.get(
            column_name=column_name,
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name=column_name,
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Property Name Length",
                column_description="Number of characters in property name (Hello World demo)",
                data_type="number",
            )
    
    # Step 2: Get analysis property views with related data
    analysis_property_views = AnalysisPropertyView.objects.filter(
        id__in=analysis_property_view_ids
    ).prefetch_related("property", "cycle", "property_state")
    
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)
    
    # Step 3: Process each property
    for analysis_property_view in analysis_property_views:
        property_view = property_views_by_apv_id[analysis_property_view.id]
        
        # Calculate our simple result
        result = _calculate_hello_world_result(property_view)
        
        # Save results to analysis property view
        analysis_property_view.parsed_results = result
        analysis_property_view.save()
        
        # Also save name length to property state extra_data if column exists
        try:
            Column.objects.get(
                column_name=column_name,
                organization=analysis.organization,
                table_name="PropertyState",
            )
            property_view.state.extra_data[column_name] = result["name_length"]
            property_view.state.save()
        except Column.DoesNotExist:
            pass  # Column doesn't exist, skip saving to extra_data
    
    # Step 4: Complete the analysis
    pipeline.set_analysis_status_to_completed()

    # Log completion message
    from seed.models import AnalysisMessage

    AnalysisMessage.log_and_create(
        logger=logger,
        type_=AnalysisMessage.INFO,
        analysis_id=analysis_id,
        analysis_property_view_id=None,
        user_message=f"Hello World analysis completed for {len(analysis_property_views)} properties",
        debug_message="Analysis finished successfully",
    )
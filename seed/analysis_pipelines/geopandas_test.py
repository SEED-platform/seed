"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

Geopandas Test Analysis - Generates random coordinates in Atlanta, Georgia
"""

import logging
import numpy as np
import geopandas as gpd
from shapely.geometry import Point

from celery import chain, shared_task

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    analysis_pipeline_task,
    task_create_analysis_property_views,
)
from seed.models import Analysis, AnalysisPropertyView, Column

logger = logging.getLogger(__name__)


class GeopandasTestPipeline(AnalysisPipeline):
    def _prepare_analysis(self, property_view_ids, start_analysis=True):
        """Prepare the geopandas test analysis"""
        
        progress_data = self.get_progress_data()
        progress_data.total = 3
        progress_data.save()

        chain(
            task_create_analysis_property_views.si(self._analysis_id, property_view_ids),
            _finish_preparation.s(self._analysis_id),
            _run_analysis.s(self._analysis_id),
        ).apply_async()

    def _start_analysis(self):
        return None


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _finish_preparation(self, analysis_view_ids_by_property_view_id, analysis_id):
    """Finish preparation for geopandas test analysis"""
    pipeline = GeopandasTestPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready("Ready to run Geopandas Test Analysis")

    return list(analysis_view_ids_by_property_view_id.values())


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, analysis_property_view_ids, analysis_id):
    """Run the geopandas test analysis - generates random Atlanta coordinates"""
    pipeline = GeopandasTestPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Generating random Atlanta coordinates using geopandas.")

    analysis = Analysis.objects.get(id=analysis_id)
    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)
    
    # Create the geopandas columns if they don't exist
    lat_column = _create_geopandas_lat_column(analysis)
    lon_column = _create_geopandas_lon_column(analysis)
    city_column = _create_geopandas_city_column(analysis)

    # Atlanta, Georgia coordinates (approximate city center)
    atlanta_lat = 33.7490
    atlanta_lon = -84.3880
    
    # Radius for random generation (roughly 20 miles from center)
    radius_degrees = 0.3  # ~20 miles in degrees

    logger.info(f"Processing {len(analysis_property_views)} properties for geopandas test analysis")

    for analysis_property_view in analysis_property_views:
        analysis_property_view.parsed_results = {}
        property_view = property_views_by_apv_id[analysis_property_view.id]

        # Generate random coordinates within Atlanta area
        # Using numpy for random generation within a circular area
        angle = np.random.uniform(0, 2 * np.pi)
        distance = np.random.uniform(0, radius_degrees)
        
        random_lat = atlanta_lat + distance * np.cos(angle)
        random_lon = atlanta_lon + distance * np.sin(angle)
        
        # Create a geopandas point to demonstrate geopandas usage
        point = Point(random_lon, random_lat)
        # Create GeoDataFrame without CRS to avoid pyproj compatibility issues
        gdf = gpd.GeoDataFrame([1], geometry=[point])
        
        # Extract coordinates from the geopandas geometry
        final_lat = float(gdf.geometry.y.iloc[0])
        final_lon = float(gdf.geometry.x.iloc[0])
        
        # Store results in analysis record
        analysis_property_view.parsed_results = {
            'lat': final_lat,
            'lon': final_lon,
            'city': 'Atlanta',
            'state': 'Georgia',
            'geopandas_version': gpd.__version__,
            'geometry_type': 'Point'
        }
        
        # Save to PropertyState extra_data using proper column names
        if lat_column:
            property_view.state.extra_data[lat_column.column_name] = final_lat
            analysis_property_view.parsed_results[lat_column.column_name] = final_lat
        if lon_column:
            property_view.state.extra_data[lon_column.column_name] = final_lon
            analysis_property_view.parsed_results[lon_column.column_name] = final_lon
        if city_column:
            property_view.state.extra_data[city_column.column_name] = 'Atlanta'
            analysis_property_view.parsed_results[city_column.column_name] = 'Atlanta'

        analysis_property_view.save()
        property_view.state.save()
        
        logger.info(f"Generated coordinates for property {property_view.property.id}: "
                   f"lat={final_lat:.6f}, lon={final_lon:.6f}")

    # Analysis complete
    pipeline.set_analysis_status_to_completed()
    logger.info(f"Geopandas test analysis {analysis_id} completed successfully")


def _create_geopandas_lat_column(analysis):
    """Create a geopandas latitude column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="Geopandas Test Latitude",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Geopandas Test Latitude",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Geopandas Test Latitude",
                column_description="Random latitude coordinate in Atlanta area (geopandas demo)",
                data_type="number",
            )
            return column
        else:
            return None


def _create_geopandas_lon_column(analysis):
    """Create a geopandas longitude column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="Geopandas Test Longitude",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Geopandas Test Longitude",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Geopandas Test Longitude",
                column_description="Random longitude coordinate in Atlanta area (geopandas demo)",
                data_type="number",
            )
            return column
        else:
            return None


def _create_geopandas_city_column(analysis):
    """Create a geopandas city column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="Geopandas Test City",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Geopandas Test City",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Geopandas Test City",
                column_description="City name for geopandas test (Atlanta)",
                data_type="string",
            )
            return column
        else:
            return None

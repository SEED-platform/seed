"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

Geopandas Test Analysis - Generates random coordinates in various US cities
"""

import logging
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import random

from celery import chain, shared_task

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    analysis_pipeline_task,
    task_create_analysis_property_views,
)
from seed.models import Analysis, AnalysisPropertyView, Column

logger = logging.getLogger(__name__)


# Inland US cities (avoid coastal cities) with their coordinates and radius for random generation
US_CITIES = [
    {
        'name': 'Denver',
        'state': 'Colorado',
        'lat': 39.7392,
        'lon': -104.9903,
        'radius_degrees': 0.2
    },
    {
        'name': 'Dallas',
        'state': 'Texas',
        'lat': 32.7767,
        'lon': -96.7970,
        'radius_degrees': 0.25
    },
    {
        'name': 'Phoenix',
        'state': 'Arizona',
        'lat': 33.4484,
        'lon': -112.0740,
        'radius_degrees': 0.25
    },
    {
        'name': 'Atlanta',
        'state': 'Georgia',
        'lat': 33.7490,
        'lon': -84.3880,
        'radius_degrees': 0.2
    },
    {
        'name': 'Minneapolis',
        'state': 'Minnesota',
        'lat': 44.9778,
        'lon': -93.2650,
        'radius_degrees': 0.2
    },
    {
        'name': 'Nashville',
        'state': 'Tennessee',
        'lat': 36.1627,
        'lon': -86.7816,
        'radius_degrees': 0.2
    },
    {
        'name': 'Kansas City',
        'state': 'Missouri',
        'lat': 39.0997,
        'lon': -94.5786,
        'radius_degrees': 0.2
    },
    {
        'name': 'Salt Lake City',
        'state': 'Utah',
        'lat': 40.7608,
        'lon': -111.8910,
        'radius_degrees': 0.2
    }
]


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
    """Run the geopandas test analysis - generates random coordinates in various US cities"""
    pipeline = GeopandasTestPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Generating random US city coordinates using geopandas.")

    analysis = Analysis.objects.get(id=analysis_id)
    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)
    
    # Create the geopandas columns if they don't exist
    lat_column = _create_geopandas_lat_column(analysis)
    lon_column = _create_geopandas_lon_column(analysis)
    city_column = _create_geopandas_city_column(analysis)

    logger.info(f"Processing {len(analysis_property_views)} properties for geopandas test analysis")

    for analysis_property_view in analysis_property_views:
        analysis_property_view.parsed_results = {}
        property_view = property_views_by_apv_id[analysis_property_view.id]

        # Randomly select a US city
        selected_city = random.choice(US_CITIES)
        
        # Generate random coordinates within the selected city's area
        angle = np.random.uniform(0, 2 * np.pi)
        distance = np.random.uniform(0, selected_city['radius_degrees'])
        
        # Add slight perturbation to avoid clustering while staying well inland
        # Very small random offset (±0.005 degrees ≈ ±0.5 km)
        lat_perturbation = np.random.uniform(-0.005, 0.005)
        lon_perturbation = np.random.uniform(-0.005, 0.005)
        
        random_lat = selected_city['lat'] + distance * np.cos(angle) + lat_perturbation
        random_lon = selected_city['lon'] + distance * np.sin(angle) + lon_perturbation
        
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
            'city': selected_city['name'],
            'state': selected_city['state'],
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
            property_view.state.extra_data[city_column.column_name] = selected_city['name']
            analysis_property_view.parsed_results[city_column.column_name] = selected_city['name']

        analysis_property_view.save()
        property_view.state.save()
        
        logger.info(f"Generated coordinates for property {property_view.property.id}: "
                   f"lat={final_lat:.6f}, lon={final_lon:.6f} in {selected_city['name']}, {selected_city['state']}")

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
                column_description="Random latitude coordinate in various US cities (geopandas demo)",
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
                column_description="Random longitude coordinate in various US cities (geopandas demo)",
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
                column_description="City name for geopandas test (various US cities)",
                data_type="string",
            )
            return column
        else:
            return None

"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

Degree Days Analysis - Calculates Cooling Degree Days (CDD) and Heating Degree Days (HDD)
using GridMET temperature data for building energy modeling

Adrian Mungroo, 2025-08-02
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd

from celery import chain, shared_task

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    analysis_pipeline_task,
    task_create_analysis_property_views,
)
from seed.models import Analysis, AnalysisPropertyView, Column

logger = logging.getLogger(__name__)


class DegreeDaysAnalysisPipeline(AnalysisPipeline):
    """
    Pipeline for calculating degree days using GridMET temperature data.
    
    Calculates Cooling Degree Days (CDD) and Heating Degree Days (HDD) for
    building energy modeling using GridMET temperature data.
    """

    def _prepare_analysis(self, property_view_ids, start_analysis=True):
        """Prepare the degree days analysis"""

        # Progress data might be None for certain analysis states
        progress_data = self.get_progress_data()
        if progress_data:
            progress_data.total = 3
            progress_data.save()

        chain(
            task_create_analysis_property_views.si(self._analysis_id, property_view_ids),
            _finish_preparation.s(self._analysis_id),
            _run_analysis.s(self._analysis_id),
        ).apply_async()

    def _start_analysis(self):
        return None


def _get_property_coordinates(property_view) -> Optional[Tuple[float, float]]:
    """
    Extract latitude and longitude from property data.
    
    Args:
        property_view: PropertyView object
        
    Returns:
        Tuple of (lat, lon) or None if coordinates not found
    """
    try:
        # Try to get coordinates from property state data
        property_data = property_view.state.extra_data
        
        # Look for various coordinate column names
        lat_cols = ['latitude', 'lat', 'Latitude', 'Lat', 'Geopandas Test Latitude', 'geopandas_test_lat']
        lon_cols = ['longitude', 'lon', 'Longitude', 'Lon', 'Geopandas Test Longitude', 'geopandas_test_lon']
        
        lat = None
        lon = None
        
        # Find latitude
        for col in lat_cols:
            if col in property_data:
                try:
                    lat = float(property_data[col])
                    break
                except (ValueError, TypeError):
                    continue
        
        # Find longitude
        for col in lon_cols:
            if col in property_data:
                try:
                    lon = float(property_data[col])
                    break
                except (ValueError, TypeError):
                    continue
        
        if lat is not None and lon is not None:
            logger.info(f"Found coordinates: {lat}, {lon}")
            return lat, lon
        else:
            logger.warning(f"No coordinates found for property {property_view.id}")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting coordinates: {e}")
        return None


def _calculate_degree_days(lat: float, lon: float, year: int = 2020) -> Dict[str, Any]:
    """
    Calculate degree days using GridMET data with real methodology from degree_day.py.
    
    Uses xarray to read NetCDF files and calculates degree days using daily temperature data.
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        year: Year for analysis (default: 2020)
        
    Returns:
        Dictionary with degree days results
    """
    # Base temperature for degree day calculations (65°F)
    BASE_TEMP_F = 65.0
    
    # Data directory - use /tmp for Docker compatibility
    data_dir = "/tmp/gridmet_weather"
    year_dir = Path(data_dir) / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    
    # File paths
    tmax_file = year_dir / f"tmmx_{year}.nc"
    tmin_file = year_dir / f"tmmn_{year}.nc"
    
    # Download files if they don't exist (exact logic from degree_day.py)
    base_url = "http://www.northwestknowledge.net/metdata/data"
    
    if not tmax_file.exists():
        logger.info(f"Downloading maximum temperature data for {year}...")
        try:
            subprocess.run([
                "wget", "-nc", "-c", "-nd", "-P", str(year_dir),
                f"{base_url}/tmmx_{year}.nc"
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise FileNotFoundError(f"Failed to download maximum temperature file for {year}: {e}")
    
    if not tmin_file.exists():
        logger.info(f"Downloading minimum temperature data for {year}...")
        try:
            subprocess.run([
                "wget", "-nc", "-c", "-nd", "-P", str(year_dir),
                f"{base_url}/tmmn_{year}.nc"
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise FileNotFoundError(f"Failed to download minimum temperature file for {year}: {e}")
    
    # Verify files exist
    if not tmax_file.exists():
        raise FileNotFoundError(f"Maximum temperature file not found: {tmax_file}")
    if not tmin_file.exists():
        raise FileNotFoundError(f"Minimum temperature file not found: {tmin_file}")
    
    try:
        logger.info(f"Loading GridMET data for lat={lat}, lon={lon}, year={year}")
        
        # Use xarray to read NetCDF files (exact methodology from degree_day.py)
        import xarray as xr
        import numpy as np
        
        # Load temperature datasets using default netCDF4 engine (now compatible)
        tmax_ds = xr.open_dataset(tmax_file)
        tmin_ds = xr.open_dataset(tmin_file)
        
        # Find the nearest grid point to the given lat/lon (exact from degree_day.py)
        lat_idx = abs(tmax_ds.lat - lat).argmin()
        lon_idx = abs(tmax_ds.lon - lon).argmin()
        
        # Extract temperature data for the specific location
        tmax_loc = tmax_ds.air_temperature[:, lat_idx, lon_idx]
        tmin_loc = tmin_ds.air_temperature[:, lat_idx, lon_idx]
        
        # Convert from Kelvin to Fahrenheit
        tmax_f = (tmax_loc - 273.15) * 9/5 + 32
        tmin_f = (tmin_loc - 273.15) * 9/5 + 32
        
        # Calculate mean temperature
        tmean_f = (tmax_f + tmin_f) / 2
        
        # Calculate daily degree days using mean temperature
        # CDD: sum of (Tmean - 65°F) when Tmean > 65°F
        cdd_daily = np.where(tmean_f > BASE_TEMP_F, tmean_f - BASE_TEMP_F, 0)
        
        # HDD: sum of (65°F - Tmean) when Tmean < 65°F
        hdd_daily = np.where(tmean_f < BASE_TEMP_F, BASE_TEMP_F - tmean_f, 0)
        
        # Calculate annual totals
        annual_cdd = np.sum(cdd_daily)
        annual_hdd = np.sum(hdd_daily)
        
        # Calculate mean temperatures
        tmax_mean = np.mean(tmax_f)
        tmin_mean = np.mean(tmin_f)
        
        # Get actual coordinates of the grid point used
        actual_lat = float(tmax_ds.lat[lat_idx])
        actual_lon = float(tmax_ds.lon[lon_idx])
        
        # Close datasets
        tmax_ds.close()
        tmin_ds.close()
        
        logger.info(f"Degree days calculation completed: CDD={annual_cdd:.1f}, HDD={annual_hdd:.1f}")
        
        return {
            'cdd': float(annual_cdd),
            'hdd': float(annual_hdd),
            'tmax_mean': float(tmax_mean),
            'tmin_mean': float(tmin_mean),
            'location': (actual_lat, actual_lon),
            'requested_location': (lat, lon),
            'year': year,
            'grid_resolution_km': '~4km',
            'method': 'Real GridMET data processing using xarray (degree_day.py methodology)'
        }
        
    except Exception as e:
        # Clean up datasets if they were opened
        if 'tmax_ds' in locals():
            tmax_ds.close()
        if 'tmin_ds' in locals():
            tmin_ds.close()
        logger.error(f"Error in degree days calculation: {e}")
        raise e


def _create_cdd_column(analysis):
    """Create Cooling Degree Days column."""
    try:
        return Column.objects.get(
            column_name="Cooling Degree Days",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Cooling Degree Days",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Cooling Degree Days",
                column_description="Annual cooling degree days for building energy modeling",
                data_type="number",
            )
            return column
        else:
            return None


def _create_hdd_column(analysis):
    """Create Heating Degree Days column."""
    try:
        return Column.objects.get(
            column_name="Heating Degree Days",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Heating Degree Days",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Heating Degree Days",
                column_description="Annual heating degree days for building energy modeling",
                data_type="number",
            )
            return column
        else:
            return None


def _create_tmax_mean_column(analysis):
    """Create Mean Max Temperature column."""
    try:
        return Column.objects.get(
            column_name="Mean Max Temperature",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Mean Max Temperature",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Mean Max Temperature (°F)",
                column_description="Annual mean maximum temperature in Fahrenheit",
                data_type="number",
            )
            return column
        else:
            return None


def _create_tmin_mean_column(analysis):
    """Create Mean Min Temperature column."""
    try:
        return Column.objects.get(
            column_name="Mean Min Temperature",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Mean Min Temperature",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Mean Min Temperature (°F)",
                column_description="Annual mean minimum temperature in Fahrenheit",
                data_type="number",
            )
            return column
        else:
            return None


def _create_year_column(analysis):
    """Create Degree Days Year column."""
    try:
        return Column.objects.get(
            column_name="Degree Days Year",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Degree Days Year",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Analysis Year",
                column_description="Year of temperature data used for degree days calculation",
                data_type="number",
            )
            return column
        else:
            return None


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _finish_preparation(self, analysis_view_ids_by_property_view_id, analysis_id):
    """Finish preparation for degree days analysis"""
    pipeline = DegreeDaysAnalysisPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready("Ready to run Degree Days Analysis")

    return list(analysis_view_ids_by_property_view_id.values())


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, analysis_property_view_ids, analysis_id):
    """Run the degree days analysis - calculates CDD and HDD for property coordinates"""
    pipeline = DegreeDaysAnalysisPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Calculating degree days for property coordinates.")

    analysis = Analysis.objects.get(id=analysis_id)
    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)

    # Get year from analysis configuration or use default
    year = analysis.configuration.get('year', 2020)
    logger.info(f"Using year {year} from analysis configuration")

    # Create the degree days analysis columns if they don't exist
    cdd_column = _create_cdd_column(analysis)
    hdd_column = _create_hdd_column(analysis)
    tmax_mean_column = _create_tmax_mean_column(analysis)
    tmin_mean_column = _create_tmin_mean_column(analysis)
    year_column = _create_year_column(analysis)

    # Process each property
    for apv_id, property_view in property_views_by_apv_id.items():
        try:
            # Get coordinates
            coords = _get_property_coordinates(property_view)
            if coords is None:
                logger.warning(f"No coordinates found for property {property_view.id}")
                continue
            
            lat, lon = coords
            
            # Calculate degree days using the configured year
            results = _calculate_degree_days(lat, lon, year)
            
            # Update the analysis property view with results
            apv = AnalysisPropertyView.objects.get(id=apv_id)
            apv.parsed_results = results
            apv.save()
            
            # Update property state extra data with column values
            # Use the property state model correctly
            property_state = property_view.state
            if property_state.extra_data is None:
                property_state.extra_data = {}
            
            property_state.extra_data['Cooling Degree Days'] = results['cdd']
            property_state.extra_data['Heating Degree Days'] = results['hdd']
            property_state.extra_data['Mean Max Temperature'] = results['tmax_mean']
            property_state.extra_data['Mean Min Temperature'] = results['tmin_mean']
            property_state.extra_data['Degree Days Year'] = results['year']
            property_state.save()
            
            logger.info(f"Degree days analysis completed for property {property_view.id}: CDD={results['cdd']:.1f}, HDD={results['hdd']:.1f}")
            
        except Exception as e:
            logger.error(f"Error in degree days analysis for property {property_view.id}: {e}")
            continue

    # Update overall analysis results with the correct year
    analysis.parsed_results = {
        'analysis_type': 'degree_days',
        'year': year,
        'total_properties': len(property_views_by_apv_id)
    }
    analysis.save()

    pipeline.set_analysis_status_to_completed()
    return analysis_property_view_ids 
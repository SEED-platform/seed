"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

Buildings Analysis - Analyzes building density, height, and setback in area around property coordinates

Adrian Mungroo, 2025-07-25
"""

import logging
import os
import json
import gzip
import hashlib
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import geopandas as gpd
import mercantile
import h3
import requests
from shapely.geometry import Point, Polygon, box, shape

from celery import chain, shared_task

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    analysis_pipeline_task,
    task_create_analysis_property_views,
)
from seed.models import Analysis, AnalysisPropertyView, Column

logger = logging.getLogger(__name__)


class BuildingsAnalysisPipeline(AnalysisPipeline):
    def _prepare_analysis(self, property_view_ids, start_analysis=True):
        """Prepare the buildings analysis"""

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
    """Finish preparation for buildings analysis"""
    pipeline = BuildingsAnalysisPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready("Ready to run Buildings Analysis")

    return list(analysis_view_ids_by_property_view_id.values())


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, analysis_property_view_ids, analysis_id):
    """Run the buildings analysis - analyzes building data around property coordinates"""
    pipeline = BuildingsAnalysisPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Analyzing building data around property coordinates.")

    analysis = Analysis.objects.get(id=analysis_id)
    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)

    # Create the building analysis columns if they don't exist
    building_count_column = _create_building_count_column(analysis)
    avg_height_column = _create_avg_height_column(analysis)
    building_density_column = _create_building_density_column(analysis)
    hex_area_column = _create_hex_area_column(analysis)
    mean_setback_column = _create_mean_setback_column(analysis)
    h3_hex_column = _create_h3_hex_column(analysis)

    # Configuration parameters
    h3_resolution = analysis.configuration.get('h3_resolution', 8)
    zoom_level = analysis.configuration.get('zoom_level', 9)
    max_workers = analysis.configuration.get('max_workers', 4)

    logger.info(f"Processing {len(analysis_property_views)} properties for buildings analysis")
    logger.info(f"Using H3 resolution: {h3_resolution}, Zoom level: {zoom_level}")

    # Load dataset links if available
    dataset_path = analysis.configuration.get('dataset_path', '/seed/dataset-links.csv')
    links_df = None
    
    # Try multiple possible paths
    possible_paths = [
        dataset_path,
        '/seed/dataset-links.csv',
        'dataset-links.csv',
        os.path.join(os.getcwd(), 'dataset-links.csv')
    ]
    
    for path in possible_paths:
        try:
            if os.path.exists(path):
                links_df = pd.read_csv(path, dtype={'QuadKey': str})
                logger.info(f"Loaded dataset links from {path}")
                break
            else:
                logger.warning(f"Dataset links file not found: {path}")
        except Exception as e:
            logger.warning(f"Error loading dataset from {path}: {e}")
    
    if links_df is None:
        logger.warning("No dataset links available, returning basic results")

    for analysis_property_view in analysis_property_views:
        analysis_property_view.parsed_results = {}
        property_view = property_views_by_apv_id[analysis_property_view.id]

        logger.info(f"Processing property {property_view.property.id} (PropertyView ID: {property_view.id})")

        # Try to get latitude and longitude from property data
        lat, lon = _get_property_coordinates(property_view)
        logger.info(f"Coordinates detected: lat={lat}, lon={lon}")
        
        if lat is None or lon is None:
            logger.warning(f"No coordinates found for property {property_view.property.id}")
            # Set default/null values
            results = {
                'error': 'No coordinates available',
                'building_count': 0,
                'avg_height': None,
                'building_density': 0,
                'hex_area_km2': 0,
                'mean_setback': None,
                'h3_hex': None
            }
        else:
            # Run the actual building analysis
            logger.info(f"Dataset available: {links_df is not None}")
            if links_df is not None:
                logger.info(f"Dataset shape: {links_df.shape}")
            
            try:
                results = _analyze_buildings_for_coordinates(
                    lat, lon, h3_resolution, zoom_level, links_df, max_workers
                )
                logger.info(f"Building analysis completed for property {property_view.property.id}")
            except Exception as e:
                logger.error(f"Error in building analysis for property {property_view.property.id}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Set default values on error
                results = {
                    'error': f'Building analysis failed: {str(e)}',
                    'building_count': 0,
                    'avg_height': None,
                    'building_density': 0,
                    'hex_area_km2': 0,
                    'mean_setback': None,
                    'h3_hex': None
                }

        # Store results in analysis record
        analysis_property_view.parsed_results = results

        # Save to PropertyState extra_data using proper column names
        if building_count_column:
            property_view.state.extra_data[building_count_column.column_name] = results.get('building_count', 0)
        if avg_height_column:
            property_view.state.extra_data[avg_height_column.column_name] = results.get('avg_height')
        if building_density_column:
            property_view.state.extra_data[building_density_column.column_name] = results.get('building_density', 0)
        if hex_area_column:
            property_view.state.extra_data[hex_area_column.column_name] = results.get('hex_area_km2', 0)
        if mean_setback_column:
            property_view.state.extra_data[mean_setback_column.column_name] = results.get('mean_setback')
        if h3_hex_column:
            property_view.state.extra_data[h3_hex_column.column_name] = results.get('h3_hex', '')
        
        # Save raw results to parsed_results for highlights display
        analysis_property_view.parsed_results = {
            'building_count': results.get('building_count', 0),
            'avg_height': results.get('avg_height'),
            'building_density': results.get('building_density', 0),
            'hex_area_km2': results.get('hex_area_km2', 0),
            'mean_setback': results.get('mean_setback'),
            'h3_hex': results.get('h3_hex', '')
        }

        analysis_property_view.save()
        property_view.state.save()

        logger.info(f"Completed building analysis for property {property_view.property.id}: "
                   f"count={results.get('building_count', 0)}, density={results.get('building_density', 0):.2f}")

    # Analysis complete
    pipeline.set_analysis_status_to_completed()
    logger.info(f"Buildings analysis {analysis_id} completed successfully")


def _get_property_coordinates(property_view):
    """Intelligently extract latitude and longitude from property data"""
    state = property_view.state
    
    # Keywords to identify latitude/longitude fields (case-insensitive)
    lat_keywords = ['lat', 'latitude', 'y_coord', 'y_coordinate', 'northing']
    lon_keywords = ['lon', 'lng', 'long', 'longitude', 'x_coord', 'x_coordinate', 'easting']
    
    lat = None
    lon = None
    
    def _find_coordinate_field(keywords, data_dict, field_type="coordinate"):
        """Find a field containing coordinate keywords, prioritizing exact matches"""
        candidates = []
        
        for field_name, value in data_dict.items():
            if value is None:
                continue
                
            field_lower = field_name.lower()
            
            # Score fields based on keyword matches
            for keyword in keywords:
                if keyword in field_lower:
                    # Higher score for exact matches or ending with keyword
                    if field_lower == keyword or field_lower.endswith(keyword):
                        score = 100
                    elif field_lower.startswith(keyword):
                        score = 90
                    else:
                        score = 50
                    
                    try:
                        float_value = float(value)
                        # Sanity check for latitude (-90 to 90) and longitude (-180 to 180)
                        if field_type == "lat" and -90 <= float_value <= 90:
                            candidates.append((score, field_name, float_value))
                        elif field_type == "lon" and -180 <= float_value <= 180:
                            candidates.append((score, field_name, float_value))
                        elif field_type == "coordinate":  # General coordinate field
                            candidates.append((score, field_name, float_value))
                    except (ValueError, TypeError):
                        continue
                    break
        
        # Return the highest scoring candidate
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][2]  # Return the float value
        return None
    
    # Search in extra_data first (most likely location)
    if state.extra_data:
        lat = _find_coordinate_field(lat_keywords, state.extra_data, "lat")
        lon = _find_coordinate_field(lon_keywords, state.extra_data, "lon")
    
    # If not found in extra_data, check standard model fields
    if lat is None or lon is None:
        # Build dictionary of standard fields
        standard_fields = {}
        for field in state._meta.fields:
            field_name = field.name
            field_value = getattr(state, field_name, None)
            if field_value is not None:
                standard_fields[field_name] = field_value
        
        if lat is None:
            lat = _find_coordinate_field(lat_keywords, standard_fields, "lat")
        if lon is None:
            lon = _find_coordinate_field(lon_keywords, standard_fields, "lon")
    
    # Log what we found for debugging
    if lat is not None and lon is not None:
        logger.debug(f"Found coordinates for property {property_view.property.id}: lat={lat}, lon={lon}")
    elif lat is None and lon is None:
        logger.debug(f"No coordinates found for property {property_view.property.id}")
    else:
        logger.warning(f"Incomplete coordinates for property {property_view.property.id}: lat={lat}, lon={lon}")
    
    return lat, lon


def _analyze_buildings_for_coordinates(lat, lon, h3_resolution, zoom_level, links_df, max_workers):
    """Core building analysis logic adapted from the original script"""
    try:
        # Get H3 hexagon for the coordinates
        hex_index = h3.geo_to_h3(lat, lon, h3_resolution)
        hex_polygon = _get_h3_hex_polygon(hex_index)
        
        # Skip UTM CRS due to geopandas/pyproj compatibility issues
        utm_crs = None
        
        results = {
            'h3_hex': hex_index,
            'building_count': 0,
            'avg_height': None,
            'building_density': 0,
            'hex_area_km2': 0,
            'mean_setback': None
        }
        
        # If no dataset links, return basic results
        if links_df is None:
            logger.warning("No dataset links available, returning basic results")
            return results
        
        # Find quadkeys intersecting with hexagon
        quadkey_polygons = _find_quadkeys_intersecting_hex(hex_polygon, zoom_level)
        
        if not quadkey_polygons:
            logger.warning(f"No quadkeys found for hex {hex_index}")
            return results
        
        # Get URLs for quadkeys
        quadkey_urls = {}
        for qk in quadkey_polygons.keys():
            url, location = _get_url_for_quadkey(qk, links_df)
            if url:
                quadkey_urls[qk] = (url, location)
        
        if not quadkey_urls:
            logger.warning(f"No data URLs found for hex {hex_index}")
            return results
        
        # Download and analyze building data
        urls = [url for url, _ in quadkey_urls.values()]
        buildings_gdf = _download_tiles_parallel(urls, max_workers)
        
        if buildings_gdf is None or buildings_gdf.empty:
            logger.warning(f"No building data loaded for hex {hex_index}")
            return results
        
        # Filter to buildings within hexagon
        buildings_in_hex = buildings_gdf[buildings_gdf.geometry.intersects(hex_polygon)]
        
        if buildings_in_hex.empty:
            logger.info(f"No buildings found within hex {hex_index}")
            return results
        
        # Calculate metrics (without UTM CRS to avoid compatibility issues)
        building_count = len(buildings_in_hex)
        avg_height, height_count = _calculate_average_height(buildings_in_hex)
        density, area_km2 = _calculate_building_density(buildings_in_hex, hex_polygon, None)
        mean_setback = _calculate_mean_setback(buildings_in_hex, None)
        
        results.update({
            'building_count': building_count,
            'avg_height': avg_height,
            'building_density': density,
            'hex_area_km2': area_km2,
            'mean_setback': mean_setback
        })
        
        logger.info(f"Analysis complete for {hex_index}: {building_count} buildings, "
                   f"density={density:.2f}, avg_height={avg_height}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in building analysis for {lat}, {lon}: {e}")
        return {
            'error': str(e),
            'building_count': 0,
            'avg_height': None,
            'building_density': 0,
            'hex_area_km2': 0,
            'mean_setback': None,
            'h3_hex': None
        }


# Helper functions adapted from the original script
def _get_h3_hex_polygon(h3_index):
    """Get the polygon geometry for an H3 hexagon."""
    hex_boundary = h3.h3_to_geo_boundary(h3_index)
    hex_boundary = [(lon, lat) for lat, lon in hex_boundary]
    hex_boundary.append(hex_boundary[0])
    return Polygon(hex_boundary)


def _get_utm_zone(longitude, latitude):
    """Calculate the UTM zone for given coordinates."""
    # Special case for Norway
    if 56 <= latitude < 64 and 3 <= longitude < 12:
        return 32
    # Special cases for Svalbard
    if 72 <= latitude < 84:
        if 0 <= longitude < 9:
            return 31
        elif 9 <= longitude < 21:
            return 33
        elif 21 <= longitude < 33:
            return 35
        elif 33 <= longitude < 42:
            return 37
    # General case
    return int((longitude + 180) / 6) % 60 + 1


def _get_utm_crs(longitude, latitude):
    """Get the appropriate UTM CRS string for given coordinates."""
    zone = _get_utm_zone(longitude, latitude)
    epsg = 32600 + zone if latitude >= 0 else 32700 + zone
    return f"EPSG:{epsg}"


def _find_quadkeys_intersecting_hex(h3_polygon, zoom):
    """Find all quadkeys at the given zoom level that intersect with the H3 hexagon."""
    minx, miny, maxx, maxy = h3_polygon.bounds
    tiles = list(mercantile.tiles(minx, miny, maxx, maxy, zooms=[zoom]))
    
    quadkey_polygons = {}
    for tile in tiles:
        qk = mercantile.quadkey(tile)
        bounds = mercantile.bounds(tile)
        tile_poly = box(bounds.west, bounds.south, bounds.east, bounds.north)
        
        if tile_poly.intersects(h3_polygon):
            quadkey_polygons[qk] = tile_poly
    
    return quadkey_polygons


def _get_url_for_quadkey(quadkey, links_df):
    """Find the URL for a given quadkey in the dataset links CSV."""
    matching_rows = links_df[links_df["QuadKey"] == quadkey]
    if matching_rows.empty:
        return None, None
    return matching_rows.iloc[0]["Url"], matching_rows.iloc[0]["Location"]


def _get_cache_directory():
    """Get or create the cache directory for storing downloaded tiles."""
    # Use /tmp instead of ~/.cache to avoid permission issues in Docker
    cache_dir = Path("/tmp/seed_building_tiles")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_cache_filename(url):
    """Generate a unique filename for the cache based on the URL."""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')
    original_filename = path_parts[-1] if path_parts else "unknown"
    cache_filename = f"{url_hash}_{original_filename}"
    return cache_filename


def _download_and_parse_tile(url):
    """Download and parse the GeoJSONL tile data from the given URL."""
    if not url:
        return None
    
    cache_dir = _get_cache_directory()
    cache_filename = _get_cache_filename(url)
    cache_path = cache_dir / cache_filename
    
    # Check cache first
    if cache_path.exists():
        logger.debug(f"Using cached tile for {cache_filename}")
        gz_path = cache_path
    else:
        # Download if not cached
        logger.debug(f"Downloading tile from {url}")
        try:
            response = requests.get(url, stream=True, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Failed to download from {url}: HTTP {response.status_code}")
                return None
            
            with open(cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            gz_path = cache_path
            
        except Exception as e:
            logger.error(f"Error downloading {url}: {str(e)}")
            return None
    
    # Parse GeoJSONL
    buildings = []
    try:
        with gzip.open(gz_path, 'rt') as f:
            for line in f:
                if line.strip():
                    try:
                        feature = json.loads(line)
                        if feature['type'] == 'Feature':
                            properties = feature['properties']
                            geom = shape(feature['geometry'])
                            record = properties.copy()
                            record['geometry'] = geom
                            buildings.append(record)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error(f"Error parsing {gz_path}: {str(e)}")
        return None
    
    if buildings:
        gdf = gpd.GeoDataFrame(buildings, geometry='geometry')
        return gdf
    return None


def _download_tiles_parallel(urls, max_workers=4):
    """Download multiple tiles in parallel and combine them."""
    gdfs = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_download_and_parse_tile, urls))
    
    for gdf in results:
        if gdf is not None and len(gdf) > 0:
            gdfs.append(gdf)
    
    if not gdfs:
        return None
    
    combined_gdf = pd.concat(gdfs, ignore_index=True)
    return gpd.GeoDataFrame(combined_gdf, geometry='geometry')


def _calculate_average_height(gdf):
    """Calculate the average height of buildings in a GeoDataFrame."""
    if gdf is None or gdf.empty:
        return None, 0
    
    height_columns = [col for col in gdf.columns if 'height' in col.lower()]
    
    if not height_columns:
        return None, 0
    
    height_col = height_columns[0]
    has_height = gdf[pd.notnull(gdf[height_col])]
    
    if len(has_height) == 0:
        return None, 0
    
    avg_height = has_height[height_col].mean()
    return avg_height, len(has_height)


def _calculate_building_density(gdf, hex_polygon, utm_crs=None):
    """Calculate building density (buildings per km²) within a hexagon."""
    if gdf is None or gdf.empty:
        return 0, 0
    
    # Use approximate area calculation without CRS conversion
    # Calculate area using simple degree-to-meter approximation
    bounds = hex_polygon.bounds
    minx, miny, maxx, maxy = bounds
    
    # Rough conversion: 1 degree ≈ 111 km
    width_km = (maxx - minx) * 111
    height_km = (maxy - miny) * 111
    area_km2 = width_km * height_km
    
    building_count = len(gdf)
    density = building_count / area_km2 if area_km2 > 0 else 0
    
    return density, area_km2


def _calculate_mean_setback(gdf, utm_crs=None):
    """Calculate the mean neighbor setback (distance to nearest neighboring building)."""
    if gdf is None or gdf.empty or len(gdf) <= 1:
        return None
    
    # Use lat/lon directly with approximate conversion to meters
    setbacks = []
    
    for idx, building in gdf.iterrows():
        distances = []
        for other_idx, other_building in gdf.iterrows():
            if idx != other_idx:
                # Use centroids for distance calculation (buildings are polygons, not points)
                centroid1 = building.geometry.centroid
                centroid2 = other_building.geometry.centroid
                lat1, lon1 = centroid1.y, centroid1.x
                lat2, lon2 = centroid2.y, centroid2.x
                
                # Convert degree distance to approximate meters
                # 1 degree lat ≈ 111 km, 1 degree lon ≈ 111 km * cos(lat)
                import math
                dlat = (lat2 - lat1) * 111000  # meters
                dlon = (lon2 - lon1) * 111000 * math.cos(math.radians((lat1 + lat2) / 2))
                dist = math.sqrt(dlat**2 + dlon**2)
                
                if dist > 1:  # Filter out very close buildings (< 1 meter)
                    distances.append(dist)
        
        if distances:
            setbacks.append(min(distances))
    
    if setbacks:
        return sum(setbacks) / len(setbacks)
    else:
        return None


# Column creation functions
def _create_building_count_column(analysis):
    """Create a building count column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="Building Count",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Building Count",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Building Count",
                column_description="Number of buildings in H3 hexagon around property",
                data_type="number",
            )
            return column
        else:
            return None


def _create_avg_height_column(analysis):
    """Create an average height column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="Average Building Height",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Average Building Height",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Average Building Height",
                column_description="Average height of buildings in meters around property",
                data_type="number",
            )
            return column
        else:
            return None


def _create_building_density_column(analysis):
    """Create a building density column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="Building Density",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Building Density",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Building Density",
                column_description="Building density in buildings per km² around property",
                data_type="number",
            )
            return column
        else:
            return None


def _create_hex_area_column(analysis):
    """Create a hexagon area column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="Hexagon Area km2",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Hexagon Area km2",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Hexagon Area (km²)",
                column_description="Area of H3 hexagon in square kilometers",
                data_type="number",
            )
            return column
        else:
            return None


def _create_mean_setback_column(analysis):
    """Create a mean setback column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="Mean Building Setback",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Mean Building Setback",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Mean Building Setback",
                column_description="Mean distance to nearest neighboring building in meters",
                data_type="number",
            )
            return column
        else:
            return None


def _create_h3_hex_column(analysis):
    """Create an H3 hexagon ID column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="H3 Hexagon ID",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="H3 Hexagon ID",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="H3 Hexagon ID",
                column_description="H3 hexagon identifier containing the property",
                data_type="string",
            )
            return column
        else:
            return None 
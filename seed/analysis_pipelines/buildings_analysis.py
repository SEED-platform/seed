"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

Buildings Analysis - Analyzes building density, height, and setback in area around property coordinates
Optimized version with improved spatial calculations

Adrian Mungroo, 2025-07-25
"""

import logging
import os
import json
import gzip
import hashlib
import tempfile
import math
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
from scipy.spatial import cKDTree

# Try to use faster JSON parser if available
try:
    import ujson as fast_json
except ImportError:
    fast_json = json

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

    # Cache for processed hexagon results
    hex_cache = {}

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
            # Check if we've already processed this hexagon
            hex_index = h3.geo_to_h3(lat, lon, h3_resolution)
            
            if hex_index in hex_cache:
                logger.info(f"Using cached results for hex {hex_index}")
                results = hex_cache[hex_index].copy()
            else:
                # Run the actual building analysis
                logger.info(f"Dataset available: {links_df is not None}")
                if links_df is not None:
                    logger.info(f"Dataset shape: {links_df.shape}")
                
                try:
                    results = _analyze_buildings_for_coordinates(
                        lat, lon, h3_resolution, zoom_level, links_df, max_workers
                    )
                    # Cache the results for this hexagon
                    hex_cache[hex_index] = results.copy()
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


def _get_optimal_crs(lat, lon):
    """Get the optimal CRS for spatial calculations with fallback hierarchy"""
    try:
        # Try UTM first for most accurate local measurements
        utm_crs = _get_utm_crs(lon, lat)
        # Test if the CRS works
        test_point = gpd.GeoSeries([Point(lon, lat)])
        test_point.to_crs(utm_crs)
        return utm_crs
    except Exception as e:
        logger.debug(f"UTM CRS failed for {lat}, {lon}: {e}")
        try:
            # Fall back to Web Mercator for approximate meter-based calculations
            test_point = gpd.GeoSeries([Point(lon, lat)])
            test_point.to_crs('EPSG:3857')
            return 'EPSG:3857'
        except Exception as e2:
            logger.warning(f"Web Mercator also failed for {lat}, {lon}: {e2}")
            # Last resort: return None to use approximate calculations
            return None


def _analyze_buildings_for_coordinates(lat, lon, h3_resolution, zoom_level, links_df, max_workers):
    """Core building analysis logic with spatial optimizations"""
    try:
        # Get H3 hexagon for the coordinates
        hex_index = h3.geo_to_h3(lat, lon, h3_resolution)
        hex_polygon = _get_h3_hex_polygon(hex_index)
        
        # Get optimal CRS for accurate measurements
        optimal_crs = _get_optimal_crs(lat, lon)
        
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
        
        logger.info(f"Found {len(quadkey_polygons)} quadkeys for hex {hex_index}")
        
        # Get URLs for quadkeys
        quadkey_urls = {}
        for qk in quadkey_polygons.keys():
            url, location = _get_url_for_quadkey(qk, links_df)
            if url:
                quadkey_urls[qk] = (url, location)
                logger.debug(f"Found URL for quadkey {qk}: {url}")
            else:
                logger.debug(f"No URL found for quadkey {qk}")
        
        if not quadkey_urls:
            logger.warning(f"No data URLs found for hex {hex_index}")
            return results
        
        logger.info(f"Found {len(quadkey_urls)} URLs for hex {hex_index}")
        
        # Download and analyze building data
        urls = [url for url, _ in quadkey_urls.values()]
        logger.info(f"Downloading {len(urls)} tiles for hex {hex_index}")
        buildings_gdf = _download_and_process_tiles(urls, hex_polygon, optimal_crs, max_workers)
        
        if buildings_gdf is None or buildings_gdf.empty:
            logger.warning(f"No building data loaded for hex {hex_index}")
            return results
        
        logger.info(f"Successfully loaded {len(buildings_gdf)} buildings for hex {hex_index}")
        
        # Calculate metrics
        building_count = len(buildings_gdf)
        avg_height, height_count = _calculate_average_height(buildings_gdf)
        density, area_km2 = _calculate_building_density(buildings_gdf, hex_polygon, optimal_crs)
        mean_setback = _calculate_mean_setback(buildings_gdf, optimal_crs)
        
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


def _download_and_process_tiles(urls, hex_polygon, optimal_crs, max_workers=4):
    """Download tiles and process with spatial optimizations"""
    all_buildings = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Pass hex_polygon to each tile download for early filtering
        tile_results = list(executor.map(lambda url: _download_and_parse_tile(url, hex_polygon), urls))
    
    # Process each tile incrementally with spatial filtering
    for tile_gdf in tile_results:
        if tile_gdf is not None and not tile_gdf.empty:
            # Apply spatial index for efficient intersection
            if hasattr(tile_gdf, 'sindex'):
                # Use spatial index for fast filtering
                possible_matches_index = list(tile_gdf.sindex.intersection(hex_polygon.bounds))
                if possible_matches_index:
                    possible_matches = tile_gdf.iloc[possible_matches_index]
                    buildings_in_hex = possible_matches[possible_matches.geometry.intersects(hex_polygon)]
                else:
                    buildings_in_hex = gpd.GeoDataFrame()
            else:
                # Fallback to basic intersection
                buildings_in_hex = tile_gdf[tile_gdf.geometry.intersects(hex_polygon)]
            
            if not buildings_in_hex.empty:
                # Pre-compute geometric properties for optimization
                buildings_in_hex = buildings_in_hex.copy()
                buildings_in_hex['centroid'] = buildings_in_hex.geometry.centroid
                
                # Convert to optimal CRS if available
                if optimal_crs:
                    try:
                        buildings_in_hex = buildings_in_hex.to_crs(optimal_crs)
                        buildings_in_hex['centroid_projected'] = buildings_in_hex['centroid'].to_crs(optimal_crs)
                    except Exception as e:
                        logger.debug(f"CRS conversion failed: {e}")
                        buildings_in_hex['centroid_projected'] = buildings_in_hex['centroid']
                else:
                    buildings_in_hex['centroid_projected'] = buildings_in_hex['centroid']
                
                all_buildings.append(buildings_in_hex)
    
    if not all_buildings:
        return None
    
    # Combine all building data
    combined_gdf = pd.concat(all_buildings, ignore_index=True)
    return gpd.GeoDataFrame(combined_gdf, geometry='geometry')


def _calculate_building_density(gdf, hex_polygon, optimal_crs=None):
    """Calculate building density with proper area calculation"""
    if gdf is None or gdf.empty:
        return 0, 0
    
    building_count = len(gdf)
    
    # Calculate area using optimal method
    if optimal_crs:
        try:
            # Use projected CRS for accurate area calculation
            hex_gdf = gpd.GeoDataFrame([1], geometry=[hex_polygon])
            hex_projected = hex_gdf.to_crs(optimal_crs)
            area_m2 = hex_projected.geometry.area.iloc[0]
            area_km2 = area_m2 / 1_000_000  # Convert to km²
        except Exception as e:
            logger.debug(f"Projected area calculation failed: {e}")
            area_km2 = _calculate_approximate_area_km2(hex_polygon)
    else:
        # Use H3 built-in area calculation (most accurate for H3 hexagons)
        try:
            # This requires the hex index, which we can derive from the polygon
            # For now, use approximate calculation
            area_km2 = _calculate_approximate_area_km2(hex_polygon)
        except:
            area_km2 = _calculate_approximate_area_km2(hex_polygon)
    
    density = building_count / area_km2 if area_km2 > 0 else 0
    return density, area_km2


def _calculate_approximate_area_km2(polygon):
    """Calculate approximate area using simple degree-to-km conversion"""
    bounds = polygon.bounds
    minx, miny, maxx, maxy = bounds
    
    # Rough conversion: 1 degree ≈ 111 km
    width_km = (maxx - minx) * 111
    height_km = (maxy - miny) * 111
    area_km2 = width_km * height_km
    
    return area_km2


def _calculate_mean_setback(gdf, optimal_crs=None):
    """Calculate mean setback using spatial data structures for O(n log n) complexity"""
    if gdf is None or gdf.empty or len(gdf) <= 1:
        return None
    
    try:
        # Use projected coordinates if available for more accurate distances
        if optimal_crs and 'centroid_projected' in gdf.columns:
            centroids = np.array([(geom.x, geom.y) for geom in gdf['centroid_projected']])
        else:
            # Convert lat/lon to approximate meters
            centroids = np.array([
                (_lon_to_meters(geom.x, geom.y), _lat_to_meters(geom.y)) 
                for geom in gdf['centroid']
            ])
        
        if len(centroids) < 2:
            return None
        
        # Use scipy's cKDTree for efficient nearest neighbor search
        tree = cKDTree(centroids)
        
        # Find the nearest neighbor for each building (k=2 to exclude self)
        distances, indices = tree.query(centroids, k=2)
        
        # Extract nearest neighbor distances (second column)
        nearest_distances = distances[:, 1]
        
        # Filter out very close buildings (< 1 meter) which might be data errors
        valid_distances = nearest_distances[nearest_distances > 1.0]
        
        if len(valid_distances) > 0:
            return float(np.mean(valid_distances))
        else:
            return None
            
    except Exception as e:
        logger.debug(f"Optimized setback calculation failed: {e}")
        # Fallback to basic calculation for small datasets
        return _calculate_mean_setback_basic(gdf)


def _calculate_mean_setback_basic(gdf):
    """Fallback basic setback calculation"""
    if gdf is None or gdf.empty or len(gdf) <= 1:
        return None
    
    setbacks = []
    
    for idx, building in gdf.iterrows():
        distances = []
        centroid1 = building.geometry.centroid
        
        for other_idx, other_building in gdf.iterrows():
            if idx != other_idx:
                centroid2 = other_building.geometry.centroid
                lat1, lon1 = centroid1.y, centroid1.x
                lat2, lon2 = centroid2.y, centroid2.x
                
                # Convert degree distance to approximate meters
                dlat = (lat2 - lat1) * 111000  # meters
                dlon = (lon2 - lon1) * 111000 * math.cos(math.radians((lat1 + lat2) / 2))
                dist = math.sqrt(dlat**2 + dlon**2)
                
                if dist > 1:  # Filter out very close buildings
                    distances.append(dist)
        
        if distances:
            setbacks.append(min(distances))
    
    return sum(setbacks) / len(setbacks) if setbacks else None


def _lon_to_meters(lon, lat):
    """Convert longitude to approximate meters"""
    return lon * 111000 * math.cos(math.radians(lat))


def _lat_to_meters(lat):
    """Convert latitude to approximate meters"""
    return lat * 111000


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


def _download_and_parse_tile(url, hex_polygon=None):
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
    
    # Parse GeoJSONL with early filtering
    buildings = []
    hex_bounds = hex_polygon.bounds if hex_polygon is not None else None
    
    try:
        with gzip.open(gz_path, 'rt') as f:
            for line in f:
                if line.strip():
                    try:
                        feature = fast_json.loads(line)
                        if feature['type'] == 'Feature':
                            # Early bounding box check to skip buildings outside hexagon
                            if hex_bounds:
                                geom_type = feature['geometry']['type']
                                coords = feature['geometry']['coordinates']
                                
                                # Handle different geometry types
                                if geom_type == 'Polygon':
                                    # For polygons, use the outer ring coordinates
                                    ring_coords = coords[0]
                                elif geom_type == 'MultiPolygon':
                                    # For multipolygons, flatten all outer rings
                                    ring_coords = [coord for poly in coords for coord in poly[0]]
                                elif geom_type == 'Point':
                                    # For points, use single coordinate
                                    ring_coords = [coords]
                                else:
                                    # For other types, skip early filtering
                                    ring_coords = None
                                
                                if ring_coords:
                                    # Quick bounds check before full geometry parsing
                                    min_x = min(coord[0] for coord in ring_coords)
                                    max_x = max(coord[0] for coord in ring_coords)
                                    min_y = min(coord[1] for coord in ring_coords)
                                    max_y = max(coord[1] for coord in ring_coords)
                                    
                                    # Skip if building is completely outside hexagon bounds
                                    if (max_x < hex_bounds[0] or min_x > hex_bounds[2] or 
                                        max_y < hex_bounds[1] or min_y > hex_bounds[3]):
                                        continue
                            
                            properties = feature['properties']
                            geom = shape(feature['geometry'])
                            record = properties.copy()
                            record['geometry'] = geom
                            buildings.append(record)
                    except (json.JSONDecodeError, ValueError):
                        continue
    except Exception as e:
        logger.error(f"Error parsing {gz_path}: {str(e)}")
        return None
    
    if buildings:
        gdf = gpd.GeoDataFrame(buildings, geometry='geometry')
        return gdf
    return None


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
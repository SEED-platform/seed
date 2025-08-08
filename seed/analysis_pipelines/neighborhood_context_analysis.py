"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

Neighborhood Context Analysis - Analyzes building count, height, density, and setback
around property coordinates (neighborhood context). Optimized spatial calculations.

Originally authored as Buildings Analysis; renamed to Neighborhood Context Analysis.
"""

import logging
import os
import json
import gzip
import hashlib
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


class NeighborhoodContextAnalysisPipeline(AnalysisPipeline):
    def _prepare_analysis(self, property_view_ids, start_analysis=True):
        """Prepare the neighborhood context analysis"""

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
    """Finish preparation for neighborhood context analysis"""
    pipeline = NeighborhoodContextAnalysisPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready("Ready to run Neighborhood Context Analysis")

    return list(analysis_view_ids_by_property_view_id.values())


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, analysis_property_view_ids, analysis_id):
    """Run the neighborhood context analysis - analyzes building data around property coordinates"""
    pipeline = NeighborhoodContextAnalysisPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Analyzing neighborhood building context around property coordinates.")

    analysis = Analysis.objects.get(id=analysis_id)
    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)

    # Create the neighborhood context columns if they don't exist
    building_count_column = _create_neighborhood_building_count_column(analysis)
    avg_height_column = _create_neighborhood_avg_height_column(analysis)
    building_density_column = _create_neighborhood_building_density_column(analysis)
    mean_setback_column = _create_neighborhood_mean_setback_column(analysis)

    # Configuration parameters
    h3_resolution = analysis.configuration.get('h3_resolution', 8)
    zoom_level = analysis.configuration.get('zoom_level', 9)
    max_workers = analysis.configuration.get('max_workers', 4)

    logger.info(f"Processing {len(analysis_property_views)} properties for neighborhood context analysis")
    logger.info(f"Using H3 resolution: {h3_resolution}, Zoom level: {zoom_level}")

    # Load dataset links if available
    dataset_path = analysis.configuration.get('dataset_path', '/seed/dataset-links.csv')
    links_df = None

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
            results = {
                'error': 'No coordinates available',
                'building_count': 0,
                'avg_height': None,
                'building_density': 0,
                'mean_setback': None,
            }
        else:
            # Check if we've already processed this hexagon
            hex_index = h3.geo_to_h3(lat, lon, h3_resolution)

            if hex_index in hex_cache:
                logger.info(f"Using cached results for hex {hex_index}")
                results = hex_cache[hex_index].copy()
            else:
                logger.info(f"Dataset available: {links_df is not None}")
                if links_df is not None:
                    logger.info(f"Dataset shape: {links_df.shape}")

                try:
                    results = _analyze_buildings_for_coordinates(
                        lat, lon, h3_resolution, zoom_level, links_df, max_workers
                    )
                    # Cache the results for this hexagon
                    hex_cache[hex_index] = results.copy()
                    logger.info(f"Neighborhood context analysis completed for property {property_view.property.id}")
                except Exception as e:
                    logger.error(f"Error in neighborhood context analysis for property {property_view.property.id}: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    results = {
                        'error': f'Neighborhood context analysis failed: {str(e)}',
                        'building_count': 0,
                        'avg_height': None,
                        'building_density': 0,
                        'mean_setback': None,
                    }

        # Store results in analysis record
        analysis_property_view.parsed_results = {
            'building_count': results.get('building_count', 0),
            'avg_height': results.get('avg_height'),
            'building_density': results.get('building_density', 0),
            'mean_setback': results.get('mean_setback'),
        }

        # Save to PropertyState extra_data using proper neighborhood column names
        if building_count_column:
            property_view.state.extra_data[building_count_column.column_name] = results.get('building_count', 0)
        if avg_height_column:
            property_view.state.extra_data[avg_height_column.column_name] = results.get('avg_height')
        if building_density_column:
            property_view.state.extra_data[building_density_column.column_name] = results.get('building_density', 0)
        if mean_setback_column:
            property_view.state.extra_data[mean_setback_column.column_name] = results.get('mean_setback')

        analysis_property_view.save()
        property_view.state.save()

        logger.info(
            f"Completed neighborhood context analysis for property {property_view.property.id}: "
            f"count={results.get('building_count', 0)}, density={results.get('building_density', 0):.2f}"
        )

    # Analysis complete
    pipeline.set_analysis_status_to_completed()
    logger.info(f"Neighborhood context analysis {analysis_id} completed successfully")


def _get_property_coordinates(property_view):
    """Intelligently extract latitude and longitude from property data"""
    state = property_view.state

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

            for keyword in keywords:
                if keyword in field_lower:
                    if field_lower == keyword or field_lower.endswith(keyword):
                        score = 100
                    elif field_lower.startswith(keyword):
                        score = 90
                    else:
                        score = 50

                    try:
                        float_value = float(value)
                        if field_type == "lat" and -90 <= float_value <= 90:
                            candidates.append((score, field_name, float_value))
                        elif field_type == "lon" and -180 <= float_value <= 180:
                            candidates.append((score, field_name, float_value))
                        elif field_type == "coordinate":
                            candidates.append((score, field_name, float_value))
                    except (ValueError, TypeError):
                        continue
                    break

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][2]
        return None

    if state.extra_data:
        lat = _find_coordinate_field(lat_keywords, state.extra_data, "lat")
        lon = _find_coordinate_field(lon_keywords, state.extra_data, "lon")

    if lat is None or lon is None:
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
        utm_crs = _get_utm_crs(lon, lat)
        test_point = gpd.GeoSeries([Point(lon, lat)])
        test_point.to_crs(utm_crs)
        return utm_crs
    except Exception as e:
        logger.debug(f"UTM CRS failed for {lat}, {lon}: {e}")
        try:
            test_point = gpd.GeoSeries([Point(lon, lat)])
            test_point.to_crs('EPSG:3857')
            return 'EPSG:3857'
        except Exception as e2:
            logger.warning(f"Web Mercator also failed for {lat}, {lon}: {e2}")
            return None


def _analyze_buildings_for_coordinates(lat, lon, h3_resolution, zoom_level, links_df, max_workers):
    """Core neighborhood context analysis logic with spatial optimizations"""
    try:
        hex_index = h3.geo_to_h3(lat, lon, h3_resolution)
        hex_polygon = _get_h3_hex_polygon(hex_index)

        optimal_crs = _get_optimal_crs(lat, lon)

        results = {
            'building_count': 0,
            'avg_height': None,
            'building_density': 0,
            'mean_setback': None,
        }

        if links_df is None:
            logger.warning("No dataset links available, returning basic results")
            return results

        quadkey_polygons = _find_quadkeys_intersecting_hex(hex_polygon, zoom_level)

        if not quadkey_polygons:
            logger.warning("No quadkeys found for hex intersection")
            return results

        logger.info(f"Found {len(quadkey_polygons)} quadkeys for hex")

        quadkey_urls = {}
        for qk in quadkey_polygons.keys():
            url, location = _get_url_for_quadkey(qk, links_df)
            if url:
                quadkey_urls[qk] = (url, location)
                logger.debug(f"Found URL for quadkey {qk}: {url}")

        if not quadkey_urls:
            logger.warning("No data URLs found for hex")
            return results

        logger.info(f"Found {len(quadkey_urls)} URLs for hex")

        urls = [url for url, _ in quadkey_urls.values()]
        logger.info("Downloading tiles for hex")
        buildings_gdf = _download_and_process_tiles(urls, hex_polygon, optimal_crs, max_workers)

        if buildings_gdf is None or buildings_gdf.empty:
            logger.warning("No building data loaded for hex")
            return results

        logger.info(f"Successfully loaded {len(buildings_gdf)} buildings for hex")

        building_count = len(buildings_gdf)
        avg_height, height_count = _calculate_average_height(buildings_gdf)
        density, area_km2 = _calculate_building_density(buildings_gdf, hex_polygon, optimal_crs)
        mean_setback = _calculate_mean_setback(buildings_gdf, optimal_crs)

        results.update({
            'building_count': building_count,
            'avg_height': avg_height,
            'building_density': density,
            'mean_setback': mean_setback
        })

        logger.info(
            f"Analysis complete for hex: {building_count} buildings, "
            f"density={density:.2f}, avg_height={avg_height}"
        )

        return results

    except Exception as e:
        logger.error(f"Error in neighborhood context analysis for {lat}, {lon}: {e}")
        return {
            'error': str(e),
            'building_count': 0,
            'avg_height': None,
            'building_density': 0,
            'mean_setback': None,
        }


def _download_and_process_tiles(urls, hex_polygon, optimal_crs, max_workers=4):
    """Download tiles and process with spatial optimizations"""
    all_buildings = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tile_results = list(executor.map(lambda url: _download_and_parse_tile(url, hex_polygon), urls))

    for tile_gdf in tile_results:
        if tile_gdf is not None and not tile_gdf.empty:
            if hasattr(tile_gdf, 'sindex'):
                possible_matches_index = list(tile_gdf.sindex.intersection(hex_polygon.bounds))
                if possible_matches_index:
                    possible_matches = tile_gdf.iloc[possible_matches_index]
                    buildings_in_hex = possible_matches[possible_matches.geometry.intersects(hex_polygon)]
                else:
                    buildings_in_hex = gpd.GeoDataFrame()
            else:
                buildings_in_hex = tile_gdf[tile_gdf.geometry.intersects(hex_polygon)]

            if not buildings_in_hex.empty:
                buildings_in_hex = buildings_in_hex.copy()
                buildings_in_hex['centroid'] = buildings_in_hex.geometry.centroid

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

    combined_gdf = pd.concat(all_buildings, ignore_index=True)
    return gpd.GeoDataFrame(combined_gdf, geometry='geometry')


def _calculate_building_density(gdf, hex_polygon, optimal_crs=None):
    """Calculate building density with proper area calculation"""
    if gdf is None or gdf.empty:
        return 0, 0

    building_count = len(gdf)

    if optimal_crs:
        try:
            hex_gdf = gpd.GeoDataFrame([1], geometry=[hex_polygon])
            hex_projected = hex_gdf.to_crs(optimal_crs)
            area_m2 = hex_projected.geometry.area.iloc[0]
            area_km2 = area_m2 / 1_000_000
        except Exception as e:
            logger.debug(f"Projected area calculation failed: {e}")
            area_km2 = _calculate_approximate_area_km2(hex_polygon)
    else:
        try:
            area_km2 = _calculate_approximate_area_km2(hex_polygon)
        except Exception:
            area_km2 = _calculate_approximate_area_km2(hex_polygon)

    density = building_count / area_km2 if area_km2 > 0 else 0
    return density, area_km2


def _calculate_approximate_area_km2(polygon):
    """Calculate approximate area using simple degree-to-km conversion"""
    bounds = polygon.bounds
    minx, miny, maxx, maxy = bounds

    width_km = (maxx - minx) * 111
    height_km = (maxy - miny) * 111
    area_km2 = width_km * height_km

    return area_km2


def _calculate_mean_setback(gdf, optimal_crs=None):
    """Calculate mean setback using spatial data structures for O(n log n) complexity"""
    if gdf is None or gdf.empty or len(gdf) <= 1:
        return None

    try:
        if optimal_crs and 'centroid_projected' in gdf.columns:
            centroids = np.array([(geom.x, geom.y) for geom in gdf['centroid_projected']])
        else:
            centroids = np.array([
                (_lon_to_meters(geom.x, geom.y), _lat_to_meters(geom.y))
                for geom in gdf['centroid']
            ])

        if len(centroids) < 2:
            return None

        tree = cKDTree(centroids)
        distances, indices = tree.query(centroids, k=2)
        nearest_distances = distances[:, 1]
        valid_distances = nearest_distances[nearest_distances > 1.0]

        if len(valid_distances) > 0:
            return float(np.mean(valid_distances))
        else:
            return None

    except Exception as e:
        logger.debug(f"Optimized setback calculation failed: {e}")
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

                dlat = (lat2 - lat1) * 111000
                dlon = (lon2 - lon1) * 111000 * math.cos(math.radians((lat1 + lat2) / 2))
                dist = math.sqrt(dlat**2 + dlon**2)

                if dist > 1:
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


# Helper functions
def _get_h3_hex_polygon(h3_index):
    """Get the polygon geometry for an H3 hexagon."""
    hex_boundary = h3.h3_to_geo_boundary(h3_index)
    hex_boundary = [(lon, lat) for lat, lon in hex_boundary]
    hex_boundary.append(hex_boundary[0])
    return Polygon(hex_boundary)


def _get_utm_zone(longitude, latitude):
    """Calculate the UTM zone for given coordinates."""
    if 56 <= latitude < 64 and 3 <= longitude < 12:
        return 32
    if 72 <= latitude < 84:
        if 0 <= longitude < 9:
            return 31
        elif 9 <= longitude < 21:
            return 33
        elif 21 <= longitude < 33:
            return 35
        elif 33 <= longitude < 42:
            return 37
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

    if cache_path.exists():
        logger.debug(f"Using cached tile for {cache_filename}")
        gz_path = cache_path
    else:
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

    buildings = []
    hex_bounds = hex_polygon.bounds if hex_polygon is not None else None

    try:
        with gzip.open(gz_path, 'rt') as f:
            for line in f:
                if line.strip():
                    try:
                        feature = fast_json.loads(line)
                        if feature['type'] == 'Feature':
                            if hex_bounds:
                                geom_type = feature['geometry']['type']
                                coords = feature['geometry']['coordinates']

                                if geom_type == 'Polygon':
                                    ring_coords = coords[0]
                                elif geom_type == 'MultiPolygon':
                                    ring_coords = [coord for poly in coords for coord in poly[0]]
                                elif geom_type == 'Point':
                                    ring_coords = [coords]
                                else:
                                    ring_coords = None

                                if ring_coords:
                                    min_x = min(coord[0] for coord in ring_coords)
                                    max_x = max(coord[0] for coord in ring_coords)
                                    min_y = min(coord[1] for coord in ring_coords)
                                    max_y = max(coord[1] for coord in ring_coords)

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


# Column creation functions (Neighborhood-prefixed)
def _create_neighborhood_building_count_column(analysis):
    """Create a neighborhood building count column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="Neighborhood Building Count",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Neighborhood Building Count",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Neighborhood Building Count",
                column_description="Number of buildings in the neighborhood context",
                data_type="number",
            )
            return column
        else:
            return None


def _create_neighborhood_avg_height_column(analysis):
    """Create a neighborhood average height column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="Neighborhood Avg Building Height",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Neighborhood Avg Building Height",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Neighborhood Avg Building Height",
                column_description="Average height of buildings in meters in the neighborhood context",
                data_type="number",
            )
            return column
        else:
            return None


def _create_neighborhood_building_density_column(analysis):
    """Create a neighborhood building density column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="Neighborhood Building Density",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Neighborhood Building Density",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Neighborhood Building Density",
                column_description="Building density (buildings per km²) in the neighborhood context",
                data_type="number",
            )
            return column
        else:
            return None


def _create_neighborhood_mean_setback_column(analysis):
    """Create a neighborhood mean setback column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="Neighborhood Mean Building Setback",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Column.DoesNotExist:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Neighborhood Mean Building Setback",
                organization=analysis.organization,
                table_name="PropertyState",
                display_name="Neighborhood Mean Building Setback",
                column_description="Mean distance to nearest neighboring building in meters (neighborhood context)",
                data_type="number",
            )
            return column
        else:
            return None



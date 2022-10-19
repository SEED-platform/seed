# !/usr/bin/env python
# encoding: utf-8

import logging

from buildingid.code import decode
from django.contrib.gis.geos import GEOSGeometry

_log = logging.getLogger(__name__)


def centroid_wkt(state):
    """
    This translates GIS data saved as binary (WKB) into a text string (WKT).
    """
    if state.centroid:
        return GEOSGeometry(state.centroid, srid=4326).wkt


def decode_unique_ids(qs):
    # import here to prevent circular reference
    from seed.models.properties import PropertyState
    from seed.models.tax_lots import TaxLotState

    if len(qs) == 0:
        return True

    if isinstance(qs.first(), PropertyState):
        filtered_qs = qs.exclude(ubid__isnull=True)
        unique_id = 'ubid'
    elif isinstance(qs.first(), TaxLotState):
        filtered_qs = qs.exclude(ulid__isnull=True)
        unique_id = 'ulid'
    else:
        return False

    for item in filtered_qs.iterator():
        try:
            bounding_box_obj = decode(getattr(item, unique_id))
        except ValueError:
            _log.error(f'Could not decode UBID of {getattr(item, unique_id)}')
            continue  # property with an incorrectly formatted UBID/ULID is skipped

        # Starting with the SE point, list the points in counter-clockwise order
        bounding_box_polygon = (
            f"POLYGON (({bounding_box_obj.longitudeHi} {bounding_box_obj.latitudeLo}, "
            f"{bounding_box_obj.longitudeHi} {bounding_box_obj.latitudeHi}, "
            f"{bounding_box_obj.longitudeLo} {bounding_box_obj.latitudeHi}, "
            f"{bounding_box_obj.longitudeLo} {bounding_box_obj.latitudeLo}, "
            f"{bounding_box_obj.longitudeHi} {bounding_box_obj.latitudeLo}))"
        )
        item.bounding_box = bounding_box_polygon

        # Starting with the SE point, list the points in counter-clockwise order
        centroid_polygon = (
            f"POLYGON (({bounding_box_obj.centroid.longitudeHi} {bounding_box_obj.centroid.latitudeLo}, "
            f"{bounding_box_obj.centroid.longitudeHi} {bounding_box_obj.centroid.latitudeHi}, "
            f"{bounding_box_obj.centroid.longitudeLo} {bounding_box_obj.centroid.latitudeHi}, "
            f"{bounding_box_obj.centroid.longitudeLo} {bounding_box_obj.centroid.latitudeLo}, "
            f"{bounding_box_obj.centroid.longitudeHi} {bounding_box_obj.centroid.latitudeLo}))"
        )
        item.centroid = centroid_polygon

        item.latitude, item.longitude = bounding_box_obj.latlng()

        item.save()

# !/usr/bin/env python
# encoding: utf-8

import buildingid.v2
import buildingid.v3
from django.contrib.gis.geos import GEOSGeometry


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
            bounding_box_obj = buildingid.v3.decode(getattr(item, unique_id))
        except ValueError:
            try:
                bounding_box_obj = buildingid.v2.decode(getattr(item, unique_id))
            except ValueError:
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
            f"POLYGON (({bounding_box_obj.child.longitudeHi} {bounding_box_obj.child.latitudeLo}, "
            f"{bounding_box_obj.child.longitudeHi} {bounding_box_obj.child.latitudeHi}, "
            f"{bounding_box_obj.child.longitudeLo} {bounding_box_obj.child.latitudeHi}, "
            f"{bounding_box_obj.child.longitudeLo} {bounding_box_obj.child.latitudeLo}, "
            f"{bounding_box_obj.child.longitudeHi} {bounding_box_obj.child.latitudeLo}))"
        )
        item.centroid = centroid_polygon

        item.latitude, item.longitude = bounding_box_obj.latlng()

        item.save()

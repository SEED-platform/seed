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


def decode_ubids(qs):
    filtered_qs = qs.exclude(ubid__isnull=True)

    for property in filtered_qs.iterator():
        try:
            bounding_box_obj = buildingid.v3.decode(property.ubid)
        except ValueError:
            try:
                bounding_box_obj = buildingid.v2.decode(property.ubid)
            except ValueError:
                continue  # property with an incorrectly formatted UBID is skipped

        # Starting with the SE point, list the points in counter-clockwise order
        bounding_box_polygon = (
            f"POLYGON (({bounding_box_obj.longitudeHi} {bounding_box_obj.latitudeLo}, "
            f"{bounding_box_obj.longitudeHi} {bounding_box_obj.latitudeHi}, "
            f"{bounding_box_obj.longitudeLo} {bounding_box_obj.latitudeHi}, "
            f"{bounding_box_obj.longitudeLo} {bounding_box_obj.latitudeLo}, "
            f"{bounding_box_obj.longitudeHi} {bounding_box_obj.latitudeLo}))"
        )
        property.bounding_box = bounding_box_polygon

        # Starting with the SE point, list the points in counter-clockwise order
        centroid_polygon = (
            f"POLYGON (({bounding_box_obj.child.longitudeHi} {bounding_box_obj.child.latitudeLo}, "
            f"{bounding_box_obj.child.longitudeHi} {bounding_box_obj.child.latitudeHi}, "
            f"{bounding_box_obj.child.longitudeLo} {bounding_box_obj.child.latitudeHi}, "
            f"{bounding_box_obj.child.longitudeLo} {bounding_box_obj.child.latitudeLo}, "
            f"{bounding_box_obj.child.longitudeHi} {bounding_box_obj.child.latitudeLo}))"
        )
        property.centroid = centroid_polygon

        property.save()

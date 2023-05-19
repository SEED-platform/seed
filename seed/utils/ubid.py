# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import logging

from buildingid.code import decode
from django.contrib.gis.geos import GEOSGeometry
from django.db import connection

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

    if not isinstance(qs.first(), (PropertyState, TaxLotState)):
        return False

    filtered_qs = qs.exclude(ubid__isnull=True)

    for item in filtered_qs.iterator():
        try:
            bounding_box_obj = decode(getattr(item, 'ubid'))
        except ValueError:
            _log.error(f'Could not decode UBID of {getattr(item, "ubid")}')
            continue  # property with an incorrectly formatted UBID is skipped

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


def get_jaccard_index(ubid1, ubid2):
    """
    Calculates the Jaccard index given 2 property_state.ubid's

    The Jaccard index is a value between zero and one. The Jaccard index is the area of the intersection divided by the intersection of the union.
    Not a Match (0.0) <-----> (1.0) Perfect Match

    @param ubid1 [text] A Property State Ubid
    @param ubid2 [text] A Property State Ubid
    @return [numeric] The Jaccard index.
    """
    if ubid1 == ubid2:
        return 1.0

    if not validate_ubid(ubid1) or not validate_ubid(ubid2):
        return 0.0

    sql = """ WITH decoded AS (
                SELECT
                    public.UBID_Decode(%s) AS left_code_area,
                    public.UBID_Decode(%s) AS right_code_area
            )
            SELECT
                public.UBID_CodeArea_Jaccard(left_code_area, right_code_area)
            FROM
                decoded """

    with connection.cursor() as cursor:
        cursor.execute(sql, [ubid1, ubid2])
        result = cursor.fetchone()[0]
    return result


def validate_ubid(ubid):
    """
    Check if the code is valid
    PARAMETERS
    code text // a pluscode
    EXAMPLE
    select pluscode_isvalid('XX5JJC23+00')

    @param ubid [text] A Property State Ubid
    @return [bool] Ubid validity.
    """

    parts = ubid.split('-')
    sql = """ SELECT public.pluscode_isvalid(%s) """

    with connection.cursor() as cursor:
        cursor.execute(sql, [parts[0]])
        result = cursor.fetchone()[0]
    return result

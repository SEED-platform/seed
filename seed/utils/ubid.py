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


# Decode UBIDs from queryset or individual PropertyState/TaxLotState
def decode_unique_ids(qs):
    # import here to prevent circular reference
    from seed.models.properties import PropertyState
    from seed.models.tax_lots import TaxLotState

    # Turn individual states back into queryset
    if isinstance(qs, PropertyState):
        qs = PropertyState.objects.filter(id=qs.id)
    elif isinstance(qs, TaxLotState):
        qs = TaxLotState.objects.filter(id=qs.id)

    if len(qs) == 0:
        return True

    if not isinstance(qs.first(), (PropertyState, TaxLotState)):
        return False

    filtered_qs = qs.exclude(ubid__isnull=True)

    for state in filtered_qs.iterator():
        try:
            bounding_box_obj = decode(getattr(state, 'ubid'))
        except ValueError:
            _log.error(f"Could not decode UBID '{getattr(state, 'ubid')}'")
            continue  # state with an incorrectly formatted UBID is skipped

        # Starting with the SE point, list the points in counter-clockwise order
        bounding_box_polygon = (
            f"POLYGON (({bounding_box_obj.longitudeHi} {bounding_box_obj.latitudeLo}, "
            f"{bounding_box_obj.longitudeHi} {bounding_box_obj.latitudeHi}, "
            f"{bounding_box_obj.longitudeLo} {bounding_box_obj.latitudeHi}, "
            f"{bounding_box_obj.longitudeLo} {bounding_box_obj.latitudeLo}, "
            f"{bounding_box_obj.longitudeHi} {bounding_box_obj.latitudeLo}))"
        )
        state.bounding_box = bounding_box_polygon

        # Starting with the SE point, list the points in counter-clockwise order
        centroid_polygon = (
            f"POLYGON (({bounding_box_obj.centroid.longitudeHi} {bounding_box_obj.centroid.latitudeLo}, "
            f"{bounding_box_obj.centroid.longitudeHi} {bounding_box_obj.centroid.latitudeHi}, "
            f"{bounding_box_obj.centroid.longitudeLo} {bounding_box_obj.centroid.latitudeHi}, "
            f"{bounding_box_obj.centroid.longitudeLo} {bounding_box_obj.centroid.latitudeLo}, "
            f"{bounding_box_obj.centroid.longitudeHi} {bounding_box_obj.centroid.latitudeLo}))"
        )
        state.centroid = centroid_polygon

        state.latitude, state.longitude = bounding_box_obj.latlng()

        state.save()


def get_jaccard_index(ubid1, ubid2):
    """
    Calculates the Jaccard index given two UBIDs

    The Jaccard index is a value between zero and one, representing the area of the intersection divided by the area of the union.
    Not a Match (0.0) <-----> (1.0) Perfect Match

    @param ubid1 [text] A Property State Ubid
    @param ubid2 [text] A Property State Ubid
    @return [numeric] The Jaccard index.
    """
    if (not ubid1 or not ubid2) or (ubid1 == ubid2):
        return 1.0

    if not validate_ubid(ubid1) or not validate_ubid(ubid2):
        return 0.0

    sql = """ WITH decoded AS (
                SELECT
                    UBID_Decode(%s) AS left_code_area,
                    UBID_Decode(%s) AS right_code_area
            )
            SELECT
                UBID_CodeArea_Jaccard(left_code_area, right_code_area)
            FROM
                decoded """

    with connection.cursor() as cursor:
        cursor.execute(sql, [ubid1, ubid2])
        result = cursor.fetchone()[0]
    return result


def validate_ubid(ubid):
    """
    Check if the code is valid

    EXAMPLE
    SELECT pluscode_isvalid('XX5JJC23+00')

    @param ubid [text] A Property or TaxLot State Ubid
    @return [bool] Ubid validity.
    """
    if not ubid:
        return False

    parts = ubid.split('-')
    sql = """ SELECT pluscode_isvalid(%s) """

    with connection.cursor() as cursor:
        cursor.execute(sql, [parts[0]])
        result = cursor.fetchone()[0]
    return result


def merge_ubid_models(old_state_ids, new_state_id, StateClass):
    """
    Given a list of old (existing) property states, merge the existing ubid_models onto the new state

    If the new_state has an equivalent ubid, skip it.
    """
    old_states = StateClass.objects.filter(id__in=old_state_ids).order_by('-id')
    new_state = StateClass.objects.get(id=new_state_id)
    new_ubids = new_state.ubidmodel_set.all()
    state_field = 'property' if StateClass.__name__ == 'PropertyState' else 'taxlot'

    preferred_ubid = find_preferred(old_states, new_state)

    for old_state in old_states:
        for old_ubid in old_state.ubidmodel_set.all():
            if old_ubid.ubid in new_ubids.values_list('ubid', flat=True):
                continue

            ubid_details = {
                'ubid': old_ubid.ubid,
                state_field: new_state,
                'preferred': old_ubid.ubid == preferred_ubid
            }

            new_state.ubidmodel_set.create(**ubid_details)

    new_state.save()

    if preferred_ubid:
        state_qs = StateClass.objects.filter(id=new_state.id)
        decode_unique_ids(state_qs)
        new_state.refresh_from_db()

    return new_state


def find_preferred(old_states, new_state):
    # The preferred ubid will be the first prefered ubid founnd on a list of states.
    # Where new_state is priority, and old_states[0] is least priority
    ordered_states = list(old_states)
    ordered_states.insert(0, new_state)

    preferred_ubid = None
    for state in ordered_states:
        ubid = state.ubidmodel_set.filter(preferred=True).first()
        if ubid:
            preferred_ubid = ubid.ubid
            break

    return preferred_ubid

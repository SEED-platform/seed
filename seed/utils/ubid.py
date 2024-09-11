# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
import re

from buildingid.code import Code, decode
from django.contrib.gis.geos import GEOSGeometry

_log = logging.getLogger(__name__)

PLUSCODE_SEPARATOR = "+"
PLUSCODE_PADDING_CHAR = "0"
PLUSCODE_ALPHABET_PATTERN = re.compile(f"^[23456789CFGHJMPQRVWX{PLUSCODE_SEPARATOR}{PLUSCODE_PADDING_CHAR}]+$")
UBID_OFFSET_PATTERN = re.compile(r"^(?:-(?:0|[1-9][0-9]*)){4}$")


def centroid_wkt(state):
    """
    This translates GIS data saved as binary (WKB) into a text string (WKT).
    """
    if state.centroid:
        return GEOSGeometry(state.centroid, srid=4326).wkt


def decode_unique_ids(qs):
    """Decode UBIDs from queryset or individual PropertyState/TaxLotState"""
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
            bounding_box_obj = decode(getattr(state, "ubid"))
        except ValueError:
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

        # Round to avoid floating point errors
        state.latitude = round(bounding_box_obj.centroid.latitudeCenter, 12)
        state.longitude = round(bounding_box_obj.centroid.longitudeCenter, 12)

        state.save()


def get_jaccard_index(ubid1: str, ubid2: str) -> float:
    """
    Calculates the Jaccard index given two UBIDs

    The Jaccard index is a value between zero and one, representing the area of the intersection divided by the area of the union.
    Not a Match (0.0) <-----> (1.0) Perfect Match

    :param ubid1: A Property State UBID
    :param ubid2: A Property State UBID
    :return: The Jaccard index
    """
    if ubid1 == ubid2:
        return 1.0

    if not validate_ubid(ubid1) or not validate_ubid(ubid2):
        return 0.0

    return ubid_jaccard(ubid1, ubid2)


def validate_ubid(ubid: str) -> bool:
    """Validate a UBID

    :param ubid: The UBID string to be validated.
    :return: True if the UBID is valid, False otherwise.

    This function is 26% - 462% faster than calling buildingid.code.isValid

    Example usage:
    ```
    ubid = "849VQJH6+95J-51-58-42-50"
    is_valid = validate_ubid(ubid)
    print(is_valid)  # Output: True
    ```
    """
    if not ubid:
        return False

    try:
        index = ubid.find("-")
        pluscode = ubid[:index]
        ubid_offsets = ubid[index:]
        return valid_pluscode(pluscode) and bool(UBID_OFFSET_PATTERN.fullmatch(ubid_offsets))
    except ValueError:
        return False


def merge_ubid_models(old_state_ids, new_state_id, StateClass):  # noqa: N803
    """
    Given a list of old (existing) property/taxlot states, merge the existing ubid_models onto the new state

    If the new_state has an equivalent ubid, skip it.
    """
    from seed.models import UbidModel

    old_states = StateClass.objects.filter(id__in=old_state_ids).order_by("-id")
    new_state = StateClass.objects.get(id=new_state_id)
    new_ubids_set = set(new_state.ubidmodel_set.values_list("ubid", flat=True))

    if StateClass.__name__ == "PropertyState":
        old_ubids_set = set(UbidModel.objects.filter(property__in=old_states).values_list("ubid", flat=True))
        state_field = "property"
    else:
        old_ubids_set = set(UbidModel.objects.filter(taxlot__in=old_states).values_list("ubid", flat=True))
        state_field = "taxlot"

    old_ubids_to_promote = old_ubids_set - new_ubids_set

    if not old_ubids_to_promote:
        return new_state

    preferred_ubid = find_preferred(old_states, new_state)
    promote_ubids = [
        UbidModel(**{"ubid": ubid, state_field: new_state, "preferred": ubid == preferred_ubid}) for ubid in old_ubids_to_promote
    ]
    new_state.ubidmodel_set.bulk_create(promote_ubids)

    if preferred_ubid:
        state_qs = StateClass.objects.filter(id=new_state.id)
        decode_unique_ids(state_qs)
        new_state.refresh_from_db()

    return new_state


def find_preferred(old_states, new_state):
    # The preferred ubid will be the first preferred ubid found on a list of states.
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


def valid_pluscode(code: str) -> bool:
    """
    This code is ported from the openlocationcode `pluscode_isvalid` PL/pgSQL function,
    because it's faster than making sql queries for individual UBIDs
    https://github.com/benno-p/openlocationcode/blob/main/pluscode_functions.sql#L70
    :param code: str, pluscode (not UBID)
    :return: bool
    """
    # Code Without "+" char
    if PLUSCODE_SEPARATOR not in code:
        return False

    separator_index = code.index(PLUSCODE_SEPARATOR)
    # Code beginning with "+" char
    if separator_index == 0:
        return False
    # Code with illegal position separator
    if separator_index > 8 or separator_index % 2 == 1:
        return False

    # Code contains padding characters "0"
    if PLUSCODE_PADDING_CHAR in code:
        if separator_index < 8:
            return False
        # Last char is a separator
        if code[-1] != PLUSCODE_SEPARATOR:
            return False

        # Check if there are many "00" groups (only one is legal)
        padding_matches = re.findall(f"{PLUSCODE_PADDING_CHAR}+", code)
        if len(padding_matches) > 1:
            return False
        # Check if the first group is % 2 == 0
        if len(padding_matches[0]) % 2 == 1:
            return False

    # If there is just one char after '+'
    if len(code) - separator_index == 2:
        return False

    # Check if each char is in code_alphabet
    return bool(PLUSCODE_ALPHABET_PATTERN.fullmatch(code.upper()))


def ubid_jaccard(ubid1: str, ubid2: str) -> float:
    """
    Calculates the Jaccard index for two UBIDs.

    The Jaccard index is a value between zero and one, representing the area of the intersection
    divided by the area of the union.
    """
    ubid1_code_area = decode(Code(ubid1))
    ubid2_code_area = decode(Code(ubid2))

    return ubid1_code_area.jaccard(ubid2_code_area) or 0.0


def generate_ubidmodels_for_state(state):
    """
    Generate UbidModels for a PropertyState if the ubid field is present
    """
    logging.error(">>> generate_ubidmodel_for_state")

    ubids = getattr(state, "ubid")
    if not ubids:
        return

    # Allow ';' separated ubids
    ubids = ubids.split(";")
    state.ubidmodel_set.filter(preferred=True).update(preferred=False)
    for idx, ubid in enumerate(ubids):
        # trim leading/trailing spaces
        ubid_stripped = ubid.strip()
        is_first = idx == 0
        _, created = state.ubidmodel_set.update_or_create(ubid=ubid_stripped, defaults={"preferred": is_first})
        if created:
            decode_unique_ids(state)

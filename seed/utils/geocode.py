# !/usr/bin/env python
# encoding: utf-8

import requests
import json
import re

from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Q
from numbers import Number


class MapQuestAPIKeyError(Exception):
    """Your MapQuest API Key is either invalid or at its limit."""
    pass


def long_lat_wkt(state):
    """
    This translates GIS data saved as binary (WKB) into a text string (WKT).
    4326 refers to the commonly used spatial reference system and is used
    for the GIS fields on the PropertyState and TaxLotState models.
    """
    if state.long_lat:
        return GEOSGeometry(state.long_lat, srid=4326).wkt


def bounding_box_wkt(state):
    """
    This translates GIS data saved as binary (WKB) into a text string (WKT).
    """
    if state.bounding_box:
        return GEOSGeometry(state.bounding_box, srid=4326).wkt


def geocode_buildings(buildings):
    """
    Expects either a QuerySet (QS) of PropertyStates or a QS TaxLotStates.

    Previous manually geocoded -States (not via API) are handled then
    separated first. Everything else is eligible for geocoding (even those
    successfully geocoded before).

    With these remaining -States, build a dictionary of {id: address} and
    a dictionary of {address: geocoding_results}. It uses those two to construct
    a dictionary of {id: geocoding_results}. Finally, the
    {id: geocoding_results} dictionary is used to update the QS objects.

    Depending on if and how a -State is geocoded, the geocoding_confidence is
    populated with the details such as the confidence quality or lack thereof.
    """
    # -States with longitude and latitude prepopulated while excluding those previously geocoded by API
    pregeocoded = buildings.filter(longitude__isnull=False, latitude__isnull=False).exclude(geocoding_confidence__startswith="High")
    _geocode_by_prepopulated_fields(pregeocoded)

    # Include ungeocoded -States as well as previously API geocoded -States.
    buildings_to_geocode = buildings.filter(Q(longitude__isnull=True, latitude__isnull=True) | Q(geocoding_confidence__startswith="High"))

    # Don't continue if there are no buildings remaining
    if not buildings_to_geocode:
        return

    org = buildings_to_geocode[0].organization
    mapquest_api_key = org.mapquest_api_key

    # Don't continue if the mapquest_api_key for this org is ''
    if not mapquest_api_key:
        return

    # Don't continue if geocoding is disabled on this org
    if not org.geocoding_enabled:
        return

    id_addresses = _id_addresses(buildings_to_geocode, org)

    # Don't continue if there are no addresses to geocode, indiciating an insufficient
    # number of geocoding columns for all individual buildings or the whole org
    if not id_addresses:
        return

    address_geocoding_results = _address_geocoding_results(id_addresses, mapquest_api_key)

    id_geocoding_results = _id_geocodings(id_addresses, address_geocoding_results)

    _save_geocoding_results(id_geocoding_results, buildings_to_geocode)


def _save_geocoding_results(id_geocoding_results, buildings_to_geocode):
    for id, geocoding_result in id_geocoding_results.items():
        building = buildings_to_geocode.get(pk=id)

        if geocoding_result.get("is_valid"):
            building.long_lat = geocoding_result.get("long_lat")
            building.geocoding_confidence = f"High ({geocoding_result.get('quality')})"

            building.longitude = geocoding_result.get("longitude")
            building.latitude = geocoding_result.get("latitude")
        else:
            building.geocoding_confidence = f"Low - check address ({geocoding_result.get('quality')})"

        building.save()


def _geocode_by_prepopulated_fields(buildings):
    for building in buildings.iterator():
        long_lat = f"POINT ({building.longitude} {building.latitude})"
        building.long_lat = long_lat
        building.geocoding_confidence = "Manually geocoded (N/A)"
        building.save()


def _id_addresses(buildings, org):
    """
    Return a dictionary with {id: address, ...} containing only addresses with
    enough components.

    Expects all buildings to be of the same type - either PropertyState or TaxLotState

    For any addresses that don't have enough components,
    specify this in `geocoding_confidence`.
    """
    geocoding_columns = org.column_set.filter(
        geocoding_order__gt=0,
        table_name=buildings[0].__class__.__name__
    ).order_by('geocoding_order').values('column_name', 'is_extra_data')

    if geocoding_columns.count() == 0:
        return {}

    id_addresses = {}

    for building in buildings.iterator():
        full_address = _full_address(building, geocoding_columns)
        if full_address is not None:
            id_addresses[building.id] = full_address
        else:
            building.geocoding_confidence = "Missing address components (N/A)"
            building.save()

    return id_addresses


def _full_address(building, geocoding_columns):
    """
    Using organization-specific geocoding columns, a full address string is built.

    Check there are at least 1 address components present. Combine components to
    one full address. This helps to avoid receiving MapQuests' best guess result.
    For example, only sending '3001 Brighton Blvd, Suite 2693' would yield a
    valid point from one of multiple cities.

    Before passing the address back, special and reserved characters are removed.
    """

    address_components = []
    for col in geocoding_columns:
        if col['is_extra_data']:
            address_value = building.extra_data.get(col['column_name'], None)
        else:
            address_value = getattr(building, col['column_name'])

        # Only accept non-empty strings or numbers
        if (isinstance(address_value, (str, Number))) and (address_value != ""):
            address_components.append(str(address_value))

    if len(address_components) > 0:
        full_address = ", ".join(address_components)
        return re.sub(r'[;/?:@=&"<>#%{}|["^~`\]\\]', '', full_address)
    else:
        return None


def _address_geocoding_results(id_addresses, mapquest_api_key):
    addresses = list(set(id_addresses.values()))

    batched_addresses = _batch_addresses(addresses)
    results = []

    for batch in batched_addresses:
        locations = {"locations": []}
        locations["locations"] = [{"street": address} for address in batch]
        locations_json = json.dumps(locations)

        request_url = (
            'https://www.mapquestapi.com/geocoding/v1/batch?' +
            '&inFormat=json&outFormat=json&thumbMaps=false&maxResults=2' +
            '&json=' + locations_json +
            '&key=' + mapquest_api_key
        )

        response = requests.get(request_url)
        try:
            results += response.json().get('results')
        except Exception as e:
            if response.status_code == 403:
                raise MapQuestAPIKeyError('Failed geocoding property states due to MapQuest error. Your MapQuest API Key is either invalid or at its limit.')
            else:
                raise e

    return {_response_address(result): _analyze_location(result) for result in results}


def _response_address(result):
    return result.get('providedLocation').get('street')


def _analyze_location(result):
    """
    If multiple geolocations are returned, pass invalid indicator of "Ambiguous".

    According to MapQuest API
     - https://developer.mapquest.com/documentation/geocoding-api/quality-codes/
     GeoCode Quality ratings are provided in 5 characters in the form 'ZZYYY'.
     'ZZ' describes granularity level, and 'YYY' describes confidence ratings.

    Accuracy to either a point or a street address is accepted, while confidence
    ratings must all be at least A's and B's without C's or X's (N/A).
    """
    if len(result.get('locations')) != 1:
        return {"quality": "Ambiguous"}

    quality = result.get('locations')[0].get('geocodeQualityCode')
    granularity_level = quality[0:2]
    confidence_level = quality[2:5]
    is_acceptable_granularity = granularity_level in ["P1", "L1"]
    is_acceptable_confidence = not ("C" in confidence_level or "X" in confidence_level)

    if is_acceptable_confidence and is_acceptable_granularity:
        long = result.get('locations')[0].get('displayLatLng').get('lng')
        lat = result.get('locations')[0].get('displayLatLng').get('lat')

        return {
            "is_valid": True,
            "long_lat": f"POINT ({long} {lat})",
            "quality": quality,
            "longitude": long,
            "latitude": lat
        }
    else:
        return {"quality": quality}


def _id_geocodings(id_addresses, address_geocoding_results):
    return {
        id: address_geocoding_results.get(address)
        for id, address
        in id_addresses.items()
        if address_geocoding_results.get(address) is not None
    }


def _batch_addresses(addresses, n=50):
    for i in range(0, len(addresses), n):
        try:
            yield addresses[i:i + n]
        except StopIteration:
            return

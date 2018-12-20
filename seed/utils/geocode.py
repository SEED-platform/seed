# !/usr/bin/env python
# encoding: utf-8

import requests
import json
import re

from django.conf import settings

from django.contrib.gis.geos import GEOSGeometry


class MapQuestAPIKeyError(Exception):
    """Your MapQuest API Key is either invalid or at its limit."""
    pass


def long_lat_wkt(state):
    """
    This translates point data saved as binary (WKB) into a text string (WKT).
    4326 refers to the commonly used spatial reference system and is used
    for the GIS fields on the PropertyState and TaxLotState models.
    """
    if state.long_lat:
        return GEOSGeometry(state.long_lat, srid=4326).wkt


def geocode_addresses(buildings):
    """
    Upon receiving a QuerySet (QS) of properties or a QS tax lots, this method
    builds a dictionary of {id: address} and a dictionary of {address: geocoding}.
    It uses those two to build a dictionary of {id: geocoding} for buildings
    whose addresses return a valid geocoded longitude and latitude.
    Finally, the {id: geocoding} dictionary is used to update the QS objects.
    """
    id_addresses = _id_addresses(buildings)
    address_geocodings = _address_geocodings(id_addresses)

    id_geocodings = _id_geocodings(id_addresses, address_geocodings)

    for id, geocoding in id_geocodings.items():
        building = buildings.get(pk=id)
        building.long_lat = geocoding
        building.save()


def _id_addresses(buildings):
    return {
        building.id: _full_address(building)
        for building
        in buildings.iterator()
        if _full_address(building) is not None
    }


def _full_address(building):
    """
    Check there are at least 3 address components present. Combine components to
    one full address. This helps to avoid receiving MapQuests' best guess result.
    For example, only sending '3001 Brighton Blvd, Suite 2693' would yield a
    valid point from one of multiple cities.

    Before passing the address back, special and reserved characters are removed.
    """

    address_components = [
        building.address_line_1 or "",
        building.address_line_2 or "",
        building.city or "",
        building.state or "",
        building.postal_code or ""
    ]

    if address_components.count("") < 3:
        full_address = ", ".join(address_components)
        return re.sub(r'[;/?:@=&"<>#%{}|["^~`\]\\]', '', full_address)
    else:
        return None


def _address_geocodings(id_addresses):
    addresses = list(set(id_addresses.values()))

    batched_addresses = _batch_addresses(addresses)
    results = []

    for batch in batched_addresses:
        locations = {"locations": [ ]}
        locations["locations"] = [ {"street": address} for address in batch ]
        locations_json = json.dumps(locations)

        request_url = (
            'https://www.mapquestapi.com/geocoding/v1/batch?' +
            '&inFormat=json&outFormat=json&thumbMaps=false&maxResults=1' +
            '&json=' + locations_json +
            '&key=' + settings.MAPQUEST_API_KEY
        )

        response = requests.get(request_url)
        try:
            results += response.json().get('results')
        except Exception as e:
            if response.status_code == 403:
                raise MapQuestAPIKeyError
            else:
                raise e

    return {
        _response_address(result): _response_location(result)
        for result
        in results
        if _response_location(result) is not None
    }


def _response_address(result):
    return result.get('providedLocation').get('street')


def _response_location(result):
    """
    According to MapQuest API
     - https://developer.mapquest.com/documentation/geocoding-api/quality-codes/
     GeoCode Quality ratings are provided in 5 characters in the form 'ZZYYY'.
     'ZZ' describes granularity level, and 'YYY' describes confidence ratings.

    Accuracy to either a point or a street address is accepted, while confidence
    ratings must all be at least A's and B's without C's or X's (N/A).
    """

    quality = result.get('locations')[0].get('geocodeQualityCode')
    granularity_level = quality[0:2]
    confidence_level = quality[2:5]
    is_acceptable_granularity = granularity_level in ["P1", "L1"]
    is_acceptable_confidence = not ("C" in confidence_level or "X" in confidence_level)

    if is_acceptable_confidence and is_acceptable_granularity:
        long = result.get('locations')[0].get('displayLatLng').get('lng')
        lat = result.get('locations')[0].get('displayLatLng').get('lat')
        return f"POINT ({long} {lat})"
    else:
        return None


def _id_geocodings(id_addresses, address_geocodings):
    return {
        id: address_geocodings.get(address)
        for id, address
        in id_addresses.items()
        if address_geocodings.get(address) is not None
    }


def _batch_addresses(addresses, n=50):
    for i in range(0, len(addresses), n):
        yield addresses[i:i + n]

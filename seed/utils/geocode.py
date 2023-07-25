# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
import re
from numbers import Number

import requests
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Q
from shapely import geometry, wkt

from seed.lib.superperms.orgs.models import Organization
from seed.models.columns import Column


class MapQuestAPIKeyError(Exception):
    """Your MapQuest API Key is either invalid or at its limit."""


def long_lat_wkt(state):
    """
    This translates GIS data saved as binary (WKB) into a text string (WKT).
    4326 refers to the commonly used spatial reference system and is used
    for the GIS fields on the PropertyState and TaxLotState models.
    """
    if state.long_lat:
        return GEOSGeometry(state.long_lat, srid=4326).wkt


def wkt_to_polygon(wkt_to_translate):
    """Translate WKT to a bounding box polygon."""
    return geometry.mapping(wkt.loads(wkt_to_translate))


def bounding_box_wkt(state):
    """
    This translates GIS data saved as binary (WKB) into a text string (WKT).
    """
    if state.bounding_box:
        return GEOSGeometry(state.bounding_box, srid=4326).wkt


def create_geocoded_additional_columns(organization: Organization):
    """Create the additional columns that are needed for storing the extra
    geocoded data that will be returned by the MapQuest service."""
    new_columns = [
        {"name": "geocoded_address", "display_name": "Geocoded Address", "description": "GeocodedAddress"},
        {"name": "geocoded_postal_code", "display_name": "Geocoded Postal Code", "description": "Geocoded Postal Code"},
        {"name": "geocoded_side_of_street", "display_name": "Geocoded Side of Street", "description": "Geocoded Side of Street"},
        {"name": "geocoded_country", "display_name": "Geocoded Country", "description": "Geocoded Country"},
        {"name": "geocoded_state", "display_name": "Geocoded State", "description": "Geocoded State"},
        {"name": "geocoded_county", "display_name": "Geocoded County", "description": "Geocoded County"},
        {"name": "geocoded_city", "display_name": "Geocoded City", "description": "Geocoded City"},
        {"name": "geocoded_neighborhood", "display_name": "Geocoded Neighborhood", "description": "Geocoded Neighborhood"},
    ]

    # make sure the columns exist for the extra data
    for new_column in new_columns:
        column, created = Column.objects.get_or_create(
            is_extra_data=True,
            column_name=new_column['name'],
            organization=organization,
            table_name='PropertyState',
            units_pint=None
        )
        if created:
            column.display_name = new_column['display_name']
            column.column_description = new_column['description']
            column.save()


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

    # Don't continue if there are no addresses to geocode, indicating an insufficient
    # number of geocoding columns for all individual buildings or the whole org
    if not id_addresses:
        return

    address_geocoding_results = _address_geocoding_results(id_addresses, mapquest_api_key)

    id_geocoding_results = _id_geocodings(id_addresses, address_geocoding_results)

    _save_geocoding_results(id_geocoding_results, buildings_to_geocode, org)


def _save_geocoding_results(id_geocoding_results, buildings_to_geocode, org):
    """Save the geocoding results to the data. Some of the Geocoded fields end up
    as extra data, so we need to make sure the columns exist.

    Args:
        id_geocoding_results (list): list of geocoded results
        buildings_to_geocode (list): list of buildings to geocode
        org (Organization): The organization that the results are to be saved to
    """
    # This is a redundant call, but intentional. If running this command from the `tasks`
    # module, then the columns should already have been created to protect against from
    # race conditions. However, there are other methods that geocode buildings (e.g., from
    # the inventory list dropdown), so this is a safety check.
    create_geocoded_additional_columns(org)

    for id, geocoding_result in id_geocoding_results.items():
        building = buildings_to_geocode.get(pk=id)

        if geocoding_result.get("is_valid"):
            building.long_lat = geocoding_result.get("long_lat")
            building.geocoding_confidence = f"High ({geocoding_result.get('quality')})"

            building.longitude = geocoding_result.get("longitude")
            building.latitude = geocoding_result.get("latitude")

            # save files to extra data, if they have been configured
            building.extra_data['geocoded_address'] = geocoding_result.get("address")
            building.extra_data['geocoded_postal_code'] = geocoding_result.get("postal_code")
            building.extra_data['geocoded_side_of_street'] = geocoding_result.get("side_of_street")
            building.extra_data['geocoded_country'] = geocoding_result.get("Country")
            building.extra_data['geocoded_state'] = geocoding_result.get("State")
            building.extra_data['geocoded_county'] = geocoding_result.get("County")
            building.extra_data['geocoded_city'] = geocoding_result.get("City")
            building.extra_data['geocoded_neighborhood'] = geocoding_result.get("Neighborhood")

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
            # Catch the invalide API key error before parsing the response
            if response.status_code == 401:
                raise MapQuestAPIKeyError(f'Failed geocoding property states due to MapQuest error. API Key is invalid with message: {response.content}.')

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

    # The Geocoded data will look something like this:
    # [{'providedLocation': {'street': '18741 e 71st ave, Colorado'},
    #   'locations': [
    #     {'street': '18741 E 71st Ave',
    #      'adminArea6': 'Denver International Airport', 'adminArea6Type': 'Neighborhood',
    #      'adminArea5': 'Denver', 'adminArea5Type': 'City',
    #      'adminArea4': 'Denver', 'adminArea4Type': 'County',
    #      'adminArea3': 'CO', 'adminArea3Type': 'State',
    #      'adminArea1': 'US', 'adminArea1Type': 'Country',
    #      'postalCode': '80249-7375', 'geocodeQualityCode': 'P1AAA',
    #      'geocodeQuality': 'ADDRESS', 'dragPoint': False, 'sideOfStreet': 'L',
    #      'linkId': '0', 'unknownInput': '', 'type': 's',
    #      'latLng': {'lat': 39.82612, 'lng': -104.76877},
    #      'displayLatLng': {'lat': 39.82622, 'lng': -104.76898}, 'mapUrl': ''}
    #   ]
    # }]
    if is_acceptable_confidence and is_acceptable_granularity:
        long = result.get('locations')[0].get('displayLatLng').get('lng')
        lat = result.get('locations')[0].get('displayLatLng').get('lat')

        # flatten out the "adminArea" fields that exist in the result
        admin_areas = {}
        for i in range(1, 7):
            if result.get('locations')[0].get(f'adminArea{i}Type') is None:
                continue
            admin_areas[result.get('locations')[0].get(f'adminArea{i}Type')] = result.get('locations')[0].get(f'adminArea{i}')

        return {
            "is_valid": True,
            "long_lat": f"POINT ({long} {lat})",
            "quality": quality,
            "longitude": long,
            "latitude": lat,
            "address": result.get('locations')[0].get('street'),
            "postal_code": result.get('locations')[0].get('postalCode'),
            "side_of_street": result.get('locations')[0].get('sideOfStreet'),
        } | admin_areas
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

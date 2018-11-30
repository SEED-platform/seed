
# base case:
"""
 - target buildings provided within a queryset
 - address fields may or may not be populated - address_line_1, address_line_2, city, state, and postal_code
 - results definitely come back
 - long_lat always updated
 - there are less than 101 addresses
"""

# once base is covered, these cases should also be covered:
"""
 - case when the data is insufficient and geocodequality is low (can notes be added?)
 - case when there are no chars or numbers (covers an error edge case in API)
    - possible that API doesn't return anything if only spaces or special chars provided
 - case when the two lat long fields are populated already?
    - might not be a case to worry about here
 - case when long_lat is populated already (consider worrying about this @ source)
"""

# general considerations
"""
 - Update docs to instruct users to update local_untracked.py
 - specific notes/TODOs listed in code
 - limit should be enforced on _address_geocodings
 - are these all the fields that are necessary? should more be added? address_line_2
"""

import requests

from django.conf import settings

from django.contrib.gis.geos import GEOSGeometry


def long_lat_wkt(state):
    return GEOSGeometry(state.long_lat,srid=4326).wkt

def geocode_addresses(buildings):
    id_addresses = _id_addresses(buildings)
    address_geocodings = _address_geocodings(id_addresses)

    id_geocodings = _id_geocodings(id_addresses, address_geocodings)

    for building in buildings:
        building.long_lat = id_geocodings.get(building.id)
        building.save()

def _id_addresses(buildings):
    return { building.id: _full_address(building) for building in buildings }

def _full_address(building):
    return ", ".join([
        building.address_line_1 or "",
        building.address_line_2 or "",
        building.city or "",
        building.state or "",
        building.postal_code or ""
    ])

def _address_geocodings(id_addresses):
    addresses = list(set(id_addresses.values()))
    # (at the very least) group by 100 should be done here
    locations = "location=" + "&location=".join(addresses)

    response = requests.get(
        'https://www.mapquestapi.com/geocoding/v1/batch?' +
        '&inFormat=kvp&outFormat=json&thumbMaps=false&maxResults=1&' +
        locations +
        '&key=' +
        settings.MAPQUEST_API_KEY
    )
    results = response.json().get('results')

    return {
        _response_address(result): _response_location(result)
        for result
        in results
    }

def _response_address(result):
    return result.get('providedLocation').get('location')

def _response_location(result):
    # analyze geocodequality here and return empty string (which turns into NoneType)
    # possibly add a note for this field as well? consider this further
    return (f"POINT ({result.get('locations')[0].get('latLng').get('lng')} " +
        f"{result.get('locations')[0].get('latLng').get('lat')})")

def _id_geocodings(id_addresses, address_geocodings):
    return {
        id: address_geocodings.get(address)
        for id, address
        in id_addresses.items()
    }

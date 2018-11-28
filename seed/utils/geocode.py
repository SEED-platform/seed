# from seed.utils.geocode import geocode_addresses

# receives a collection of PropertyState objects
# if applicable, updates long_lat
# returns the same collection of PropertyState objects

# base case:
"""
 - target properties provided within a queryset
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
from seed.models.properties import PropertyState


def geocode_addresses():
    # properties will be a parameter
    # consider using objects.select_for_update() to lock objects
    properties = PropertyState.objects.filter(state='Pennsylvania')

    id_addresses = _id_addresses(properties)
    address_geocodings = _address_geocodings(id_addresses)

    id_geocodings = _id_geocodings(id_addresses, address_geocodings)

    for property in properties:
        property.long_lat = id_geocodings.get(property.id)
        # property.long_lat = ""
        property.save()

def _id_addresses(properties):
    return { property.id: _full_address(property) for property in properties }

def _full_address(property):
    return ", ".join([
        property.address_line_1 or "",
        property.address_line_2 or "",
        property.city or "",
        property.state or "",
        property.postal_code or ""
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
    # refactor below to not be so long in one line
    # any value out of dictionary comprehension vs other approach?
    # this where logic should live for assessing geocodequality
    return {
        _response_address(result): _response_location(result)
        for result
        in results
    }

def _response_address(result):
    return result.get('providedLocation').get('location')

def _response_location(result):
    # analyze geocodequality here and return empty string (which turns into NoneType)
    return (f"POINT ({result.get('locations')[0].get('latLng').get('lng')} " +
        f"{result.get('locations')[0].get('latLng').get('lat')})")

def _id_geocodings(id_addresses, address_geocodings):
    return {
        id: address_geocodings.get(address)
        for id, address
        in id_addresses.items()
    }

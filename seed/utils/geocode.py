# from seed.utils.geocode import geocode_addresses

# receives a collection of PropertyState objects
# if applicable, updates long_lat
# returns the same collection of PropertyState objects

# base case:
"""
 - target properties provided within a queryset
 - address fields populated - address_line_1, city, state, and postal_code
 - long_lat not populated
 - there are less than 101 addresses
"""

# once base is covered, these cases should also be covered:
"""
 - case when the data is insufficient and geocodequality is low
 - case when the two lat long fields are populated already
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
        property.save()

def _id_addresses(properties):
    return {
        property.id: ", ".join([
            property.address_line_1,
            property.city,
            property.state,
            property.postal_code
        ])
        for property
        in properties
    }

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
        result.get('providedLocation').get('location'): f"POINT ({result.get('locations')[0].get('latLng').get('lng')} {result.get('locations')[0].get('latLng').get('lat')})"
        for result
        in results
    }

def _id_geocodings(id_addresses, address_geocodings):
    return {
        id: address_geocodings.get(address)
        for id, address
        in id_addresses.items()
    }

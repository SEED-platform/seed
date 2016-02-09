import logging

from seed.models import (
    BuildingSnapshot,
    CanonicalBuilding,
)
_log = logging.getLogger(__name__)

def retrieve_building_id(addresses):
    _log.info('\nretrieveID of buildings')

    for address in addresses:
        # open a cursor

        # retrieve GreenButton URL and building_id relationship from PostgreSQL
        # Query the database and obtain data as Python objects
        # select the table seed_buildingsnapshot and the record with
        # address equals to the query address
        # address search is a simple query, might need to change for
        # approximate searching later
        snapshot = BuildingSnapshot.objects.filter(address_line_1=format(address))
        
        if snapshot:
            s_id = snapshot[0].id
        else:
            _log.info('No matching data with address {0}'.format(address))
            s_id = None
            c_id = None
            addresses[address] = {'buildingsnapshot_id' : s_id, 'canonical_building' : c_id}
            continue

        canonical = CanonicalBuilding.objects.filter(canonical_snapshot_id=format(s_id))
        if canonical:
            c_id = canonical[0].id
        else:
            _log.info('No matching data with address {0}'.format(address))
            c_id = None

        addresses[address] = {'buildingsnapshot_id' : s_id, 'canonical_building' : c_id}


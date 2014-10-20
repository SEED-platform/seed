import json

from superperms.orgs.decorators import has_perm
from annoying.decorators import ajax_request
from django.contrib.auth.decorators import login_required

from seed.models import (
    ENERGY_TYPES,
    ENERGY_UNITS,
    obj_to_dict,
    BuildingSnapshot,
    Meter,
    TimeSeries
)

from seed.utils.time import convert_datestr


@ajax_request
@login_required
@has_perm('requires_viewer')
def get_meters(request):
    """Returns all of the meters for a building.

    Expected GET params:

    building_id: int, unique identifier for a (canonical) building.
    """
    building_id = request.GET.get('building_id', '')
    if not building_id:
        return {'status': 'error', 'message': 'No building id specified'}

    return {
        'status': 'success', 'building_id': building_id, 'meters': [
            obj_to_dict(m) for m in Meter.objects.filter(
                building_snapshot=building_id
            )
        ]
    }


def _convert_energy_data(name, mapping):
    """Converts human name to interger for DB.

    :parm name: str, the unit or type name from JS.
    :param mapping: tuple of tuples used for Django Meter choices.
    :returns: int, the intereger value of the string stored in the DB.

    ``mapping`` looks like ((3, 'Electricity'), (4, 'Natural Gas'))
    See ``ENERGY_TYPES`` and ``ENERGY_UNITS`` in ``seed.models``.
    """
    return filter(
        lambda x: x[1] == name, [t for t in mapping]
    )[0][0]


@ajax_request
@login_required
@has_perm('can_modify_data')
def add_meter_to_building(request):
    """Will add a building to an existing meter.

    Payload is expected to look like the following:
    {
        'organization_id': 435,
        'building_id': 342,
        'meter_name': 'Unit 34.',
        'energy_type': 'Electricity',
        'energy_units': 'kWh'
    }
    """
    body = json.loads(request.body)
    building_id = body.get('building_id', '')

    building = BuildingSnapshot.objects.get(pk=building_id)

    meter_name = body.get('meter_name', '')
    energy_type_name = body.get('energy_type', 'Electricity')
    energy_unit_name = body.get('energy_units', 'kWh')
    # Grab the integer representation of the energytype from ENERGY_TYPES.
    energy_type = _convert_energy_data(energy_type_name, ENERGY_TYPES)
    energy_units = _convert_energy_data(energy_unit_name, ENERGY_UNITS)

    meter = Meter.objects.create(
        name=meter_name, energy_type=energy_type, energy_units=energy_units
    )

    meter.building_snapshot.add(building)
    meter.save()

    return {'status': 'success'}


@ajax_request
@login_required
@has_perm('requires_viewer')
def get_timeseries(request):
    """Return all time series data for a building, grouped by meter.

    Expected GET params:

    meter_id: int, unique identifier for the meter.
    offset: int, the offset from the most recent meter data to begin showing.
    num: int, the number of results to show.
    """
    meter_id = request.GET.get('meter_id', '')
    offset = int(request.GET.get('offset', 0))
    num = int(request.GET.get('num', 12))  # 12 because monthly data.

    if not meter_id:
        return {'status': 'error', 'message': 'No meter id specified'}

    result = {'status': 'success', 'meter_id': meter_id, 'timeseries': []}

    paginated_ts = TimeSeries.objects.filter(
        meter_id=meter_id
    )[offset:offset + num]

    for ts in paginated_ts:
        t = obj_to_dict(ts)
        result['timeseries'].append(t)

    return result


@ajax_request
@login_required
@has_perm('can_modify_data')
def add_timeseries(request):
    """Add timeseries data for a meter.

    Payload is expected to look like the following:
    {
        'organization_id': 435,
        'meter_id': 34,
        'timeseries': [
            {
                'begin_time': 2342342232,
                'end_time': 23423433433,
                'cost': 232.23,
            }...
        ]
    }
    """
    body = json.loads(request.body)
    meter_id = body.get('meter_id', '')
    ts_data = body.get('timeseries', [])
    try:
        meter = Meter.objects.get(pk=meter_id)
    except Meter.DoesNotExist:
        return {'status': 'error', 'message': 'Meter ID does not match'}

    for ts_item in ts_data:
        TimeSeries.objects.create(
            begin_time=convert_datestr(ts_item.get('begin_time', None)),
            end_time=convert_datestr(ts_item.get('end_time', None)),
            reading=ts_item.get('reading', None),
            cost=ts_item.get('cost', None),
            meter=meter
        )

    return {'status': 'success'}

from seed.decorators import ajax_request
from seed.utils.api import api_endpoint

from django.db.models import Max
from seed.models import(
    BuildingSnapshot,
)


@api_endpoint
@ajax_request
def overview_portfolio(request):
    res = {}

    rank_type = request.GET.get('rank_type')
    if not rank_type:
        res['status'] = 'error'
        res['msg'] = 'Expecting rank_type parameter'
        return res
    if rank_type != 'building_number' and rank_type != 'gross_floor_area':
        res['status'] = 'error'
        res['msg'] = 'Unrecognized rank_type, expecting building_number or gross_floor_area'
        return res

    last_bld_snapshot_ids = BuildingSnapshot.objects.values('canonical_building_id').annotate(max_id=Max('id')).order_by()
    bld_snapshot_ids = [ids['max_id'] for ids in last_bld_snapshot_ids]

    query_result = BuildingSnapshot.objects.filter(id__in=bld_snapshot_ids).exclude(use_description__isnull=True).exclude(use_description__exact='').exclude(gross_floor_area__isnull=True)

    data = {}
    for bld in query_result:
        bld_type = bld.use_description
        gross_floor_area = bld.gross_floor_area

        if bld_type not in data:
            data[bld_type] = {}
            data[bld_type]['building_number'] = 0
            data[bld_type]['gross_floor_area'] = 0

        data[bld_type]['building_number'] += 1
        data[bld_type]['gross_floor_area'] += float(gross_floor_area)

    blds = []
    for bld_type, bld_info in data.iteritems():
        bld = {}
        bld['building_type'] = bld_type
        bld['building_number'] = bld_info['building_number']
        bld['gross_floor_area'] = bld_info['gross_floor_area']
        blds.append(bld)

    blds = sorted(blds, key=lambda bld: bld[rank_type], reverse=True)

    ret = {}
    ret['building_type'] = []
    ret['building_number'] = []
    ret['gross_floor_area'] = []
    for bld_type in blds:
        ret['building_type'].append(bld_type['building_type'])
        ret['building_number'].append(bld_type['building_number'])
        ret['gross_floor_area'].append(bld_type['gross_floor_area'] / 1000)

    res['status'] = 'success'
    res['data'] = ret
    return res

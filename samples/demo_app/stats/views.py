"""
:copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Min, Max, StdDev
from django.shortcuts import render_to_response
from django.template import RequestContext

from seed.models import BuildingSnapshot


@login_required
def stats(request):
    """get a couple averages to display"""
    stats_dict = BuildingSnapshot.objects.filter(
        canonical_building__active=True
    ).aggregate(
        Avg('gross_floor_area'),
        Min('gross_floor_area'),
        Max('gross_floor_area'),
        StdDev('gross_floor_area'),
    )

    return render_to_response(
        'stats/stats.html',
        locals(),
        context_instance=RequestContext(request))

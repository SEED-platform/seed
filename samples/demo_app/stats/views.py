"""
:copyright: (c) 2014 Building Energy Inc
"""

from django.contrib.auth.decorators import login_required
from annoying.decorators import render_to
from seed.models import BuildingSnapshot
from django.db.models import Avg, Min, Max, StdDev


@login_required
@render_to('stats/stats.html')
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

    return locals()

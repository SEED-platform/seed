from rest_framework import filters

from seed import search


class BuildingFilterBackend(filters.BaseFilterBackend):
    """
    Implements the filtering and searching of buildings as a Django Rest
    Framework filter backend.
    """
    def filter_queryset(self, request, queryset, view):
        # TODO: this needs to be filled in with the same logic that implements
        # search/filtering in `seed.views.main.search_buildings`.
        params = search.process_search_params(
            params=request.query_params,
            user=request.user,
            is_api_request=True,
        )
        buildings_queryset = search.orchestrate_search_filter_sort(
            params=params,
            user=request.user,
        )
        return buildings_queryset

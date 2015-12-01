from rest_framework import filters


class BuildingFilterBackend(filters.BaseFilterBackend):
    """
    Implements the filtering and searching of buildings as a Django Rest
    Framework filter backend.
    """
    def filter_queryset(self, request, queryset, view):
        # TODO: this needs to be filled in with the same logic that implements
        # search/filtering in `seed.views.main.search_buildings`.
        assert False
        return queryset

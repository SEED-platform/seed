from rest_framework import pagination
from rest_framework import response


class FakePaginiation(pagination.PageNumberPagination):
    """
    DRF Paginator class that presents results in the same format as
    `PageNumberPagination` but always includes all results on the first page.
    """
    def get_paginated_response(self, data):
        return response.Response({
            "next": None,
            "previous": None,
            "count": len(data),
            "results": data,
        })

    def paginate_queryset(self, queryset, request, view=None):
        return queryset

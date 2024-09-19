"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ResultsListPagination(PageNumberPagination):
    page_size_query_param = "per_page"

    def get_paginated_response(self, data):
        page_num = self.page.number

        return Response(
            OrderedDict(
                [
                    ("page", page_num),
                    ("start", self.page.start_index()),
                    ("end", self.page.end_index()),
                    ("num_pages", self.page.paginator.num_pages),
                    ("has_next", self.page.has_next()),
                    ("has_previous", self.page.has_previous()),
                    ("total", self.page.paginator.count),
                    ("results", data),
                ]
            )
        )

    # TODO this won't work until drf-yasg is updated to v1.21.7
    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "success"},
                "data": schema,
                "pagination": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer", "example": 123},
                        "start": {"type": "integer", "example": 123},
                        "end": {"type": "integer", "example": 123},
                        "num_pages": {"type": "integer", "example": 123},
                        "has_next": {"type": "boolean", "example": True},
                        "has_previous": {"type": "boolean", "example": False},
                        "total": {"type": "integer", "example": 123},
                    },
                },
            },
        }

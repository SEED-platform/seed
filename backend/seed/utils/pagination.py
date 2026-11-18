"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
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

    def get_paginated_response_schema(self, schema):
        """Matches `get_paginated_response`. Views using `SEEDJSONRenderer` additionally move all but `results`
        under a `pagination` key, which `seed.utils.api_schema.SEEDAutoSchema` accounts for."""
        return {
            "type": "object",
            "required": ["page", "start", "end", "num_pages", "has_next", "has_previous", "total", "results"],
            "properties": {
                "page": {"type": "integer", "example": 1},
                "start": {"type": "integer", "example": 1},
                "end": {"type": "integer", "example": 25},
                "num_pages": {"type": "integer", "example": 4},
                "has_next": {"type": "boolean", "example": True},
                "has_previous": {"type": "boolean", "example": False},
                "total": {"type": "integer", "example": 100},
                "results": schema,
            },
        }

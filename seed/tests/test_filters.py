"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from seed.filters import ColumnListProfileFilterBackend


class ColumnListProfileFilterBackendTests(SimpleTestCase):
    def test_accepts_drf_keyword_arguments(self):
        # DRF's filter protocol permits callers to pass view by keyword.
        request = SimpleNamespace(query_params={"organization_id": "42"})
        queryset = Mock()

        result = ColumnListProfileFilterBackend().filter_queryset(request=request, queryset=queryset, view=object())

        queryset.filter.assert_called_once_with(organization_id="42")
        assert result is queryset.filter.return_value

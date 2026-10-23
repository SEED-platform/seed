"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import pytest
from django.test import SimpleTestCase
from shapely import wkt

from seed.management.commands.create_geojson_mock_data import Command


class CreateGeoJSONMockDataTests(SimpleTestCase):
    def test_convert_polygon_to_wkt_preserves_interior_rings(self):
        geojson = {
            "type": "Polygon",
            "coordinates": [
                [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]],
                [[1, 1], [1, 2], [2, 2], [2, 1], [1, 1]],
            ],
        }

        polygon = wkt.loads(Command().convert_list_to_wkt(geojson))

        assert len(polygon.interiors) == 1

    def test_convert_non_polygon_rejects_unknown_geometry_type(self):
        with pytest.raises(ValueError, match="Unknown type of Geometry in GeoJSON of Point"):
            Command().convert_list_to_wkt({"type": "Point", "coordinates": [0, 0]})

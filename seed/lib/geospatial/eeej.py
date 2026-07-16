"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import csv
import lzma
import os
from contextlib import suppress

from django.conf import settings
from django.contrib.gis.geos import Point

from seed.models.eeej import EeejCejst, EeejHud, HousingType

BATCH_SIZE = 5000


def _bool(value):
    return value == "True"


def _int_or_none(value):
    return int(value) if value != "" else None


def add_eeej_data():
    """Import EEEJ data from various sources
    This will take a while to run
    """
    import_cejst()
    import_hud()


def import_hud():
    """Import HUD data for Public Developments and Multi-Family - Assisted
    https://hudgis-hud.opendata.arcgis.com/datasets/public-housing-developments-1/explore?showTable=true
    https://hudgis-hud.opendata.arcgis.com/datasets/HUD::multifamily-properties-assisted/explore?showTable=true

    # property_name comes from PROJECT_NAME or PROPERTY_NAME_TEXT columns
    """
    # Note: instead of update_or_create, it might be better to clear and start over
    # Use smaller files to test with
    if settings.EEEJ_LOAD_SMALL_TEST_DATASET:
        HUD_DATA_PATH_HOUSING = os.path.join(settings.BASE_DIR, "seed/lib/geospatial/data", "test-Public_Housing_Developments.csv.xz")
        HUD_DATA_PATH_MULTIFAMILY = os.path.join(
            settings.BASE_DIR, "seed/lib/geospatial/data", "test-Multifamily_Properties_-_Assisted.csv.xz"
        )
    else:
        HUD_DATA_PATH_HOUSING = os.path.join(settings.BASE_DIR, "seed/lib/geospatial/data", "Public_Housing_Developments.csv.xz")
        HUD_DATA_PATH_MULTIFAMILY = os.path.join(settings.BASE_DIR, "seed/lib/geospatial/data", "Multifamily_Properties_-_Assisted.csv.xz")

    files = [
        {"type": HousingType.PUBLIC_HOUSING, "path": HUD_DATA_PATH_HOUSING},
        {"type": HousingType.MULTIFAMILY, "path": HUD_DATA_PATH_MULTIFAMILY},
    ]
    for file in files:
        with lzma.open(file["path"], mode="rt", encoding="utf-8") as fd:
            reader = csv.reader(fd)
            col: dict[str, int] = {}
            for col_index, header in enumerate(next(reader, None)):
                col[header] = col_index

            hud_rows = []
            for row in reader:
                if file["type"] == HousingType.PUBLIC_HOUSING:
                    hud_object_id = f"PH_{row[col['OBJECTID']]}"
                    name = row[col["PROJECT_NAME"]]
                elif file["type"] == HousingType.MULTIFAMILY:
                    hud_object_id = f"MF_{row[col['OBJECTID']]}"
                    name = row[col["PROPERTY_NAME_TEXT"]]

                tract = row[col["TRACT_LEVEL"]]
                lon = row[col["LON"]]
                lat = row[col["LAT"]]
                if not tract or not lon or not lat:
                    continue

                with suppress(ValueError):
                    hud_rows.append(
                        EeejHud(
                            hud_object_id=hud_object_id,
                            census_tract_geoid=tract.zfill(11),
                            name=name,
                            housing_type=file["type"],
                            long_lat=Point(float(lon), float(lat)),
                        )
                    )

            EeejHud.objects.bulk_create(
                hud_rows,
                batch_size=BATCH_SIZE,
                update_conflicts=True,
                unique_fields=["hud_object_id"],
                update_fields=[
                    "census_tract_geoid",
                    "long_lat",
                    "housing_type",
                    "name",
                ],
            )


def import_cejst():
    """Import CEJST Data:
    https://energyjustice-buildings.egs.anl.gov/resources/serve/Buildings/cejst.csv
    Headers of interest: Census tract 2010 ID, Identified as disadvantaged,
    Greater than or equal to the 90th percentile for energy burden and is low income?, Energy burden (percentile)
    """
    # Use a smaller file to test with
    if settings.EEEJ_LOAD_SMALL_TEST_DATASET:
        CEJST_DATA_PATH = os.path.join(settings.BASE_DIR, "seed/lib/geospatial/data", "test-cejst-1.0-communities.csv.xz")
    else:
        CEJST_DATA_PATH = os.path.join(settings.BASE_DIR, "seed/lib/geospatial/data", "cejst-1.0-communities.csv.xz")

    # import CEJST
    with lzma.open(CEJST_DATA_PATH, mode="rt", encoding="utf-8") as fd:
        reader = csv.reader(fd)
        col: dict[str, int] = {}
        for col_index, header in enumerate(next(reader, None)):
            col[header] = col_index

        cejst_rows = []
        for row in reader:
            cejst_rows.append(
                EeejCejst(
                    census_tract_geoid=row[col["Census tract 2010 ID"]],
                    dac=_bool(row[col["Identified as disadvantaged"]]),
                    energy_burden_low_income=_bool(
                        row[col["Greater than or equal to the 90th percentile for energy burden and is low income?"]]
                    ),
                    energy_burden_percent=_int_or_none(row[col["Energy burden (percentile)"]]),
                    low_income=_bool(row[col["Is low income?"]]),
                    share_neighbors_disadvantaged=_int_or_none(row[col["Share of neighbors that are identified as disadvantaged"]]),
                )
            )

        EeejCejst.objects.bulk_create(
            cejst_rows,
            batch_size=BATCH_SIZE,
            update_conflicts=True,
            unique_fields=["census_tract_geoid"],
            update_fields=[
                "dac",
                "energy_burden_low_income",
                "energy_burden_percent",
                "low_income",
                "share_neighbors_disadvantaged",
            ],
        )

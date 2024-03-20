"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""
import csv
import lzma
import os

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db.utils import IntegrityError

from seed.models.eeej import EeejCejst, EeejHud, HousingType


def add_eeej_data():
    """ Import EEEJ data from various sources
    This will take a while to run
    """
    import_cejst()
    import_hud()


def import_hud():
    """ Import HUD data for Public Developments and Multi-Family - Assisted
    https://hudgis-hud.opendata.arcgis.com/datasets/public-housing-developments-1/explore?showTable=true
    https://hudgis-hud.opendata.arcgis.com/datasets/HUD::multifamily-properties-assisted/explore?showTable=true

    # property_name comes from PROJECT_NAME or PROPERTY_NAME_TEXT columns
    """
    # Note: instead of update_or_create, it might be better to clear and start over
    # Use smaller files to test with
    if settings.EEEJ_LOAD_SMALL_TEST_DATASET:
        HUD_DATA_PATH_HOUSING = os.path.join(settings.BASE_DIR, 'seed/lib/geospatial/data', 'test-Public_Housing_Developments.csv.xz')
        HUD_DATA_PATH_MULTIFAMILY = os.path.join(settings.BASE_DIR, 'seed/lib/geospatial/data', 'test-Multifamily_Properties_-_Assisted.csv.xz')
    else:
        HUD_DATA_PATH_HOUSING = os.path.join(settings.BASE_DIR, 'seed/lib/geospatial/data', 'Public_Housing_Developments.csv.xz')
        HUD_DATA_PATH_MULTIFAMILY = os.path.join(settings.BASE_DIR, 'seed/lib/geospatial/data', 'Multifamily_Properties_-_Assisted.csv.xz')

    files = [
        {'type': HousingType.PUBLIC_HOUSING, 'path': HUD_DATA_PATH_HOUSING},
        {'type': HousingType.MULTIFAMILY, 'path': HUD_DATA_PATH_MULTIFAMILY}
    ]
    errors = []
    for file in files:
        with lzma.open(file['path'], mode='rt', encoding='utf-8') as fd:
            reader = csv.reader(fd)
            col: dict[str, int] = {}
            for col_index, header in enumerate(next(reader, None)):
                col[header] = col_index

            for row_index, row in enumerate(reader, start=1):
                if file['type'] == HousingType.PUBLIC_HOUSING:
                    hud_object_id = f"PH_{row[col['OBJECTID']]}"
                    name = row[col['PROJECT_NAME']]
                elif file['type'] == HousingType.MULTIFAMILY:
                    hud_object_id = f"MF_{row[col['OBJECTID']]}"
                    name = row[col['PROPERTY_NAME_TEXT']]

                try:
                    EeejHud.objects.update_or_create(
                        census_tract_geoid=(row[col['TRACT_LEVEL']] or None).zfill(11),
                        hud_object_id=hud_object_id,
                        name=name,
                        housing_type=file['type'],
                        defaults={'long_lat': Point(
                            float(row[col['LON']]),
                            float(row[col['LAT']])
                        )}
                    )
                except IntegrityError as e:
                    errors.append("EEEJ HUD Row already exists: {}. error: {}".format(row_index, str(e)))
                    # print(str(e))
                except Exception as e:
                    errors.append("EEEJ HUD - could not add row: {}. error: {}".format(row_index, str(e)))
                    # print(str(e))

    # print(f"{len(errors)} errors encountered when loading HUD data")


def import_cejst():
    """" Import CEJST Data:
        https://energyjustice-buildings.egs.anl.gov/resources/serve/Buildings/cejst.csv
        Headers of interest: Census tract 2010 ID, Identified as disadvantaged,
        Greater than or equal to the 90th percentile for energy burden and is low income?, Energy burden (percentile)
    """
    # Use a smaller file to test with
    if settings.EEEJ_LOAD_SMALL_TEST_DATASET:
        CEJST_DATA_PATH = os.path.join(settings.BASE_DIR, 'seed/lib/geospatial/data', 'test-cejst-1.0-communities.csv.xz')
    else:
        CEJST_DATA_PATH = os.path.join(settings.BASE_DIR, 'seed/lib/geospatial/data', 'cejst-1.0-communities.csv.xz')

    # import CEJST
    with lzma.open(CEJST_DATA_PATH, mode='rt', encoding='utf-8') as fd:
        reader = csv.reader(fd)
        col: dict[str, int] = {}
        for col_index, header in enumerate(next(reader, None)):
            col[header] = col_index

        errors = []
        for row_index, row in enumerate(reader, start=1):
            try:
                EeejCejst.objects.update_or_create(
                    census_tract_geoid=row[col['Census tract 2010 ID']],
                    dac=row[col['Identified as disadvantaged']],
                    energy_burden_low_income=row[col['Greater than or equal to the 90th percentile for energy burden and is low income?']],
                    energy_burden_percent=row[col['Energy burden (percentile)']] or None,
                    low_income=row[col['Is low income?']],
                    share_neighbors_disadvantaged=row[col['Share of neighbors that are identified as disadvantaged']] or None
                )
            except IntegrityError as e:
                errors.append("EEEJ CEJST Row already exists: {}. error: {}".format(row_index, str(e)))
            except Exception as e:
                errors.append("EEEJ CEJST - could not add row: {}. error: {}".format(row_index, str(e)))

        # print(f"{len(errors)} errors encountered when loading CEJST data")

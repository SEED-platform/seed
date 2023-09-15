import os

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db.utils import IntegrityError
from xlrd import open_workbook

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
    HUD_DATA_PATH_HOUSING = os.path.join(settings.BASE_DIR, 'seed/lib/geospatial/', 'Public_Housing_Developments.xlsx')
    HUD_DATA_PATH_MULTIFAMILY = os.path.join(settings.BASE_DIR, 'seed/lib/geospatial/', 'Multifamily_Properties_-_Assisted.xlsx')

    # header mappings
    housing_headers = {
        'tract': {'name': 'TRACT2KX', 'loc': None},
        'state': {'name': 'STATE2KX', 'loc': None},
        'county': {'name': 'CNTY2KX', 'loc': None},
        'object_id': {'name': 'OBJECTID', 'loc': None},
        'lat': {'name': 'LAT', 'loc': None},
        'lon': {'name': 'LON', 'loc': None},
        'property_name': {'name': 'PROJECT_NAME', 'loc': None}
    }
    mf_headers = {
        'tract': {'name': 'TRACT2KX', 'loc': None},
        'state': {'name': 'STATE2KX', 'loc': None},
        'county': {'name': 'CNTY2KX', 'loc': None},
        'object_id': {'name': 'OBJECTID', 'loc': None},
        'lat': {'name': 'LAT', 'loc': None},
        'lon': {'name': 'LON', 'loc': None},
        'property_name': {'name': 'PROPERTY_NAME_TEXT', 'loc': None}
    }

    # format
    header_data = [
        {'name': HousingType.PUBLIC_HOUSING, 'path': HUD_DATA_PATH_HOUSING, 'headers': housing_headers},
        {'name': HousingType.MULTIFAMILY, 'path': HUD_DATA_PATH_MULTIFAMILY, 'headers': mf_headers}
    ]
    errors = []
    for ds in header_data:

        book = open_workbook(ds['path'])
        sheet = book.sheet_by_index(0)
        for key, header in ds['headers'].items():
            for col_index in range(sheet.ncols):
                if sheet.cell(0, col_index).value == header['name']:
                    header['loc'] = col_index
                    break

        for row_index in range(1, sheet.nrows):
            try:
                # calculate census tract GEOID
                state = int(sheet.cell(row_index, ds['headers']['state']['loc']).value)
                county = int(sheet.cell(row_index, ds['headers']['county']['loc']).value)
                tract = int(sheet.cell(row_index, ds['headers']['tract']['loc']).value)
                census_tract_geoid = str(state).zfill(2) + str(county).zfill(3) + str(tract).zfill(6)

                # Unique HUD object ID
                hud_object_id = 'PH' if ds['name'] == HousingType.PUBLIC_HOUSING else 'MF'
                hud_object_id = hud_object_id + "_" + str(int(sheet.cell(row_index, ds['headers']['object_id']['loc']).value))
                # lon/lat Point
                lon = sheet.cell(row_index, ds['headers']['lat']['loc']).value
                lat = sheet.cell(row_index, ds['headers']['lon']['loc']).value
                long_lat = None
                if lon != '' and lat != '':
                    long_lat = Point(float(lon), float(lat))

                # add to DB
                obj, created = EeejHud.objects.update_or_create(
                    census_tract_geoid=census_tract_geoid,
                    hud_object_id=hud_object_id,
                    defaults={'long_lat': long_lat},
                    name=sheet.cell(row_index, ds['headers']['property_name']['loc']).value,
                    housing_type=ds['name'],
                )
            except IntegrityError as e:
                errors.append("EEEJ HUD Row already exists: {}. error: {}".format(row_index, str(e)))
                # print(str(e))

            except Exception as e:
                errors.append("EEEJ HUD - could not add row: {}. error: {}".format(row_index, str(e)))
                # print(str(e))
    print(f"{len(errors)} errors encountered when loading HUD data")


def import_cejst():
    """" Import CEJST Data:
        https://energyjustice-buildings.egs.anl.gov/resources/serve/Buildings/cejst.csv
        Headers of interest: Census tract 2010 ID, Identified as disadvantaged,
        Greater than or equal to the 90th percentile for energy burden and is low income?, Energy burden (percentile)
    """
    CEJST_DATA_PATH = os.path.join(settings.BASE_DIR, 'seed/lib/geospatial/', 'CEJST-1.0-communities-with-indicators.xlsx')

    # import CEJST
    headers = {
        'census_tract': {'name': 'Census tract 2010 ID', 'loc': None},
        'dac': {'name': 'Identified as disadvantaged', 'loc': None},
        'energy_burden_low_income': {'name': 'Greater than or equal to the 90th percentile for energy burden and is low income?', 'loc': None},
        'energy_burden_percent': {'name': 'Energy burden (percentile)', 'loc': None},
        'low_income': {'name': 'Is low income?', 'loc': None},
        'share_neighbors_disadvantaged': {'name': 'Share of neighbors that are identified as disadvantaged', 'loc': None}
    }

    book = open_workbook(CEJST_DATA_PATH)
    sheet = book.sheet_by_index(0)
    for key, header in headers.items():
        for col_index in range(sheet.ncols):
            if sheet.cell(0, col_index).value == header['name']:
                header['loc'] = col_index
                break
    errors = []

    for row_index in range(1, sheet.nrows):
        try:
            burden_percent = None
            if sheet.cell(row_index, headers['energy_burden_percent']['loc']).value != '':
                burden_percent = sheet.cell(row_index, headers['energy_burden_percent']['loc']).value

            share_neighbors_dac = None
            if sheet.cell(row_index, headers['share_neighbors_disadvantaged']['loc']).value != '':
                share_neighbors_dac = sheet.cell(row_index, headers['share_neighbors_disadvantaged']['loc']).value
            low_income = False
            if sheet.cell(row_index, headers['low_income']['loc']).value != '':
                low_income = sheet.cell(row_index, headers['low_income']['loc']).value

            obj, created = EeejCejst.objects.update_or_create(
                census_tract_geoid=sheet.cell(row_index, headers['census_tract']['loc']).value,
                dac=sheet.cell(row_index, headers['dac']['loc']).value,
                energy_burden_low_income=sheet.cell(row_index, headers['energy_burden_low_income']['loc']).value,
                energy_burden_percent=burden_percent,
                low_income=low_income,
                share_neighbors_disadvantaged=share_neighbors_dac
            )
        except IntegrityError as e:
            errors.append("EEEJ CEJST Row already exists: {}. error: {}".format(row_index, str(e)))

        except Exception as e:
            errors.append("EEEJ CEJST - could not add row: {}. error: {}".format(row_index, str(e)))
    print(f"{len(errors)} errors encountered when loading CEJST data")

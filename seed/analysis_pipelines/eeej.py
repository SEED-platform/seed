# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import logging
import urllib.parse

import requests
from celery import chain, shared_task
from django.contrib.gis.geos import Point

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    AnalysisPipelineException,
    analysis_pipeline_task,
    task_create_analysis_property_views
)
from seed.models import (
    Analysis,
    AnalysisMessage,
    AnalysisPropertyView,
    Column,
    PropertyView
)
from seed.models.eeej import EeejCejst, EeejHud

logger = logging.getLogger(__name__)

ERROR_INVALID_LOCATION = 0
ERROR_RETRIEVING_CENSUS_TRACT = 1
ERROR_NO_VALID_PROPERTIES = 2
WARNING_SOME_INVALID_PROPERTIES = 3
ERROR_NO_TRACT_OR_LOCATION = 4

EEEJ_ANALYSIS_MESSAGES = {
    ERROR_INVALID_LOCATION: 'Property missing one of Address Line 1, City & State, or Postal Code.',
    ERROR_RETRIEVING_CENSUS_TRACT: 'Unable to retrieve Census Tract for this property.',
    ERROR_NO_TRACT_OR_LOCATION: 'Property missing location or Census Tract',
    ERROR_NO_VALID_PROPERTIES: 'Analysis found no valid properties.',
    WARNING_SOME_INVALID_PROPERTIES: 'Some properties failed to validate.'
}

CENSUS_GEOCODER_URL_STUB = 'https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress?benchmark=2020&vintage=2010&format=json&address='
CENSUS_GEOCODER_URL_COORDS_STUB = 'https://geocoding.geo.census.gov/geocoder/geographies/coordinates?benchmark=2020&vintage=2010&format=json&'
TRACT_FIELDNAME = 'analysis_census_tract'

EJSCREEN_URL_STUB = 'https://ejscreen.epa.gov/mapper/EJscreen_SOE_report.aspx?namestr=&geometry={"spatialReference":{"wkid":4326},"x":LONG,"y":LAT}&distance=1&unit=9035&areatype=&areaid=&f=report'


def _get_data_for_census_tract_fetch(property_view_ids, organization):
    """Performs basic validation of the properties for running EEEJ and returns any errors
    Fetches census tract information based on address if it doesn't exist already

    :param property_view_ids
    :param organization
    :returns: dictionary[id:str], dictionary of property_view_ids to error message
    """
    # invalid_location = []
    loc_data_by_property_view = {}
    errors_by_property_view_id = {}

    # make sure the Census Tract column exists
    column, created = Column.objects.get_or_create(
        is_extra_data=True,
        column_name=TRACT_FIELDNAME,
        organization=organization,
        table_name='PropertyState',
    )
    if created:
        column.display_name = 'Census Tract'
        column.column_description = '2010 Census Tract'
        column.save()

    property_views = PropertyView.objects.filter(id__in=property_view_ids)
    for property_view in property_views:
        loc_data_by_property_view[property_view.id] = {'tract': None, 'latitude': None, 'longitude': None, 'geocoding_confidence': None, 'location': None}
        # check that we have lat/lon
        if property_view.state.latitude:
            loc_data_by_property_view[property_view.id]['latitude'] = property_view.state.latitude
        if property_view.state.longitude:
            loc_data_by_property_view[property_view.id]['longitude'] = property_view.state.longitude
        try:
            loc_data_by_property_view[property_view.id]['geocoding_confidence'] = property_view.state.geocoding_confidence
        except Exception:
            pass

        # census tract already computed?
        if TRACT_FIELDNAME in property_view.state.extra_data.keys():
            loc_data_by_property_view[property_view.id]['tract'] = property_view.state.extra_data[TRACT_FIELDNAME]
            if not loc_data_by_property_view[property_view.id]['tract']:
                # reset to None if blank so we can re-geocode
                loc_data_by_property_view[property_view.id]['tract'] = None

        if loc_data_by_property_view[property_view.id]['tract'] is None:
            # try to calculate it
            location, status = _get_location(property_view)
            if 'error' in status:
                # invalid_location.append(property_view.id)
                if property_view.id not in errors_by_property_view_id:
                    errors_by_property_view_id[property_view.id] = []
                errors_by_property_view_id[property_view.id].append(EEEJ_ANALYSIS_MESSAGES[ERROR_INVALID_LOCATION])
                del loc_data_by_property_view[property_view.id]
                continue
            # save location
            loc_data_by_property_view[property_view.id]['location'] = location

        # if both are None, error
        if loc_data_by_property_view[property_view.id]['tract'] is None \
            and loc_data_by_property_view[property_view.id]['location'] is None \
                and 'Census' not in loc_data_by_property_view[property_view.id]['geocoding_confidence'] \
                    and 'High' not in loc_data_by_property_view[property_view.id]:
            # invalid_location.append(property_view.id)
            if property_view.id not in errors_by_property_view_id:
                errors_by_property_view_id[property_view.id] = []
            errors_by_property_view_id[property_view.id].append(EEEJ_ANALYSIS_MESSAGES[ERROR_NO_TRACT_OR_LOCATION])
            del loc_data_by_property_view[property_view.id]
            continue

    return loc_data_by_property_view, errors_by_property_view_id


def _fetch_census_tract(pv_data):
    """Contacts the census geocoder service to get census tract from address or lat, lng coordinates

    :param str: pv_data, dictionary of data for a particular property view, including location and lat, lng
    :returns: list[str], list containing a census tract and status message (success or error)
    """

    # first check if we have lat/lng already with geocoding confidence of HIGH
    # prioritize geocoded lat/lng over address string, which is more error-prone

    if pv_data['latitude'] and pv_data['longitude'] and pv_data['geocoding_confidence'] and 'High' in pv_data['geocoding_confidence']:
        url = f"{CENSUS_GEOCODER_URL_COORDS_STUB}x={pv_data['longitude']}&y={pv_data['latitude']}"
    else:
        # use address string
        url = f"{CENSUS_GEOCODER_URL_STUB}{urllib.parse.quote(pv_data['location'])}"
    headers = {
        'accept': 'application/json'
    }

    try:
        response = requests.request("GET", url, headers=headers)
        if response.status_code != 200:
            logger.error(f"EEEJ Analysis: Expected 200 response from CENSUS GEOCODER service but got {response.status_code}: {response.content} for location: {pv_data['location']}")
            return None, None, None, 'error'
    except Exception as e:
        logger.error(f"EEEJ Analysis: Unexpected error retrieving census tract from CENSUS GEOCODER service {e} for location: {pv_data['location']}, error: {e}")
        return None, None, None, 'error'

    # find census tract (response format is different for lat/lng vs. location search)
    results = response.json()
    num_results = 0
    res = {}
    try:
        # try location first
        num_results = len(results['result']['addressMatches'])
        if num_results > 0:
            res = results['result']['addressMatches'][0]
    except KeyError:
        # try coordinates
        if 'result' in results:
            res = results['result']

    if 'geographies' not in res:
        logger.error(f"EEEJ Analysis: No matches from CENSUS GEOCODER service for location: {pv_data['location']}")
        return None, None, None, 'error'

    # use the first one (if more than one is returned)
    try:
        tract = res['geographies']['Census Tracts'][0]['GEOID']
        # x = longitude, y = latitude
        if 'coordinates' in res:
            longitude = res['coordinates']['x']
            latitude = res['coordinates']['y']
        else:
            # keep original
            longitude = pv_data['latitude']
            latitude = pv_data['longitude']
    except Exception as e:
        logger.error(f"EEEJ Analysis: error processing results from CENSUS GEOCODER service for location: {pv_data['location']}, error: {e}")
        return None, None, None, 'error'

    return tract, latitude, longitude, 'success'


def _get_location(property_view):
    """Retrieves the location string of a property, formatted for geocoding request

    :param analysis: property_view
    :returns: list[str], list containing a location string and status (success or error)
    """
    location = None
    # ensure we have Address Line 1 + Postal Code or Address Line 1 + City/State
    if property_view.state.address_line_1 is None:
        return location, 'error'

    location = property_view.state.address_line_1
    if property_view.state.address_line_2 is not None:
        location = location + " " + property_view.state.address_line_2

    # city/state or postal_code
    has_citystate = False
    has_zip = False
    if property_view.state.city is not None and property_view.state.state is not None:
        has_citystate = True
    if property_view.state.postal_code is not None:
        has_zip = True
    if not has_citystate and not has_zip:
        return location, 'error'

    if has_citystate:
        location = location + ", " + property_view.state.city + ", " + property_view.state.state
    if has_zip:
        location = location + ", " + property_view.state.postal_code

    # for debugging:
    # print(f" ------------ LOCATION STR: {location}")

    return location, 'success'


def _get_eeej_indicators(analysis_property_views, loc_data_by_analysis_property_view):
    """Looks up the pre-determined EEEJ indicators for a particular census tract or
    Location. If Census Tract is not already computed, use census.gov API to retrieve it.
    We are doing this during 'run_analysis' because it can take some time for retrieve
    many tracts

    :param analysis: census_tract or location (in loc_data_by_analysis_property_view)
    :returns: dict[id:str], dictionary containing indicators and their values
    """
    results = {}
    errors_by_apv_id = {}
    for apv in analysis_property_views:
        # The keys in loc_data_by_analysis_property_view will be `str` normally, or `int` if using CELERY_TASK_ALWAYS_EAGER
        key = str(apv.id) if str(apv.id) in loc_data_by_analysis_property_view else apv.id

        if loc_data_by_analysis_property_view[key]['tract'] is not None:
            tract = loc_data_by_analysis_property_view[key]['tract']
            longitude = loc_data_by_analysis_property_view[key]['longitude']
            latitude = loc_data_by_analysis_property_view[key]['latitude']
        else:
            # fetch census tract from https://geocoding.geo.census.gov/
            tract, latitude, longitude, status = _fetch_census_tract(loc_data_by_analysis_property_view[key])
            if 'error' in status:
                # invalid_location.append(apv.id)
                if apv.id not in errors_by_apv_id:
                    errors_by_apv_id[apv.id] = []
                # Note: this will be a generic error...logging the actual errors and could add those here in the future
                errors_by_apv_id[apv.id].append(EEEJ_ANALYSIS_MESSAGES[ERROR_RETRIEVING_CENSUS_TRACT])
                continue

        # lookup row in EeejCejst model
        try:
            cejst = EeejCejst.objects.get(census_tract_geoid=tract)
        except Exception:
            cejst = None

        results[apv.id] = {}
        results[apv.id]['census_tract'] = tract
        results[apv.id]['latitude'] = latitude
        results[apv.id]['longitude'] = longitude
        results[apv.id]['dac'] = None if cejst is None else cejst.dac
        results[apv.id]['energy_burden_low_income'] = None if cejst is None else cejst.energy_burden_low_income
        results[apv.id]['energy_burden_percentile'] = None if cejst is None else cejst.energy_burden_percent
        results[apv.id]['low_income'] = None if cejst is None else cejst.low_income
        results[apv.id]['share_neighbors_disadvantaged'] = None if cejst is None else cejst.share_neighbors_disadvantaged

        # lookup HUD records
        properties = EeejHud.objects.filter(census_tract_geoid=tract)
        results[apv.id]['number_affordable_housing'] = len(properties)

    return results, errors_by_apv_id


def _get_ejscreen_reports(results_by_apv, analysis_property_views):
    """Create EJScreen Report URL from https://ejscreen.epa.gov/mapper/ejscreenapi1.html
    """
    errors_by_apv_id = {}
    for apv in analysis_property_views:
        try:
            if apv.id not in results_by_apv or not results_by_apv[apv.id]['latitude'] or not results_by_apv[apv.id]['longitude']:
                # we cannot get report b/c we don't have lat/lng
                if apv.id not in errors_by_apv_id:
                    errors_by_apv_id[apv.id] = []
                errors_by_apv_id[apv.id].append('Cannot retrieve EJ Screen report URL without latitude and longitude values')
                continue

            url = EJSCREEN_URL_STUB.replace('LONG', str(results_by_apv[apv.id]['longitude'])).replace('LAT', str(results_by_apv[apv.id]['latitude']))

            if apv.id not in results_by_apv:
                results_by_apv[apv.id] = {}
            results_by_apv[apv.id]['ejscreen_report'] = url

        except Exception as e:
            if apv.id not in errors_by_apv_id:
                errors_by_apv_id[apv.id] = []
            errors_by_apv_id[apv.id].append(f'Unexpected error creating EJ SCREEN report URL: {e}')
            continue

    return results_by_apv, errors_by_apv_id


def _log_errors(errors_by_apv_id, analysis_id):
    """Log individual analysis property view errors to the analysis"""
    if errors_by_apv_id:
        for av_id in errors_by_apv_id:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=analysis_id,
                analysis_property_view_id=av_id,
                user_message="  ".join(errors_by_apv_id[av_id]),
                debug_message=''
            )


class EEEJPipeline(AnalysisPipeline):

    def _prepare_analysis(self, property_view_ids, start_analysis=True):
        # current implementation will *always* start the analysis immediately
        analysis = Analysis.objects.get(id=self._analysis_id)

        # TODO: check that we have the data we need to retrieve census tract for each property
        loc_data_by_property_view, errors_by_property_view_id = _get_data_for_census_tract_fetch(property_view_ids, analysis.organization)

        if not loc_data_by_property_view:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=self._analysis_id,
                analysis_property_view_id=None,
                user_message=EEEJ_ANALYSIS_MESSAGES[ERROR_NO_VALID_PROPERTIES],
                debug_message=''
            )
            analysis = Analysis.objects.get(id=self._analysis_id)
            analysis.status = Analysis.FAILED
            analysis.save()
            raise AnalysisPipelineException(EEEJ_ANALYSIS_MESSAGES[ERROR_NO_VALID_PROPERTIES])

        progress_data = self.get_progress_data()
        progress_data.total = 3
        progress_data.save()

        chain(
            task_create_analysis_property_views.si(self._analysis_id, property_view_ids),
            _finish_preparation.s(loc_data_by_property_view, errors_by_property_view_id, self._analysis_id),
            _run_analysis.s(self._analysis_id)
        ).apply_async()

    def _start_analysis(self):
        return None


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _finish_preparation(self, analysis_view_ids_by_property_view_id, loc_data_by_property_view, errors_by_property_view_id, analysis_id):
    pipeline = EEEJPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready('Ready to run EEEJ analysis')

    # attach errors to respective analysis_property_views
    if errors_by_property_view_id:
        for pid in errors_by_property_view_id:
            analysis_view_id = analysis_view_ids_by_property_view_id[pid]
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=analysis_id,
                analysis_property_view_id=analysis_view_id,
                user_message="  ".join(errors_by_property_view_id[pid]),
                debug_message=''
            )

    # replace property_view id with analysis_property_view id
    loc_data_by_analysis_property_view = {}
    for property_view in loc_data_by_property_view:
        analysis_view_id = analysis_view_ids_by_property_view_id[property_view]
        loc_data_by_analysis_property_view[analysis_view_id] = loc_data_by_property_view[property_view]

    return loc_data_by_analysis_property_view


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, loc_data_by_analysis_property_view, analysis_id):
    pipeline = EEEJPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step('Calculating EEEJ Indicators')
    analysis = Analysis.objects.get(id=analysis_id)

    # make sure we have the extra data columns we need, don't set the
    # displayname and description if the column already exists because
    # the user might have changed them which would re-create new columns
    # here.
    column, created = Column.objects.get_or_create(
        is_extra_data=True,
        column_name='analysis_dac',
        organization=analysis.organization,
        table_name='PropertyState',
    )
    if created:
        column.display_name = 'Disadvantaged Community'
        column.column_description = 'Property located in a Disadvantaged Community as defined by CEJST'
        column.save()

    column, created = Column.objects.get_or_create(
        is_extra_data=True,
        column_name='analysis_energy_burden_low_income',
        organization=analysis.organization,
        table_name='PropertyState',
    )
    if created:
        column.display_name = 'Energy Burden and low Income?'
        column.column_description = 'Is this property located in an energy burdened census tract. Energy Burden defined by CEJST as greater than or equal to the 90th percentile for energy burden and is low income.'
        column.save()

    column, created = Column.objects.get_or_create(
        is_extra_data=True,
        column_name='analysis_energy_burden_percentile',
        organization=analysis.organization,
        table_name='PropertyState',
    )
    if created:
        column.display_name = 'Energy Burden Percentile'
        column.column_description = 'Energy Burden Percentile as identified by CEJST'
        column.save()

    column, created = Column.objects.get_or_create(
        is_extra_data=True,
        column_name='analysis_low_income',
        organization=analysis.organization,
        table_name='PropertyState',
    )
    if created:
        column.display_name = 'Low Income?'
        column.column_description = 'Is this property located in a census tract identified as Low Income by CEJST?'
        column.save()

    column, created = Column.objects.get_or_create(
        is_extra_data=True,
        column_name='analysis_share_neighbors_disadvantaged',
        organization=analysis.organization,
        table_name='PropertyState',
    )
    if created:
        column.display_name = 'Share of Neighboring Tracts Identified as Disadvantaged'
        column.column_description = 'The percentage of neighboring census tracts that have been identified as disadvantaged by CEJST'
        column.save()

    column, created = Column.objects.get_or_create(
        is_extra_data=True,
        column_name='analysis_number_affordable_housing',
        organization=analysis.organization,
        table_name='PropertyState',
    )
    if created:
        column.display_name = 'Number of Affordable Housing Locations in Tract'
        column.column_description = 'Number of affordable housing locations (both public housing developments and multi-family assisted housing) identified by HUD in census tract'
        column.save()

    # fix the dict b/c celery messes with it when serializing
    analysis_property_view_ids = list(loc_data_by_analysis_property_view.keys())

    # prefetching property and cycle b/c .get_property_views() uses them (this is not "clean" but whatever)
    analysis_property_views = (
        AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
        .prefetch_related('property', 'cycle', 'property_state')
    )
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)

    # create and save EEEJ Indicators for each property view
    results, errors_by_apv_id = _get_eeej_indicators(analysis_property_views, loc_data_by_analysis_property_view)
    # log errors
    _log_errors(errors_by_apv_id, analysis_id)

    # EJ SCREEN (builds on top of and appends to EEEJ results)
    results, errors_by_apv_id = _get_ejscreen_reports(results, analysis_property_views)
    # log errors again
    _log_errors(errors_by_apv_id, analysis_id)

    # save results
    for analysis_property_view in analysis_property_views:
        if analysis_property_view.id not in results:
            # if not in results, means an error occurred.
            continue

        analysis_property_view.parsed_results = {
            '2010 Census Tract': results[analysis_property_view.id]['census_tract'],
            'Latitude': results[analysis_property_view.id]['latitude'],
            'Longitude': results[analysis_property_view.id]['longitude'],
            'DAC': results[analysis_property_view.id]['dac'],
            'Energy Burden and is Low Income': results[analysis_property_view.id]['energy_burden_low_income'],
            'Energy Burden Percentile': results[analysis_property_view.id]['energy_burden_percentile'],
            'Low Income': results[analysis_property_view.id]['low_income'],
            'Share of Neighboring Disadvantaged Tracts': results[analysis_property_view.id]['share_neighbors_disadvantaged'],
            'Number of Affordable Housing Locations in Tract': results[analysis_property_view.id]['number_affordable_housing'],
            'EJ Screen Report URL': results[analysis_property_view.id]['ejscreen_report'] if 'ejscreen_report' in results[analysis_property_view.id] else None
        }

        analysis_property_view.save()

        # TODO: save each indicators back to property_view
        property_view = property_views_by_apv_id[analysis_property_view.id]
        property_view.state.extra_data.update({'analysis_census_tract': results[analysis_property_view.id]['census_tract']})
        property_view.state.extra_data.update({'analysis_dac': results[analysis_property_view.id]['dac']})
        property_view.state.extra_data.update({'analysis_energy_burden_low_income': results[analysis_property_view.id]['energy_burden_low_income']})
        property_view.state.extra_data.update({'analysis_energy_burden_percentile': results[analysis_property_view.id]['energy_burden_percentile']})
        property_view.state.extra_data.update({'analysis_low_income': results[analysis_property_view.id]['low_income']})
        property_view.state.extra_data.update({'analysis_share_neighbors_disadvantaged': results[analysis_property_view.id]['share_neighbors_disadvantaged']})
        property_view.state.extra_data.update({'analysis_number_affordable_housing': results[analysis_property_view.id]['number_affordable_housing']})

        # store lat/lng (if blank) Census geocoder codes at the street address level (not Point level like mapquest)
        # store anyway but record as "Census Geocoder (L1AAA)" vs. mapquest "High (P1AAA)"
        if (not property_view.state.latitude or not property_view.state.longitude) and (property_view.state.geocoding_confidence is None or 'High' not in property_view.state.geocoding_confidence):
            # don't overwrite the mapquest geocoding
            property_view.state.latitude = results[analysis_property_view.id]['latitude']
            property_view.state.longitude = results[analysis_property_view.id]['longitude']
            property_view.state.geocoding_confidence = 'Census Geocoder (L1AAA)'
            # recalculate long_lat Point
            property_view.state.long_lat = Point(
                float(results[analysis_property_view.id]['longitude']),
                float(results[analysis_property_view.id]['latitude'])
            )

        property_view.state.save()

    # all done!
    pipeline.set_analysis_status_to_completed()

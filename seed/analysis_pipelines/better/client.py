from tempfile import TemporaryDirectory, NamedTemporaryFile
import json
import logging

import requests
import polling

from django.conf import settings

from seed.analysis_pipelines.pipeline import AnalysisPipelineException

logger = logging.getLogger(__name__)


HOST = "https://better-lbnl-development.herokuapp.com"
API_URL = f'{HOST}/api/v1'


def _better_create_portfolio(name):
    """Create a new BETTER portfolio

    :param name: str, portfolio name
    :returns: tuple(int, list[str]), portfolio id followed by list of errors
    """
    url = f'{API_URL}/portfolios/'
    data = {
        'name': name,
        'portfolio_currency': 'USD'
    }
    headers = {
        'accept': 'application/json',
        'Authorization': settings.BETTER_TOKEN,
    }

    try:
        response = requests.request("POST", url, headers=headers, data=data)
        if response.status_code == 201:
            data = response.json()
            portfolio_id = data['id']
        else:
            return None, [f'Expected 201 response from BETTER but got {response.status_code}: {response.content}']
    except Exception as e:
        return None, [f'Unexpected error creating BETTER portfolio: {e}']

    return portfolio_id, []


def _create_better_portfolio_analysis(better_portfolio_id, analysis_config):
    """Create an analysis for the portfolio.

    :param better_portfolio_id: int
    :param analysis_config: dict, Used as analysis configuration, should be structured
        according to API requirements
    :return: tuple(int, list[str]), ID of analysis followed by list of error messages
    """
    url = f'{API_URL}/portfolios/{better_portfolio_id}/analytics/'
    data = dict(analysis_config)
    data.update({'building_ids': 'ALL'})
    headers = {
        'accept': 'application/json',
        'Authorization': settings.BETTER_TOKEN,
    }

    try:
        response = requests.request("POST", url, headers=headers, data=data)
        if response.status_code == 201:
            data = response.json()
            logger.info(f'CREATED Analysis: {data}')
            analysis_id = data['id']
        else:
            return None, [f'Expected 201 response from BETTER but got {response.status_code}: {response.content}']
    except Exception as e:
        return None, [f'Unexpected error creating BETTER portfolio analysis: {e}']

    return analysis_id, []


def _get_better_portfolio_analysis_json(better_portfolio_id, better_analysis_id):
    """Get portfolio analysis as dict

    :param better_portfolio_id: int
    :param better_analysis_id: int, ID of analysis created for the portfolio
    :return: tuple(dict, list[str]), JSON response as dict followed by list of error messages
    """
    url = f'{API_URL}/portfolios/{better_portfolio_id}/analytics/{better_analysis_id}/'
    headers = {
        'accept': 'application/json',
        'Authorization': settings.BETTER_TOKEN,
    }

    try:
        response = requests.request("GET", url, headers=headers)
        if response.status_code != 200:
            return None, [f'Expected 200 response from BETTER but got {response.status_code}: {response.content}']
    except Exception as e:
        return None, [f'Unexpected error getting BETTER portfolio analysis: {e}']

    return response.json(), []


def _generate_better_portfolio_analysis_results(better_portfolio_id, better_analysis_id):
    """Start portfolio analysis and wait for it to finish.

    :param better_portfolio_id: int
    :param better_analysis_id: int, ID of analysis created for the portfolio
    :return: list[str], list of error messages
    """
    url = f'{API_URL}/portfolios/{better_portfolio_id}/analytics/{better_analysis_id}/generate/'
    headers = {
        'accept': 'application/json',
        'Authorization': settings.BETTER_TOKEN,
    }

    try:
        response = requests.request("GET", url, headers=headers)
        if response.status_code != 200:
            return [f'Expected 200 response from BETTER but got {response.status_code}: {response.content}']
    except Exception as e:
        return [f'Unexpected error generating BETTER portfolio analysis: {e}']

    # Gotta make sure the analysis is done
    def is_ready(res):
        """
        :param res: response tuple from _get_better_analysis_json
        :return: bool
        """
        response, errors = res[0], res[1]
        if errors:
            raise Exception('; '.join(errors))
        return response['generation_result'] == 'COMPLETE'

    try:
        polling.poll(
            lambda: _get_better_portfolio_analysis_json(better_portfolio_id, better_analysis_id),
            check_success=is_ready,
            timeout=60,
            step=1
        )
    except TimeoutError:
        return ['BETTER analysis timed out']
    except Exception as e:
        return [f'Unexpected error checking status of BETTER portfolio analysis: {e}']

    return []


def _get_better_portfolio_analysis_standalone_html(better_analysis_id):
    """Get portfolio analysis HTML results.

    :param better_analysis_id: int, ID of an analysis for a portfolio
    :return: tuple(tempfile.TemporaryDirectory, list[str]), temporary directory
        containing result files and list of error messages
    """
    url = f'{API_URL}/standalone_html/portfolio_analytics/{better_analysis_id}/'
    headers = {
        'accept': 'text/html',
        'Authorization': settings.BETTER_TOKEN,
    }

    try:
        response = requests.request("GET", url, headers=headers)
        if response.status_code != 200:
            return None, [f'Expected 200 response from BETTER but got {response.status_code}: {response.content}']

        standalone_html = response.text.encode('utf8').decode()
    except Exception as e:
        return None, [f'Unexpected error creating BETTER portfolio: {e}']

    # save the file from the response
    temporary_results_dir = TemporaryDirectory()
    with NamedTemporaryFile(mode='w', suffix='.html', dir=temporary_results_dir.name, delete=False) as file:
        file.write(standalone_html)

    return temporary_results_dir, []


def _better_building_service_request(bsync_xml, better_portfolio_id=None):
    """Makes request to better building endpoint using the provided file

    :param bsync_xml: str, path to BSync xml file for property
    :param better_portfolio_id: int | str, optional, if provided it will add the
        building to the portfolio
    :returns: requests.Response building_id
    """
    url = ""
    if better_portfolio_id is None:
        url = f"{API_URL}/buildings/"
    else:
        url = f"{API_URL}/portfolios/{better_portfolio_id}/buildings/"

    with open(bsync_xml, 'r') as file:
        bsync_content = file.read()

    headers = {
        'Authorization': settings.BETTER_TOKEN,
        'Content-Type': 'buildingsync/xml',
    }
    try:
        response = requests.request("POST", url, headers=headers, data=bsync_content)
        if response.status_code == 201:
            data = response.json()
            building_id = data['id']
        else:
            raise Exception(f'Received non 2xx status from BETTER: {response.status_code}: {response.content}')
    except Exception as e:
        message = 'BETTER service could not create building with the following message: {e}'.format(e=e)
        raise AnalysisPipelineException(message)

    return building_id


def _better_analysis_service_request(building_id, config):
    """Makes request to better analysis endpoint using the provided configuration

    :params: request body with building_id, savings_target, benchmark_data, min_model_r_squared
    :returns: requests.Response
    """

    url = f"{API_URL}/buildings/{building_id}/analytics/"

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': settings.BETTER_TOKEN,
    }

    try:
        response = requests.request("POST", url, headers=headers, data=json.dumps(config))
    except ConnectionError:
        message = 'BETTER service could not create analytics for this building'
        raise AnalysisPipelineException(message)

    return response


def _get_better_building_analysis_standalone_html(analysis_id):
    """Makes request to better html report endpoint using the provided analysis_id

    :params: analysis id
    :returns: tuple(tempfile.TemporaryDirectory, list[str]), temporary directory containing result files and list of error messages
    """
    url = f"{API_URL}/standalone_html/building_analytics/{analysis_id}/"

    headers = {
        'accept': '*/*',
        'Authorization': settings.BETTER_TOKEN,
    }
    try:
        response = requests.request("GET", url, headers=headers)
        standalone_html = response.text.encode('utf8').decode()

    except ConnectionError:
        message = 'BETTER service could not find the analysis'
        raise AnalysisPipelineException(message)

    # save the file from the response
    temporary_results_dir = TemporaryDirectory()
    with NamedTemporaryFile(mode='w', suffix='.html', dir=temporary_results_dir.name, delete=False) as file:
        file.write(standalone_html)

    return temporary_results_dir, []


def _better_report_json_request(better_building_id, better_analysis_id):
    """Makes request to better html report endpoint using the provided analysis_id

    :params: better_building_id
    :params: better_analysis_id
    :returns: tuple(dict, list[str]), analysis response json and error messages
    """
    url = f'{API_URL}/buildings/{better_building_id}/analytics/{better_analysis_id}/?format=json'

    headers = {
        'accept': '*/*',
        'Authorization': settings.BETTER_TOKEN,
    }
    try:
        response = requests.request("GET", url, headers=headers)
        if response.status_code != 200:
            return None, [f'BETTER analysis could not be fetched: {response.text}']
        response_json = response.json()
    except ConnectionError as e:
        message = f'Failed to connect to BETTER service: {e}'
        raise AnalysisPipelineException(message)

    return response_json, []


def _run_better_analysis(building_id, config):
    """Runs the better analysis by making a request to a better server with the
    provided configuration. Returns the analysis id for standalone html

    :param building_id: BETTER building id analysis configuration
    :param config: dict
    :returns: better_analysis_pk
    """
    try:
        response = _better_analysis_service_request(building_id, config)
    except Exception as e:
        return None, [f'Failed to make request to better server: {e}']

    if response.status_code != 201:
        return None, ['BETTER analysis could not be completed and got the following response: {message}'.format(
            message=response.text)]

    # Gotta make sure the analysis is done
    url = f"{API_URL}/buildings/{building_id}/analytics/"

    headers = {
        'accept': 'application/json',
        'Authorization': settings.BETTER_TOKEN,
    }
    try:
        response = polling.poll(
            lambda: requests.request("GET", url, headers=headers),
            check_success=lambda response: response.json()[0]['generation_result'] == 'COMPLETE',
            timeout=60,
            step=1)
    except TimeoutError:
        return None, ['BETTER analysis timed out']

    data = response.json()
    better_analysis_id = data[0]['id']
    return better_analysis_id, []

"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
import logging
import time
import urllib3

import requests
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import Column, PropertyView
from seed.utils.api import api_endpoint_class

import xmltodict
from datetime import datetime
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from seed.utils.api_schema import AutoSchemaHelper

_log = logging.getLogger(__name__)


class PMError(Exception):
    pass


class PortfolioManagerSerializer(serializers.Serializer):
    pass


class PortfolioManagerViewSet(GenericViewSet):
    """
    This ViewSet contains four API views: /template_list/, /report/, /download/, and /custom_download/ that are used to interface SEED with ESPM
    """

    serializer_class = PortfolioManagerSerializer

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory(
            {"username": "string", "password": "string"}, description="ESPM account credentials.", required=["username", "password"]
        ),
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "templates": [{"template_information_1": "string", "template_information_2": "integer", "[other keys...]": "string"}],
                    "message": "string",
                }
            ),
        },
    )
    @action(detail=False, methods=["POST"])
    def template_list(self, request):
        """
        This API view makes a request to ESPM for the list of available report templates, including root templates and
        child data requests.
        ---
        This API responds with a JSON object with two keys: status, which will be a string -
        either error or success.  If successful, a second key, templates, will hold the list of templates from ESPM. If
        not successful, a second key, message, will include an error description that can be presented on the UI.
        """
        if "username" not in request.data:
            return JsonResponse(
                {"status": "error", "message": "Invalid call to PM worker: missing username for PM account"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if "password" not in request.data:
            return JsonResponse(
                {"status": "error", "message": "Invalid call to PM worker: missing password for PM account"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        username = request.data["username"]
        password = request.data["password"]
        pm = PortfolioManagerImport(username, password)
        try:
            possible_templates = pm.get_list_of_report_templates()
        except PMError as pme:
            return JsonResponse({"status": "error", "message": str(pme)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse({"status": "success", "templates": possible_templates})

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory(
            {
                "username": "string",
                "password": "string",
                "template": {"[copy information from template_list]": "string"},
                "report_format": "string",
            },
            description="ESPM account credentials.",
            required=["username", "password", "template"],
        ),
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "properties": [
                        {"properties_information_1": "string", "properties_information_2": "integer", "[other keys...]": "string"}
                    ],
                    "message": "string",
                }
            ),
        },
    )
    @action(detail=False, methods=["POST"])
    def report(self, request):
        """
        This API view makes a request to ESPM to generate and download a report based on a specific template.
        ---
        This API responds with a JSON object with two keys: status, which will be a string -
        either error or success.  If successful, a second key, properties, will hold the list of properties found in
        this generated report.  If not successful, a second key, message, will include an error description that can be
        presented on the UI.
        """

        if "username" not in request.data:
            _log.debug("Invalid call to PM worker: missing username for PM account: %s" % str(request.data))
            return JsonResponse(
                {"status": "error", "message": "Invalid call to PM worker: missing username for PM account"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if "password" not in request.data:
            _log.debug("Invalid call to PM worker: missing password for PM account: %s" % str(request.data))
            return JsonResponse(
                {"status": "error", "message": "Invalid call to PM worker: missing password for PM account"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if "template" not in request.data:
            _log.debug("Invalid call to PM worker: missing template for PM account: %s" % str(request.data))
            return JsonResponse(
                {"status": "error", "message": "Invalid call to PM worker: missing template for PM account"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = request.data["username"]
        password = request.data["password"]
        template = request.data["template"]
        # report format defaults to XML if not provided
        report_format = request.data.get("report_format", "XML")

        pm = PortfolioManagerImport(username, password)
        try:
            try:
                if "z_seed_child_row" not in template:
                    _log.debug("Invalid template formulation during portfolio manager data import: %s" % str(template))
                    return JsonResponse(
                        {"status": "error", "message": "Invalid template formulation during portfolio manager data import"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if template["z_seed_child_row"]:
                    content = pm.generate_and_download_child_data_request_report(template, report_format)
                else:
                    content = pm.generate_and_download_template_report(template, report_format)
            except PMError as pme:
                _log.debug(f"{pme!s}: {template!s}")
                return JsonResponse({"status": "error", "message": str(pme)}, status=status.HTTP_400_BAD_REQUEST)

            if report_format == "EXCEL":
                try:
                    # return the Excel file
                    filename = "pm_report_export.xlsx"
                    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    response["Content-Disposition"] = f'attachment; filename="{filename}"'
                    response.write(content)
                    return response

                except Exception as e:
                    _log.debug("ERROR downloading EXCEL report: %s" % str(e))
                    return JsonResponse(
                        {"status": "error", "message": "Malformed XML from template download"}, status=status.HTTP_400_BAD_REQUEST
                    )

            # rest is for XML reports
            try:
                content_object = xmltodict.parse(content, dict_constructor=dict)

            except Exception:  # catch all because xmltodict doesn't specify a class of Exceptions
                _log.debug("Malformed XML from template download: %s" % str(content))
                return JsonResponse(
                    {"status": "error", "message": "Malformed XML from template download"}, status=status.HTTP_400_BAD_REQUEST
                )
            try:
                if content_object.get("report", None) is not None:
                    success, properties = pm._parse_properties_v1(content_object)
                else:
                    # assume that v2 is the correct version now
                    success, properties = pm._parse_properties_v2(content_object)
                if not success:
                    return JsonResponse({"status": "error", "message": properties}, status=status.HTTP_400_BAD_REQUEST)

            except (KeyError, TypeError):
                _log.debug(
                    "Processed template successfully, but missing keys -- is the report empty on Portfolio Manager?: %s"
                    % str(content_object)
                )
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Processed template successfully, but missing keys -- is the report empty on Portfolio Manager?",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return JsonResponse({"status": "success", "properties": properties})
        except Exception as e:
            _log.debug(f"{e}: {request.data!s}")
            return JsonResponse({"status": "error", "message": e}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_integer_field("id", True, "ID of the ESPM Property to download")],
        request_body=AutoSchemaHelper.schema_factory(
            {
                "username": "string",
                "password": "string",
                "filename": "string",
            },
            description="ESPM account credentials.",
            required=["username", "password"],
        ),
    )
    @action(detail=True, methods=["POST"])
    def download(self, request, pk):
        """Download a single property report from Portfolio Manager. The PK is the
        PM property ID that is on ESPM"""
        if "username" not in request.data:
            _log.debug("Invalid call to PM worker: missing username for PM account: %s" % str(request.data))
            return JsonResponse(
                {"status": "error", "message": "Invalid call to PM worker: missing username for PM account"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if "password" not in request.data:
            _log.debug("Invalid call to PM worker: missing password for PM account: %s" % str(request.data))
            return JsonResponse(
                {"status": "error", "message": "Invalid call to PM worker: missing password for PM account"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = request.data["username"]
        password = request.data["password"]
        if "filename" not in request.data:
            filename = f'pm_{pk}_{datetime.strftime(datetime.now(), "%Y%m%d_%H%M%S")}.xlsx'
        else:
            filename = request.data["filename"]

        pm = PortfolioManagerImport(username, password)
        try:
            content = pm.return_single_property_report(pk)

            # return the excel file as the HTTP response
            response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            response.write(content)
            return response

        except PMError as pme:
            _log.debug(f"{pme!s}: PM Property ID {pk}")
            return JsonResponse({"status": "error", "message": str(pme)}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory(
            {
                "username": "string",
                "password": "string",
                "property_ids": ['string'],
            },
            description="ESPM (Energy Star Portfolio Manager) account credentials and property IDs to generate report for.",
            required=["username", "password", "property_ids"],
        ),
        responses={
            200: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            400: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "message": "string",
                },
                description="Returned when request validation fails or required fields are missing"
            ),
            500: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "message": "string",
                },
                description="Returned when an unexpected error occurs"
            ),
        },
    )
    @action(detail=False, methods=["POST"])
    def custom_download(self, request):
        """
        This API view makes a request to ESPM to generate and download a custom download for the selected property IDs.
        ---
        This API responds with a JSON object with two keys: status, which will be a string -
        either error or success.  If successful, a second key, properties, will hold the list of properties found in
        this generated report.  If not successful, a second key, message, will include an error description that can be
        presented on the UI.
        """

        if "username" not in request.data:
            _log.debug("Invalid call to PM worker: missing username for PM account: %s" % str(request.data))
            return JsonResponse(
                {"status": "error", "message": "Invalid call to PM worker: missing username for PM account"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if "password" not in request.data:
            _log.debug("Invalid call to PM worker: missing password for PM account: %s" % str(request.data))
            return JsonResponse(
                {"status": "error", "message": "Invalid call to PM worker: missing password for PM account"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if "property_ids" not in request.data:
            _log.debug("Invalid call to PM worker: missing property ids for PM account: %s" % str(request.data))
            return JsonResponse(
                {"status": "error", "message": "Invalid call to PM worker: missing property ids for PM account"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = request.data["username"]
        password = request.data["password"]
        property_ids = request.data["property_ids"]

        pm = PortfolioManagerImport(username, password)
        try:
            try:
                content = pm.generate_and_download_meter_data(property_ids)
            except PMError as pme:
                _log.debug(f"{pme!s}: {property_ids!s}")
                return JsonResponse({"status": "error", "message": str(pme)}, status=status.HTTP_400_BAD_REQUEST)

            try:
                # return the Excel file
                filename = "pm_report_export.xlsx"
                response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
                response.write(content)
                return response

            except Exception as e:
                _log.debug("ERROR downloading EXCEL report: %s" % str(e))
                return JsonResponse(
                    {"status": "error", "message": "Malformed XML from template download"}, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            _log.error("Unexpected error: %s" % str(e))
            return JsonResponse({"status": "error", "message": "An unexpected error occurred"}, status=500)

# TODO: Move this object to /seed/utils/portfolio_manager.py
class PortfolioManagerImport:
    """This class is essentially a wrapper around the ESPM login/template/report operations"""

    def __init__(self, m_username, m_password):
        """To instantiate this class, provide ESPM username and password.  Currently, this constructor doesn't do anything
        except store the credentials.

        :param m_username: The ESPM username
        :param m_password: The ESPM password
        """

        # store the original, unmodified versions -- DO NOT ENCODE THESE
        self.username = m_username
        self.password = m_password
        self.authenticated_headers = None
        self.session = None
        _log.debug("Created PortfolioManagerManager for username: %s" % self.username)

        # vars for the URLs if they are used in more than one place.
        self.REPORT_URL = "https://portfoliomanager.energystar.gov/pm/reports/reportData/MY_REPORTS_AND_TEMPLATES"
        # The root URL for downloading the report, code will add the template ID and the XML
        self.DOWNLOAD_REPORT_URL = "https://portfoliomanager.energystar.gov/pm/reports/download"

        self.DOWNLOAD_SINGLE_PROPERTY_REPORT_URL = "https://portfoliomanager.energystar.gov/pm/property"

        # The url for custom downloads, useful for downloading meter data
        self.DOWNLOAD_CUSTOM_REPORT_URL = "https://portfoliomanager.energystar.gov/pm/property/createCustomDownloadSubmit/"

    def login_and_set_cookie_header(self):
        """This method calls out to ESPM to perform a login operation and get a session authentication token.  This token
        is then stored in the proper form to allow authenticated calls into ESPM.

        :return: None
        """

        # Create a session to maintain cookies
        session = requests.Session()
        
        # First we need to get the login page to get any CSRF tokens
        try:
            login_page = session.get("https://portfoliomanager.energystar.gov/pm/login", timeout=300)
            if login_page.status_code != 200:
                raise PMError(f"Failed to load login page: {login_page.status_code}")
        except requests.exceptions.RequestException as e:
            raise PMError(f"Error accessing login page: {str(e)}")

        # Now log in to Portfolio Manager
        login_url = "https://portfoliomanager.energystar.gov/pm/j_spring_security_check"
        payload = {"j_username": self.username, "j_password": self.password}
        try:
            response = session.post(login_url, data=payload, timeout=300, allow_redirects=True)
        except requests.exceptions.SSLError:
            raise PMError("SSL Error in Portfolio Manager Query; check VPN/Network/Proxy.")
        except requests.exceptions.RequestException as e:
            raise PMError(f"Error during login: {str(e)}")

        # Check for failed login
        if "The username and/or password you entered is not correct" in response.text:
            raise PMError("Login failed: Invalid credentials")
            
        # Verify we're actually logged in by checking the response URL or content
        if "/pm/login" in response.url or "Sign In to ENERGY STAR Portfolio Manager" in response.text:
            raise PMError("Login failed: Redirected back to login page")

        # Get all cookies from the session
        cookies = "; ".join([f"{cookie.name}={cookie.value}" for cookie in session.cookies])
        if not cookies:
            raise PMError("No cookies received after login")

        # Store the cookies and session for future requests
        self.authenticated_headers = {
            "Cookie": cookies,
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest"
        }
        self.session = session

    def _make_request_with_retry(self, method, url, **kwargs):
        """Make a request with retry logic for connection issues.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            **kwargs: Additional arguments to pass to requests

        Returns:
            requests.Response object

        Raises:
            PMError: If the request fails after retries
        """
        max_retries = 3
        retry_delay = 2
        session = requests.Session()

        # Configure retries with backoff
        retry_strategy = urllib3.util.Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
            raise_on_status=False
        )

        # Use more conservative connection settings
        adapter = requests.adapters.HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=1,
            pool_maxsize=1,
            pool_block=True
        )
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        # Add conservative request headers
        default_headers = {
            'Connection': 'close',  # Don't keep connections alive
            'Accept-Encoding': 'identity',  # Disable compression
        }
        if 'headers' in kwargs:
            kwargs['headers'].update(default_headers)
        else:
            kwargs['headers'] = default_headers

        for attempt in range(max_retries):
            try:
                response = session.request(method, url, **kwargs)

                # Check if we got redirected to login
                if "/pm/login" in response.url:
                    session.close()
                    if attempt < max_retries - 1:
                        _log.debug("Session expired, attempting to re-login")
                        self.login_and_set_cookie_header()
                        continue
                    else:
                        raise PMError("Session expired and re-login attempts failed")

                # For streaming responses, we need to read the content before checking status
                if kwargs.get('stream', False):
                    try:
                        # First try with streaming
                        content = []
                        for chunk in response.iter_content(chunk_size=8192, decode_unicode=False):
                            if chunk:
                                content.append(chunk)
                        response._content = b''.join(content)
                    except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError) as e:
                        # If streaming fails, try to get the content directly
                        try:
                            response.raw.decode_content = True
                            content = response.raw.read()
                            if content:
                                response._content = content
                                return response
                        except Exception as raw_e:
                            _log.warning(f"Failed to read raw content: {raw_e}")

                        session.close()
                        if attempt < max_retries - 1:
                            _log.debug(f"Streaming failed with {str(e)}, retrying in {retry_delay} seconds")
                            # Disable streaming for retry attempts
                            kwargs['stream'] = False
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        raise PMError(f"Streaming failed after {max_retries} attempts: {str(e)}")

                # Check response status
                if response.status_code >= 400:
                    session.close()
                    if attempt < max_retries - 1 and response.status_code in retry_strategy.status_forcelist:
                        _log.debug(f"Request failed with status {response.status_code}, retrying in {retry_delay} seconds")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    raise PMError(f"Request failed with status {response.status_code}: {response.text}")

                return response

            except requests.exceptions.RequestException as e:
                session.close()
                if attempt < max_retries - 1:
                    _log.debug(f"Request failed with {str(e)}, retrying in {retry_delay} seconds")
                    # Disable streaming for retry attempts if it was a streaming error
                    if isinstance(e, (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError)):
                        kwargs['stream'] = False
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise PMError(f"Request failed after {max_retries} attempts: {str(e)}")
            finally:
                session.close()

    def get_list_of_report_templates(self):
        """New method to support update to ESPM

        :return: Returns a list of template objects. All rows will have a z_seed_child_row key that is False for main
        rows and True for child rows
        """
        # login if needed
        if not self.authenticated_headers:
            self.login_and_set_cookie_header()

        # get the report data
        try:
            json_authenticated_headers = self.authenticated_headers.copy()
            json_authenticated_headers["Accept"] = "application/json"
            json_authenticated_headers["Content-Type"] = "application/json"
            response = self._make_request_with_retry("GET", self.REPORT_URL, headers=json_authenticated_headers, timeout=300)

        except requests.exceptions.SSLError:
            raise PMError("SSL Error in Portfolio Manager Query; check VPN/Network/Proxy.")
        if not response.status_code == status.HTTP_200_OK:
            raise PMError("Unsuccessful response from report template rows query; aborting.")

        # This endpoint now is JSON and not encoded JSON string. So just return the JSON.
        template_object = response.json()

        # We need to parse the list of report templates
        if "reportTabData" not in template_object:
            raise PMError("Could not find reportTabData key in template response; aborting.")
        templates = template_object["reportTabData"]
        template_response = []
        sorted_templates = sorted(templates, key=lambda x: x["name"])
        for t in sorted_templates:
            t["z_seed_child_row"] = False
            t["display_name"] = t["name"]
            template_response.append(t)
            if "id" not in t or "name" not in t:
                _log.debug("Template from Portfolio Manager was missing id or name field")
                continue
            _log.debug("Found template,\n id=" + str(t["id"]) + "\n name=" + str(t["name"]))
            if t.get("hasChildrenRows"):
                _log.debug("Template row has children data request rows, trying to get them now")
                children_url = f'https://portfoliomanager.energystar.gov/pm/reports/templateChildrenRows/TEMPLATE/{t["id"]}'

                # SSL errors would have been caught earlier in this function and raised, so this should be ok
                children_response = self._make_request_with_retry("GET", children_url, headers=self.authenticated_headers, timeout=300)
                if not children_response.status_code == status.HTTP_200_OK:
                    raise PMError("Unsuccessful response from child row template lookup; aborting.")
                try:
                    # the data are now in the string of the data key of the returned dictionary with an excessive amount of
                    # escaped double quotes.
                    # e.g., response = {"data": "{"customReportsData":"..."}"}
                    decoded = json.loads(children_response.text)  # .encode('utf-8').decode('unicode_escape')

                    # the beginning and end of the string needs to be without the doublequote. Remove the escaped double quotes
                    data_to_parse = (
                        decoded["data"]
                        .replace('"{', "{")
                        .replace('}"', "}")
                        .replace('"[{', "[{")
                        .replace('}]"', "}]")
                        .replace('\\"', '"')
                        .replace('"[]"', "[]")
                    )

                    # print(f'data to parse: {data_to_parse}')
                    child_object = json.loads(data_to_parse)["childrenRows"]
                except ValueError:
                    raise PMError("Malformed JSON response from report template child row query; aborting.")
                _log.debug("Received the following child JSON return: " + json.dumps(child_object, indent=2))
                for child_row in child_object:
                    child_row["z_seed_child_row"] = True
                    child_row["display_name"] = f"  -  {child_row['name']}"
                    template_response.append(child_row)
        return template_response

    def get_template_by_name(templates, template_name):
        """
        This method searches through a list of templates for a template that matches the specific template name

        :param templates: A list of template objects, each of which will have a name key
        :param template_name: A string name to match in the list of templates
        :return: Returns a single template object that matches the name, raises a PMExcept if no match
        """

        # Then we need to pick a single report template by name, eventually this is defined by the PM user
        matched_template = next((t for t in templates if t["name"] == template_name), None)
        if not matched_template:
            raise PMError("Could not find a matching template for this name, try a different name")
        _log.debug("Desired report name found, template info: " + json.dumps(matched_template, indent=2))
        return matched_template

    # TODO: Is there a need to call just this instead of generate_and_download...?
    def update_template_report(self, template, start_month, start_year, end_month, end_year, property_ids):
        """This method calls out to ESPM to (re)generate a specific template

        :param template: A specific template object
        :param start_month: reporting period start month
        :param start_year: reporting period start year
        :param end_month: reporting period end month
        :param end_year: reporting period end year
        :property_ids: list of property ids to include in report
        :return: TODO
        """
        # login if needed
        if not self.authenticated_headers:
            self.login_and_set_cookie_header()

        template_report_id = template["id"]
        update_report_url = f"https://portfoliomanager.energystar.gov/pm/reports/generateData/{template_report_id}"

        new_authenticated_headers = self.authenticated_headers.copy()
        new_authenticated_headers["Content-Type"] = "application/x-www-form-urlencoded"

        try:
            response = self._make_request_with_retry("POST", update_report_url, headers=self.authenticated_headers, timeout=300)
        except requests.exceptions.SSLError:
            raise PMError("SSL Error in Portfolio Manager Query; check VPN/Network/Proxy.")
        if not response.status_code == status.HTTP_200_OK:
            raise PMError("Unsuccessful response from POST to update report; aborting.")
        _log.debug(f"Triggered report update,\n status code={response.status_code}\n response headers={response.headers!s}")

        return response.content

    def generate_and_download_template_report(self, matched_template, report_format="XML"):
        """
        This method calls out to ESPM to trigger generation of a report for the supplied template.  The process requires
        calling out to the generateData/ endpoint on ESPM, followed by a waiting period for the template status to be
        updated to complete.  Once complete, a download URL allows download of the report in XML or EXCEL format.

        This response content can be enormous, so ...
        TODO: Evaluate whether we should just download this XML to file here.  It would require re-reading the file
        TODO: afterwards, but it would 1) be downloaded and available for inspection/debugging, and 2) reduce the size
        TODO: of data coming through in memory during these calls, which seems to have been problematic at times

        :param matched_template: A template object down-selected from the full list found using the /template_list/ API
        :return: Full XML data report from ESPM report generation and download process
        """

        # login if needed
        if not self.authenticated_headers:
            self.login_and_set_cookie_header()

        # We should then trigger generation of the report we selected
        template_report_id = matched_template["id"]
        generation_url = f"https://portfoliomanager.energystar.gov/pm/reports/generateData/{template_report_id}"
        try:
            response = self._make_request_with_retry("POST", generation_url, headers=self.authenticated_headers, timeout=300)
        except requests.exceptions.SSLError:
            raise PMError("SSL Error in Portfolio Manager Query; check VPN/Network/Proxy.")
        if not response.status_code == status.HTTP_200_OK:
            raise PMError("Unsuccessful response from POST to trigger report generation; aborting.")
        _log.debug(f"Triggered report generation,\n status code={response.status_code}\n response headers={response.headers!s}")

        # Now we need to wait while the report is being generated
        attempt_count = 0
        report_generation_complete = False
        while attempt_count < 90:
            attempt_count += 1

            # get the report data
            try:
                json_authenticated_headers = self.authenticated_headers.copy()
                json_authenticated_headers["Accept"] = "application/json"
                json_authenticated_headers["Content-Type"] = "application/json"
                response = self._make_request_with_retry("GET", self.REPORT_URL, headers=json_authenticated_headers, timeout=300)
            except requests.exceptions.SSLError:
                raise PMError("SSL Error in Portfolio Manager Query; check VPN/Network/Proxy.")
            if not response.status_code == status.HTTP_200_OK:
                raise PMError("Unsuccessful response from report template rows query; aborting.")

            template_objects = response.json()["reportTabData"]
            for t in template_objects:
                if "id" in t and t["id"] == template_report_id:
                    this_matched_template = t
                    break
            else:
                this_matched_template = None
            if not this_matched_template:
                raise PMError("Could not find a match for this report template id... odd at this point")
            if this_matched_template["pending"] == 1:
                time.sleep(2)
                continue
            else:
                report_generation_complete = True
                break

        if report_generation_complete:
            _log.debug("Report appears to have been generated successfully (attempt_count=" + str(attempt_count) + ")")
        else:
            raise PMError("Template report not generated successfully; aborting.")

        # Finally we can download the generated report
        try:
            response = self._make_request_with_retry("GET", self.download_url(template_report_id, report_format), headers=self.authenticated_headers, timeout=300)
        except requests.exceptions.SSLError:
            raise PMError("SSL Error in Portfolio Manager Query; check VPN/Network/Proxy.")
        if response.status_code != status.HTTP_200_OK:
            error_message = "Unsuccessful response from GET trying to download generated report;"
            error_message += f' Generated report name: {matched_template["name"]};'
            error_message += f"Tried to download report from URL: {self.download_url(template_report_id)};"
            error_message += f"Returned with a status code = {response.status_code};"
            raise PMError(error_message)
        return response.content

    def generate_and_download_child_data_request_report(self, matched_data_request, report_format="XML"):
        """
        Updated for recent update of ESPM

        This method calls out to ESPM to get the report data for a child template (a data request).  For child
        templates, the process simply requires calling out the download URL and getting the data in XML format.

        This response content can be enormous, so the same message applies here as with the main report download method
        where we should consider downloading the file itself instead of passing the XML data around in memory.

        :param matched_data_request: A child template object (template where z_seed_child_row is True)
        :param report_format
        :return: Full XML data report from ESPM report generation and download process
        """

        # login if needed
        if not self.authenticated_headers:
            self.login_and_set_cookie_header()

        # Generate the url to download this file
        try:
            response = self._make_request_with_retry(
                "GET",
                self.download_url(matched_data_request["id"], report_format),
                headers=self.authenticated_headers,
                allow_redirects=True,
                timeout=300,
            )
        except requests.exceptions.SSLError:
            raise PMError("SSL Error in Portfolio Manager Query; check VPN/Network/Proxy.")

        if not response.status_code == status.HTTP_200_OK:
            raise PMError("Unsuccessful response from GET trying to download generated report; aborting.")

        return response.content

    def return_single_property_report(self, pm_property_id: int):
        """Return (in memory) a single property report from ESPM based on the passed
        ESPM Property ID (SEED calls this the pm_property_id). This method returns
        the XLSX file in memory with all the tabs for the single property.

        This method differs from the others in that this it does not need to know
        the template of the report, it is simply the entire ESPM record (meters and all).

        Args:
            pm_property_id (int): The ESPM Property ID to download.

        Returns:
            str: Content of an XLSX file which will need to be persisted
        """
        # login if needed
        if not self.authenticated_headers:
            self.login_and_set_cookie_header()

        # Generate the url to download this file
        try:
            response = self._make_request_with_retry(
                "GET",
                self.download_url_single_report(pm_property_id), headers=self.authenticated_headers, allow_redirects=True, timeout=300
            )

            if response.status_code == status.HTTP_200_OK:
                return response.content
            else:
                raise PMError("Unsuccessful response from GET trying to download single report; aborting.")

        except requests.exceptions.SSLError:
            raise PMError("SSL Error in Portfolio Manager Query; check VPN/Network/Proxy.")

    def generate_and_download_meter_data(self, property_ids, download_format="XML"):
        """
        This method calls out to ESPM to trigger generation of a custom download of energy and water meter data for the supplied list of property ids.  The process requires
        calling out to the createCustomDownloadSubmit/ endpoint on ESPM, followed by a waiting period for the custom download status to be
        updated to complete.  Once complete, a download URL allows download of the meter data in XML or EXCEL format.
        TODO: Add start and end date parameters


        :param property_ids: list of property ids to include in custom download
        :param download_format: Format to download the data in (XML or EXCEL)
        :return: Full data report from ESPM custom download generation and download process
        :raises PMError: If the download fails or times out
        """
        if not property_ids:
            raise PMError("No property IDs provided for meter data download")

        # Force a fresh login to ensure we have a valid session
        self.login_and_set_cookie_header()

        try:
            # Initial page load - no streaming needed
            download_page = self._make_request_with_retry(
                "GET",
                "https://portfoliomanager.energystar.gov/pm/property/reports/dataRequest/create",
                headers=self.authenticated_headers,
                timeout=300,
                stream=False
            )

            # Build the payload with proper URL encoding
            payload = {
                "proID": "",
                "numberOfPropertiesWithinLimit": "true",
                "basicPropertyInfoCount": "0",
                "propertyIdentifierCount": "0",
                "propertyUseCount": "0",
                "propertyUseDetailCount": "0",
                "meterCount": "0",
                "meterDataCount": "29403",
                "onsiteCount": "0",
                "offsiteCount": "0",
                "energyProjectsCount": "0",
                "designDataCount": "0",
                "targetAndBaselineCount": "0",
                "maxPropertiesCountAsyncDownload": "12000",
                "selectionType": "MULTIPLE",
                "_basicPropertyInfo": "on",
                "_propertyIds": "on",
                "_propertyUses": "on",
                "_propertyUseDetails": "on",
                "_meterType": "on",
                "_energyMeter": "on",
                "_waterMeter": "on",
                "_wasteMeter": "on",
                "_itEnergyMeter": "on",
                "_plantFlowMeter": "on",
                "_aggregateMeter": "on",
                "meterEntries": "true",
                "_meterEntries": "on",
                "energyMeterEntries": "true",
                "_energyMeterEntries": "on",
                "waterMeterEntries": "true",
                "_waterMeterEntries": "on",
                "_wasteMeterEntries": "on",
                "_itEnergyMeterEntries": "on",
                "_plantFlowMeterEntries": "on",
                "customDownloadStartDate": "01/01/2007",
                "customDownloadEndDate": "12/31/2023",
                "includeInactiveMeters": "true",
                "includeUnassociatedMeters": "false",
                "_onsiteRecOwnership": "on",
                "_offsitePurchase": "on",
                "_energyProjects": "on",
                "_designData": "on",
                "_designUseDesignData": "on",
                "_designUseDetailDesignData": "on",
                "_energyDesignData": "on",
                "_designTargetsDesignData": "on",
                "_targetAndBaseline": "on",
                "selectedPropertyIdsAsString": "%".join([str(p_id) for p_id in property_ids])
            }

            # Submit custom download request - no streaming needed
            generation_url = "https://portfoliomanager.energystar.gov/pm/property/createCustomDownloadSubmit/"
            response = self._make_request_with_retry(
                "POST",
                generation_url,
                headers={
                    **self.authenticated_headers,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": "https://portfoliomanager.energystar.gov/pm/property/reports/dataRequest/create",
                    "Accept": "application/json, text/plain, */*"
                },
                data=payload,
                timeout=300,
                stream=False
            )

            if response.status_code == 500:
                error_msg = "Portfolio Manager server error (500)."
                if response.text:
                    if "<!DOCTYPE html>" in response.text:
                        raise PMError("Authentication error. Please try logging in again.")
                    else:
                        error_msg += f" Details: {response.text[:200]}"
                raise PMError(error_msg)

            if response.status_code != status.HTTP_200_OK:
                raise PMError(f"Failed to generate report: {response.status_code} - {response.text}")

            # Poll for report completion - no streaming needed
            max_attempts = 90
            attempt_count = 0
            poll_interval = 5

            while attempt_count < max_attempts:
                attempt_count += 1
                
                try:
                    # Poll notifications - no streaming needed
                    notifications_response = self._make_request_with_retry(
                        "POST",
                        "https://portfoliomanager.energystar.gov/pm/notifications.json",
                        headers={
                            **self.authenticated_headers,
                            "Content-Type": "application/json",
                        },
                        data='{"page":1,"pageSize":100,"sort":{"column":"CREATE_DATE","ascending":true},"type":"Notices"}',
                        timeout=30,
                        stream=False
                    )

                    if notifications_response.status_code != status.HTTP_200_OK:
                        _log.warning(f"Failed to get notifications: {notifications_response.status_code}")
                        time.sleep(poll_interval)
                        continue

                    try:
                        notifications_data = notifications_response.json()
                        if not notifications_data.get("result", {}).get("items"):
                            time.sleep(poll_interval)
                            continue

                        latest_notification = notifications_data["result"]["items"][-1]
                        if latest_notification["notificationTypeCode"]["code"] == "CUSTOMPORTFOLIODOWNLOAD":
                            break
                    except (ValueError, KeyError) as e:
                        _log.warning(f"Failed to parse notifications response: {e}")
                        time.sleep(poll_interval)
                        continue

                except requests.exceptions.RequestException as e:
                    _log.warning(f"Request failed: {e}")
                    time.sleep(poll_interval)
                    continue

            if attempt_count >= max_attempts:
                raise PMError("Timed out waiting for report generation to complete")

            # Download the final report with multiple strategies
            custom_download_url = "https://portfoliomanager.energystar.gov/pm" + latest_notification["notificationParameters"][1]["url"]
            
            # Try direct download first without streaming
            try:
                _log.debug("Attempting direct download without streaming")
                response = self._make_request_with_retry(
                    "GET",
                    custom_download_url,
                    headers={
                        **self.authenticated_headers,
                        'Connection': 'close',
                        'Accept-Encoding': 'identity',
                        'Accept': '*/*',
                        'User-Agent': 'SEED Platform'
                    },
                    stream=False,
                    timeout=300
                )
                try:
                    return response.content
                except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError) as e:
                    _log.warning(f"Direct content access failed: {e}")
                    # Try to read the raw response
                    try:
                        response.raw.decode_content = True
                        return response.raw.read()
                    except Exception as raw_e:
                        _log.warning(f"Raw content access failed: {raw_e}")
            except Exception as e:
                _log.warning(f"Direct download failed: {e}")
            
            time.sleep(5)  # Wait before trying streaming
            
            # Try with very conservative streaming
            try:
                _log.debug("Attempting conservative streaming download")
                response = self._make_request_with_retry(
                    "GET",
                    custom_download_url,
                    headers={
                        **self.authenticated_headers,
                        'Connection': 'close',
                        'Accept-Encoding': 'identity',
                        'Accept': '*/*',
                        'User-Agent': 'SEED Platform'
                    },
                    stream=True,
                    timeout=300
                )
                
                # Read the entire response into memory first
                response.raw.decode_content = True
                content = response.raw.read()
                if content:
                    return content
                
                # If raw read fails, try manual chunking
                content = []
                chunk_size = 1024  # Start with very small chunks
                for chunk in response.iter_content(chunk_size=chunk_size, decode_unicode=False):
                    if chunk:
                        content.append(chunk)
                        if len(content) * chunk_size > 100 * 1024 * 1024:  # 100MB limit
                            raise PMError("Download size exceeded safety limit")
                return b''.join(content)
            except Exception as e:
                _log.warning(f"Streaming download failed: {e}")
                time.sleep(5)
            
            # Final attempt with minimal configuration
            try:
                _log.debug("Final attempt: direct download with minimal headers")
                response = requests.get(
                    custom_download_url,
                    headers={
                        **self.authenticated_headers,
                        'Connection': 'close',
                        'Accept-Encoding': 'identity',
                        'Accept': '*/*'
                    },
                    timeout=300,
                    verify=True,
                    allow_redirects=True
                )
                response.raise_for_status()
                return response.content
            except Exception as e:
                raise PMError(f"All download attempts failed. Last error: {str(e)}")
        except PMError as e:
            raise e
    def _parse_properties_v1(self, xml):
        """Parse the XML (in dict format) response from the ESPM API and return a list of
        properties. This version was implemented prior to 02/13/2023

        Args:
            xml (dict): content to be parsed

        Returns:
            (valid, properties): success and list of properties, or failure and error message
        """
        try:
            possible_properties = xml["report"]["informationAndMetrics"]["row"]
            if isinstance(possible_properties, list):
                properties = possible_properties
            elif isinstance(possible_properties, dict):
                properties = [possible_properties]
            else:  # OrderedDict hints that a 'preview' report was generated, anything else is an unhandled case
                _log.debug("Property list was not a list...was a preview report template used on accident?: %s" % str(possible_properties))
                return False, "Property list was not a list...was a preview report template used on accident?"
        except (KeyError, TypeError):
            _log.debug("Processed template successfully, but missing keys -- is the report empty on Portfolio Manager?: %s" % str(xml))
            return False, "Processed template successfully, but missing keys -- is the report empty on Portfolio Manager?"

        return True, properties

    def _parse_properties_v2(self, xml):
        """Parse the XML (in dict format) response from the ESPM API and return a list of
        properties. This version was implemented after 02/13/2023

        Args:
            xml (dict): content to be parsed

        Returns:
            (valid, return_data): success and list of properties, or failure and error message
        """

        def _flatten_property_metrics(pm):
            """convert the property metrics into a flat dictionary and type case the nils"""
            data = {}
            for metric in pm["metric"]:
                if isinstance(metric["value"], dict) and metric["value"]["@xsi:nil"] == "true":
                    data[metric["@name"]] = None
                    continue

                # all other values are treated as strings. Eventually SEED will type cast
                # these values.
                data[metric["@name"]] = metric["value"]
            return data

        return_data = []
        try:
            possible_properties = xml["reportData"]["informationAndMetrics"]["propertyMetrics"]
            if isinstance(possible_properties, list):
                properties = possible_properties
            elif isinstance(possible_properties, dict):
                properties = [possible_properties]
            else:  # OrderedDict hints that a 'preview' report was generated, anything else is an unhandled case
                _log.debug("Property list was not a list...was a preview report template used on accident?: %s" % str(possible_properties))
                return False, "Property list was not a list...was a preview report template used on accident?"

            for p in properties:
                return_data.append(_flatten_property_metrics(p))
        except (KeyError, TypeError):
            _log.debug("Processed template successfully, but missing keys -- is the report empty on Portfolio Manager?: %s" % str(xml))
            return False, "Processed template successfully, but missing keys -- is the report empty on Portfolio Manager?"

        return True, return_data

    def download_url(self, template_id, report_format="XML"):
        """helper method to assemble the download url for a given template id. Default format is XML"""
        return f"{self.DOWNLOAD_REPORT_URL}/{template_id}/{report_format}?testEnv=false&filterResponses=false"

    def download_url_single_report(self, pm_property_id: int) -> str:
        """helper method to assemble the download url for a single property report.

        Args:
            pm_property_id (int): PM Property ID to download

        Returns:
            str: URL
        """
        url = f"{self.DOWNLOAD_SINGLE_PROPERTY_REPORT_URL}/{pm_property_id}/download/{pm_property_id}.xlsx"
        _log.debug(f"ESPM single property download URL is {url}")
        return url

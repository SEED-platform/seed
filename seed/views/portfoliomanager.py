# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

import json
import logging
import time
import urllib

import pint
import requests
import xmltodict
from django.http import JsonResponse
from rest_framework.serializers import Serializer
from rest_framework.decorators import list_route
from rest_framework.viewsets import GenericViewSet

_log = logging.getLogger(__name__)


class PortfolioManagerSerializer(Serializer):
    pass


class PortfolioManagerViewSet(GenericViewSet):

    serializer_class = PortfolioManagerSerializer

    ATTRIBUTES_TO_PROCESS = [
        'national_median_site_energy_use',
        'site_energy_use',
        'source_energy_use',
        'site_eui',
        'source_eui'
    ]

    @staticmethod
    def normalize_attribute(attribute_object):
        u_registry = pint.UnitRegistry()
        if '@uom' in attribute_object and '#text' in attribute_object:
            # this is the correct expected path for unit-based attributes
            string_value = attribute_object['#text']
            try:
                float_value = float(string_value)
            except ValueError:
                return {'status': 'error', 'message': 'Could not cast value to float: \"%s\"' % string_value}
            original_unit_string = attribute_object['@uom']
            if original_unit_string == u'kBtu':
                converted_value = float_value * 3.0
                return {'status': 'success', 'value': converted_value, 'units': str(u_registry.meter)}
            elif original_unit_string == u'kBtu/ft²':
                converted_value = float_value * 3.0
                return {'status': 'success', 'value': converted_value, 'units': str(u_registry.meter)}
            elif original_unit_string == u'Metric Tons CO2e':
                converted_value = float_value * 3.0
                return {'status': 'success', 'value': converted_value, 'units': str(u_registry.meter)}
            elif original_unit_string == u'kgCO2e/ft²':
                converted_value = float_value * 3.0
                return {'status': 'success', 'value': converted_value, 'units': str(u_registry.meter)}
            else:
                return {'status': 'error', 'message': 'Unsupported units string: \"%s\"' % original_unit_string}

    @list_route(methods=['POST'])
    def template_list(self, request):
        if 'username' not in request.data:
            return JsonResponse('Invalid call to PM worker: missing username for PM account')
        if 'password' not in request.data:
            return JsonResponse('Invalid call to PM worker: missing password for PM account')
        username = request.data['username']
        password = request.data['password']
        pm = PortfolioManagerImport(username, password)
        possible_templates = pm.get_list_of_report_templates()
        return JsonResponse({'status': 'success', 'templates': possible_templates})

    @list_route(methods=['POST'])
    def report(self, request):
        if 'username' not in request.data:
            return JsonResponse('Invalid call to PM worker: missing username for PM account')
        if 'password' not in request.data:
            return JsonResponse('Invalid call to PM worker: missing password for PM account')
        if 'template' not in request.data:
            return JsonResponse('Invalid call to PM worker: missing template for PM account')
        username = request.data['username']
        password = request.data['password']
        template = request.data['template']
        pm = PortfolioManagerImport(username, password)
        content = pm.generate_and_download_template_report(template)
        try:
            content_object = xmltodict.parse(content)
        except Exception:  # xmltodict doesn't specify a class of Exceptions, so I'm not sure what all to catch here
            return JsonResponse({'status': 'error', 'message': 'Malformed XML from template download'}, status=500)
        success = True
        if 'report' not in content_object:
            success = False
        if 'informationAndMetrics' not in content_object['report']:
            success = False
        if 'row' not in content_object['report']['informationAndMetrics']:
            success = False
        if not success:
            return JsonResponse({'status': 'error',
                                 'message': 'Template XML response was properly formatted but missing expected keys.'},
                                status=500)
        properties = content_object['report']['informationAndMetrics']['row']
        return JsonResponse({'status': 'success', 'properties': properties})


class PortfolioManagerImport(object):

    def __init__(self, m_username, m_password):

        # store the original, unmodified versions -- DO NOT ENCODE THESE
        self.username = m_username
        self.password = m_password
        self.authenticated_headers = None
        _log.debug("Created PortfolioManagerManager for username: %s" % self.username)

    def login_and_set_cookie_header(self):

        # First we need to log in to Portfolio Manager
        login_url = "https://portfoliomanager.energystar.gov/pm/j_spring_security_check"
        payload = {"j_username": self.username, "j_password": self.password}
        response = requests.post(login_url, data=payload)

        # This returns a 200 even if the credentials are bad, so I'm having to check some text in the response
        if 'The username and/or password you entered is not correct. Please try again.' in response.content:
            raise Exception("Unsuccessful response from login attempt; aborting.  Check credentials.")

        # Upon successful logging in, we should have received a cookie header that we can reuse later
        if 'Cookie' not in response.request.headers:
            raise Exception("Could not find Cookie key in response headers; aborting.")
        cookie_header = response.request.headers['Cookie']
        if '=' not in cookie_header:
            raise Exception("Malformed Cookie key in response headers; aborting.")
        cookie = cookie_header.split('=')[1]
        _log.debug("Logged in and received cookie: " + cookie)

        # Prepare the fully authenticated headers
        self.authenticated_headers = {
            "Cookie": "JSESSIONID=" + cookie + "; org.springframework.web.servlet.i18n.CookieLocaleResolver.LOCALE=en"
        }

    def get_list_of_report_templates(self):

        # login if needed
        if not self.authenticated_headers:
            self.login_and_set_cookie_header()

        # Get the report templates
        url = "https://portfoliomanager.energystar.gov/pm/reports/templateTableRows"
        response = requests.get(url, headers=self.authenticated_headers)
        if not response.status_code == 200:
            raise Exception("Unsuccessful response from report template rows query; aborting.")
        try:
            template_object = json.loads(response.text)
        except ValueError:
            raise Exception("Malformed JSON response from report template rows query; aborting.")
        _log.debug("Received the following JSON return: " + json.dumps(template_object, indent=2))

        # We need to parse the list of report templates
        if 'rows' not in template_object:
            raise Exception("Could not find rows key in template response; aborting.")
        templates = template_object["rows"]
        for t in templates:
            _log.debug("Found template,\n id=" + str(t["id"]) + "\n name=" + str(t["name"]))

        return templates

    @staticmethod
    def get_template_by_name(templates, template_name):

        # Then we need to pick a single report template by name, eventually this is defined by the PM user
        matched_template = next((t for t in templates if t["name"] == template_name), None)
        if not matched_template:
            raise Exception("Could not find a matching template for this name, try a different name")
        _log.debug("Desired report name found, template info: " + json.dumps(matched_template, indent=2))
        return matched_template

    def generate_and_download_template_report(self, matched_template):

        # login if needed
        if not self.authenticated_headers:
            self.login_and_set_cookie_header()

        # We should then trigger generation of the report we selected
        template_report_id = matched_template["id"]
        generation_url = "https://portfoliomanager.energystar.gov/pm/reports/generateData/" + str(template_report_id)
        response = requests.post(generation_url, headers=self.authenticated_headers)
        if not response.status_code == 200:
            raise Exception("Unsuccessful response from POST to trigger report generation; aborting.")
        _log.debug("Triggered report generation,\n status code=" + str(
            response.status_code) + "\n response headers=" + str(
            response.headers))

        # Now we need to wait while the report is being generated
        url = "https://portfoliomanager.energystar.gov/pm/reports/templateTableRows"
        attempt_count = 0
        report_generation_complete = False
        while attempt_count < 10:
            attempt_count += 1
            response = requests.get(url, headers=self.authenticated_headers)
            if not response.status_code == 200:
                raise Exception("Unsuccessful response from GET trying to check status on generated report; aborting.")
            template_objects = json.loads(response.text)["rows"]
            this_matched_template = next((t for t in template_objects if t["id"] == matched_template["id"]), None)
            if not this_matched_template:
                raise Exception("Couldn't find a match for this report template id...odd at this point")
            if this_matched_template["pending"] == 1:
                time.sleep(2)
                continue
            else:
                report_generation_complete = True
                break
        if report_generation_complete:
            _log.debug("Report appears to have been generated successfully (attempt_count=" + str(attempt_count) + ")")
        else:
            raise Exception("Template report not generated successfully; aborting.")

        # Finally we can download the generated report
        template_report_name = urllib.quote(matched_template["name"]) + ".xml"
        download_url = "https://portfoliomanager.energystar.gov/pm/reports/template/download/%s/XML/false/%s" % (
            str(template_report_id), template_report_name
        )
        response = requests.get(download_url, headers=self.authenticated_headers)
        if not response.status_code == 200:
            raise Exception("Unsuccessful response from GET trying to download generated report; aborting.")
        return response.content

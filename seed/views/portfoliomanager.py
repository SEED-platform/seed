# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

import json
import logging
import time
import urllib

import requests
import xmltodict
from django.http import JsonResponse
from rest_framework.decorators import list_route
from rest_framework.viewsets import GenericViewSet
from rest_framework import serializers, status

_log = logging.getLogger(__name__)


class PMExcept(Exception):
    pass


class PortfolioManagerSerializer(serializers.Serializer):
    pass


class PortfolioManagerViewSet(GenericViewSet):
    serializer_class = PortfolioManagerSerializer

    @list_route(methods=['POST'])
    def template_list(self, request):

        if 'username' not in request.data:
            return JsonResponse(
                {'status': 'error', 'message': 'Invalid call to PM worker: missing username for PM account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if 'password' not in request.data:
            return JsonResponse(
                {'status': 'error', 'message': 'Invalid call to PM worker: missing password for PM account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        username = request.data['username']
        password = request.data['password']
        pm = PortfolioManagerImport(username, password)
        try:
            possible_templates, any_errors = pm.get_list_of_report_templates()
        except PMExcept as pme:
            return JsonResponse(
                {'status': 'error', 'message': pme.message},
                status=status.HTTP_400_BAD_REQUEST
            )
        return JsonResponse({'status': 'success', 'templates': possible_templates, 'any_errors': any_errors})

    @list_route(methods=['POST'])
    def report(self, request):

        if 'username' not in request.data:
            return JsonResponse(
                {'status': 'error', 'message': 'Invalid call to PM worker: missing username for PM account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if 'password' not in request.data:
            return JsonResponse(
                {'status': 'error', 'message': 'Invalid call to PM worker: missing password for PM account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if 'template' not in request.data:
            return JsonResponse(
                {'status': 'error', 'message': 'Invalid call to PM worker: missing template for PM account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        username = request.data['username']
        password = request.data['password']
        template = request.data['template']
        pm = PortfolioManagerImport(username, password)
        try:
            content, any_errors = pm.generate_and_download_template_report(template)
        except PMExcept as pme:
            return JsonResponse(
                {'status': 'error', 'message': pme.message},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            content_object = xmltodict.parse(content)
        except Exception:  # catch all because xmltodict doesn't specify a class of Exceptions (just ParsingInterrupted)
            return JsonResponse({'status': 'error', 'message': 'Malformed XML from template download'}, status=500)
        try:
            properties = content_object['report']['informationAndMetrics']['row']
        except KeyError:
            return JsonResponse(
                {'status': 'error', 'message': 'Template XML was properly formatted but missing expected keys.'},
                status=500
            )

        return JsonResponse({'status': 'success', 'properties': properties, 'any_errors': any_errors})


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
        try:
            response = requests.post(login_url, data=payload)
        except requests.exceptions.SSLError:
            raise PMExcept("SSL Error in Portfolio Manager Query; check VPN/Network/Proxy.")

        # This returns a 200 even if the credentials are bad, so I'm having to check some text in the response
        if 'The username and/or password you entered is not correct. Please try again.' in response.content:
            raise PMExcept("Unsuccessful response from login attempt; aborting.  Check credentials.")

        # Upon successful logging in, we should have received a cookie header that we can reuse later
        if 'Cookie' not in response.request.headers:
            raise PMExcept("Could not find Cookie key in response headers; aborting.")
        cookie_header = response.request.headers['Cookie']
        if '=' not in cookie_header:
            raise PMExcept("Malformed Cookie key in response headers; aborting.")
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
        try:
            response = requests.get(url, headers=self.authenticated_headers)
        except requests.exceptions.SSLError:
            raise PMExcept("SSL Error in Portfolio Manager Query; check VPN/Network/Proxy.")
        if not response.status_code == 200:
            raise PMExcept("Unsuccessful response from report template rows query; aborting.")
        try:
            template_object = json.loads(response.text)
        except ValueError:
            raise PMExcept("Malformed JSON response from report template rows query; aborting.")
        _log.debug("Received the following JSON return: " + json.dumps(template_object, indent=2))

        # We need to parse the list of report templates
        if 'rows' not in template_object:
            raise PMExcept("Could not find rows key in template response; aborting.")
        templates = template_object["rows"]
        return_templates = []
        any_errors = False
        for t in templates:
            if "id" not in t and "name" not in t:
                _log.debug("Template retrieved from PortfolioManager but with no id or name keys")
                any_errors = True
            elif "id" not in t:
                _log.debug("Template retrieved but did not include \"id\" key; name = " + str(t["name"]))
                any_errors = True
            elif "name" not in t:
                _log.debug("Template retrieved but did not include \"name\" key; id = " + str(t["id"]))
                any_errors = True
            else:
                _log.debug("Found template,\n id=" + str(t["id"]) + "\n name=" + str(t["name"]))
                return_templates.append(t)
        return return_templates, any_errors

    @staticmethod
    def get_template_by_name(templates, template_name):

        # Then we need to pick a single report template by name, eventually this is defined by the PM user
        matched_template = next((t for t in templates if t["name"] == template_name), None)
        if not matched_template:
            raise PMExcept("Could not find a matching template for this name, try a different name")
        _log.debug("Desired report name found, template info: " + json.dumps(matched_template, indent=2))
        return matched_template

    def generate_and_download_template_report(self, matched_template):

        # login if needed
        if not self.authenticated_headers:
            self.login_and_set_cookie_header()

        # We should then trigger generation of the report we selected
        if "id" not in matched_template:
            raise PMExcept("Matched template does not have id field, this should not be possible")
        template_report_id = matched_template["id"]
        generation_url = "https://portfoliomanager.energystar.gov/pm/reports/generateData/" + str(template_report_id)
        try:
            response = requests.post(generation_url, headers=self.authenticated_headers)
        except requests.exceptions.SSLError:
            raise PMExcept("SSL Error in Portfolio Manager Query; check VPN/Network/Proxy.")
        if not response.status_code == 200:
            raise PMExcept("Unsuccessful response from POST to trigger report generation; aborting.")
        _log.debug("Triggered report generation,\n status code=" + str(
            response.status_code) + "\n response headers=" + str(
            response.headers))

        # Now we need to wait while the report is being generated
        url = "https://portfoliomanager.energystar.gov/pm/reports/templateTableRows"
        attempt_count = 0
        report_generation_complete = False
        any_errors = False
        while attempt_count < 10:
            attempt_count += 1
            try:
                response = requests.get(url, headers=self.authenticated_headers)
            except requests.exceptions.SSLError:
                raise PMExcept("SSL Error in Portfolio Manager Query; check VPN/Network/Proxy.")
            if not response.status_code == 200:
                raise PMExcept("Unsuccessful response from GET trying to check status on generated report; aborting.")
            try:
                template_object_dictionary = json.loads(response.text)
            except ValueError:
                raise PMExcept("Malformed JSON response from report template rows query; aborting.")
            if "rows" not in template_object_dictionary:
                raise PMExcept("Could not find rows key in template response; aborting.")
            template_objects = template_object_dictionary["rows"]
            valid_templates = [t for t in template_objects if "id" in t]
            if len(template_objects) != len(valid_templates):
                any_errors = True
            this_matched_template = next((t for t in valid_templates if t["id"] == matched_template["id"]), None)
            if not this_matched_template:
                raise PMExcept("Couldn't find a match for this report template id...odd at this point")
            if this_matched_template["pending"] == 1:
                time.sleep(2)
                continue
            else:
                report_generation_complete = True
                break
        if report_generation_complete:
            _log.debug("Report appears to have been generated successfully (attempt_count=" + str(attempt_count) + ")")
        else:
            raise PMExcept("Template report not generated successfully; aborting.")

        # Finally we can download the generated report
        template_report_name = urllib.quote(matched_template["name"]) + ".xml"
        download_url = "https://portfoliomanager.energystar.gov/pm/reports/template/download/%s/XML/false/%s" % (
            str(template_report_id), template_report_name
        )
        try:
            response = requests.get(download_url, headers=self.authenticated_headers)
        except requests.exceptions.SSLError:
            raise PMExcept("SSL Error in Portfolio Manager Query; check VPN/Network/Proxy.")
        if not response.status_code == 200:
            raise PMExcept("Unsuccessful response from GET trying to download generated report; aborting.")
        return response.content, any_errors

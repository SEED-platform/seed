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
import time
import urllib

import pint
import requests
import xmltodict
from django.http import JsonResponse
from rest_framework.decorators import list_route
from rest_framework.viewsets import GenericViewSet

from seed.models import PropertyState
from seed.utils.address import normalize_address_str


class PortfolioManagerViewSet(GenericViewSet):

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
        if 'email' not in request.data:
            return JsonResponse('Invalid call to PM worker: missing email for PM account')
        if 'username' not in request.data:
            return JsonResponse('Invalid call to PM worker: missing username for PM account')
        if 'password' not in request.data:
            return JsonResponse('Invalid call to PM worker: missing password for PM account')
        email = request.data['email']
        username = request.data['username']
        password = request.data['password']
        pm = PortfolioManagerImport(email, username, password)
        possible_templates = pm.get_list_of_report_templates()
        return JsonResponse({'status': 'success', 'templates': possible_templates})  # TODO: Could just return ['name']s...
        # print("  Index  |  Template Report Name  ")
        # print("---------|------------------------")
        # for i, t in enumerate(possible_templates):
        #     print("  %s  |  %s  " % (str(i).ljust(5), t['name']))
        # selection = raw_input("\nEnter an Index to download the report: ")
        # try:
        #     s_id = int(selection)
        # except ValueError:
        #     raise Exception("Invalid Selection; aborting.")
        # if 0 <= s_id < len(possible_templates):
        #     selected_template = possible_templates[s_id]
        # else:
        #     raise Exception("Invalid Selection; aborting.")

    @list_route(methods=['POST'])
    def report(self, request):
        if 'email' not in request.data:
            return JsonResponse('Invalid call to PM worker: missing email for PM account')
        if 'username' not in request.data:
            return JsonResponse('Invalid call to PM worker: missing username for PM account')
        if 'password' not in request.data:
            return JsonResponse('Invalid call to PM worker: missing password for PM account')
        if 'template' not in request.data:
            return JsonResponse('Invalid call to PM worker: missing template for PM account')
        email = request.data['email']
        username = request.data['username']
        password = request.data['password']
        template = request.data['template']
        pm = PortfolioManagerImport(email, username, password)
        content = pm.generate_and_download_template_report(template)
        try:
            content_object = xmltodict.parse(content)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Malformed XML response from template download'}, status=500)
        success = True
        if 'report' not in content_object:
            success = False
        if 'informationAndMetrics' not in content_object['report']:
            success = False
        if 'row' not in content_object['report']['informationAndMetrics']:
            success = False
        if not success:
            return JsonResponse({'status': 'error',
                                 'message': 'Template XML response was properly formatted but was missing expected keys.'},
                                status=500)
        properties = content_object['report']['informationAndMetrics']['row']

        # now we need to actually process each property
        # if we find a match we should update it, if we don't we should create it
        # then we should assign/update property values, possibly from this list?
        #  energy_score
        #  site_eui
        #  generation_date
        #  release_date
        #  source_eui_weather_normalized
        #  site_eui_weather_normalized
        #  source_eui
        #  energy_alerts
        #  space_alerts
        #  building_certification
        for prop in properties:
            seed_property_match = None

            # first try to match by pm property id if the PM report includes it
            if 'property_id' in prop:
                this_property_pm_id = prop['property_id']
                try:
                    seed_property_match = PropertyState.objects.get(pm_property_id=this_property_pm_id)
                    prop['MATCHED'] = 'Matched via pm_property_id'
                except PropertyState.DoesNotExist:
                    seed_property_match = None

            # second try to match by address/city/state if the PM report includes it
            if not seed_property_match:
                if all(attr in prop for attr in ['address_1', 'city', 'state_province']):
                    this_property_address_one = prop['address_1']
                    this_property_city = prop['city']
                    this_property_state = prop['state_province']
                    try:
                        seed_property_match = PropertyState.objects.get(
                            address_line_1__iexact=this_property_address_one,  # This is normalized so I don't need iexact
                            city__iexact=this_property_city,  # But I think I still need iexact on city/state right?
                            state__iexact=this_property_state
                        )
                        prop['MATCHED'] = 'Matched via address/city/state'
                    except PropertyState.DoesNotExist:
                        seed_property_match = None

            # if we didn't match then we need to create a new one
            if not seed_property_match:
                prop['MATCHED'] = 'NO! need to create new property'

            # either way at this point we should have a property, existing or new
            # so now we should process the attributes
            processed_attributes = {}
            for attribute_to_check in PortfolioManagerViewSet.ATTRIBUTES_TO_PROCESS:
                if attribute_to_check in prop:
                    found_attribute = prop[attribute_to_check]
                    if isinstance(found_attribute, dict):
                        if found_attribute['#text']:
                            if found_attribute['#text'] == 'Not Available':
                                processed_attributes[attribute_to_check] = 'Requested variable blank/unavailable on PM'
                            else:
                                updated_attribute = PortfolioManagerViewSet.normalize_attribute(found_attribute)
                                processed_attributes[attribute_to_check] = updated_attribute
                        else:
                            processed_attributes[attribute_to_check] = 'Malformed attribute did not have #text field'
                    else:
                        pass  # nothing for now

            prop['PROCESSED'] = processed_attributes

        return JsonResponse({'status': 'success', 'properties': properties})


def log(s):
    print s


def error(s):
    raise Exception(s)


# give username/password for PM
class PortfolioManagerImport(object):
    def __init__(self, m_email, m_username, m_password):
        # store the original, unmodified versions -- DO NOT ENCODE THESE
        self.email = m_email
        self.username = m_username
        self.password = m_password
        log(
            "Created PortfolioManagerManager:\n email: %s \n username: %s \n password: %s" %
            (self.email, self.username, self.password)
        )
        self.authenticated_headers = None

    def login_and_set_cookie_header(self):
        # First we need to log in to Portfolio Manager
        login_url = "https://portfoliomanager.energystar.gov/pm/j_spring_security_check"
        payload = {"j_username": self.username, "j_password": self.password}
        response = requests.post(login_url, data=payload)
        if not response.status_code == 200:
            error("Unsuccessful response from login attempt; aborting.  Check credentials.")
        # TODO: This returns 200 even if the credentials are bad...

        # Upon successful logging in, we should have received a cookie header that we can reuse later
        if 'Cookie' not in response.request.headers:
            error("Could not find Cookie key in response headers; aborting.")
        cookie_header = response.request.headers['Cookie']
        if '=' not in cookie_header:
            error("Malformed Cookie key in response headers; aborting.")
        cookie = cookie_header.split('=')[1]
        log("Logged in and received cookie: " + cookie)

        # Prepare the fully authenticated headers
        self.authenticated_headers = {
            "Cookie": "JSESSIONID=" + cookie + "; org.springframework.web.servlet.i18n.CookieLocaleResolver.LOCALE=en"
        }

    def get_list_of_report_templates(self):
        if not self.authenticated_headers:
            self.login_and_set_cookie_header()

        # Get the report templates
        url = "https://portfoliomanager.energystar.gov/pm/reports/templateTableRows"
        response = requests.get(url, headers=self.authenticated_headers)
        if not response.status_code == 200:
            error("Unsuccessful response from report template rows query; aborting.")
        try:
            template_object = json.loads(response.text)
        except ValueError:
            template_object = None  # to avoid static analysis error for uninitialized variable
            error("Malformed JSON response from report template rows query; aborting.")
        log("Received the following JSON return: " + json.dumps(template_object, indent=2))

        # We need to parse the list of report templates
        if 'rows' not in template_object:
            error("Could not find rows key in template response; aborting.")
        templates = template_object["rows"]
        for t in templates:
            log("Found template,\n id=" + str(t["id"]) + "\n name=" + str(t["name"]))

        return templates

    @staticmethod
    def get_template_by_name(templates, template_name):
        # Then we need to pick a single report template by name, eventually this is defined by the PM user
        matched_template = next((t for t in templates if t["name"] == template_name), None)
        if not matched_template:
            error("Could not find a matching template for this name, try a different name")
        log("Desired report name found, template info: " + json.dumps(matched_template, indent=2))
        return matched_template

    def generate_and_download_template_report(self, matched_template):
        if not self.authenticated_headers:
            self.login_and_set_cookie_header()

        # We should then trigger generation of the report we selected
        template_report_id = matched_template["id"]
        generation_url = "https://portfoliomanager.energystar.gov/pm/reports/generateData/" + str(template_report_id)
        response = requests.post(generation_url, headers=self.authenticated_headers)
        if not response.status_code == 200:
            error("Unsuccessful response from POST to trigger report generation; aborting.")
        log("Triggered report generation,\n status code=" + str(
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
                error("Unsuccessful response from GET trying to check status on generated report; aborting.")
            template_objects = json.loads(response.text)["rows"]
            this_matched_template = next((t for t in template_objects if t["id"] == matched_template["id"]), None)
            if not this_matched_template:
                error("Couldn't find a match for this report template id...odd at this point")
            if this_matched_template["pending"] == 1:
                time.sleep(2)
                continue
            else:
                report_generation_complete = True
                break
        if report_generation_complete:
            log("Report appears to have been generated successfully (attempt_count=" + str(attempt_count) + ")")
        else:
            error("Template report not generated successfully; aborting.")

        # Finally we can download the generated report
        template_report_name = urllib.quote(matched_template["name"]) + ".xml"
        download_url = "https://portfoliomanager.energystar.gov/pm/reports/template/download/%s/XML/false/%s" % (
            str(template_report_id), template_report_name
        )
        response = requests.get(download_url, headers=self.authenticated_headers)
        if not response.status_code == 200:
            error("Unsuccessful response from GET trying to download generated report; aborting.")
        return response.content

    def automated_test(self):
        if not self.authenticated_headers:
            self.login_and_set_cookie_header()
        templates = self.get_list_of_report_templates()
        matched_template = PortfolioManagerImport.get_template_by_name(templates, "SEED City Test Report")
        template_data = self.generate_and_download_template_report(matched_template)
        return template_data

# check whether the report matches the last report
# upload the report into seed if different

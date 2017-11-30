#!/usr/bin/env python

import json
import time
import urllib

import requests

DEBUG = False


def log(s):
    if DEBUG:
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

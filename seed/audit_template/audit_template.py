# !/usr/bin/env python
# encoding: utf-8

from django.conf import settings
import logging
import requests

_log = logging.getLogger(__name__)


class AuditTemplate(object):

    HOST = settings.AUDIT_TEMPLATE_HOST
    API_URL = f'{HOST}/api/v2'

    def __init__(self, token):
        self._token = token

    def get_building(self, at_building_id):
        url = f'{self.API_URL}/building_sync/download/rp/buildings/{at_building_id}.xml?token={self._token}'
        headers = {'accept': 'application/xml'}

        try:
            response = requests.request("GET", url, headers=headers)
            if response.status_code != 200:
                return None, [f'Expected 200 response from Audit Template but got {response.status_code}: {response.content}']
        except Exception as e:
            return None, [f'Unexpected error from Audit Template: {e}']

        return response

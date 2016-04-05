import requests
from django.conf import settings

from requests.exceptions import ConnectionError

def detect():
    try:
        requests.get(settings.TSDB['version_url']) #get KairosDB version
    except ConnectionError:
        return False

    return True

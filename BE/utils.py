"""
:copyright: (c) 2014 Building Energy Inc
"""
import logging
import re
from django.conf import settings

logger = logging.getLogger(__name__)


SITE_PREFIX_MAPPING = {}
for k, v in settings.DOMAIN_URLCONFS.items():
    SITE_PREFIX_MAPPING[k] = v.split(".")[1]


def de_camel_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1)

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import re
from importlib import import_module
from functools import wraps

from django.conf import settings


def get_api_endpoints():
    """
    Examines all views and returns those with is_api_endpoint set
    to true (done by the @api_endpoint decorator).
    """
    urlconf = import_module(settings.ROOT_URLCONF)
    urllist = urlconf.urlpatterns
    api_endpoints = {}
    for (url, callback) in get_all_urls(urllist):
        if getattr(callback, 'is_api_endpoint', False):
            clean_url = clean_api_regex(url)
            api_endpoints[clean_url] = callback
    return api_endpoints


def format_api_docstring(docstring):
    """
    Cleans up a python method docstring for human consumption.
    """
    if not isinstance(docstring, basestring):
        return "INVALID DOCSTRING"
    whitespace_regex = '\s+'
    ret = re.sub(whitespace_regex, ' ', docstring)
    ret = ret.strip()
    return ret


def clean_api_regex(url):
    """
    Given a django-style url regex pattern, strip it down to a human-readable
    url.

    TODO: If pks ever appear in the url, this will need to account for that.
    """
    url = url.replace('^', '')
    url = url.replace('$', '')
    if not url.startswith('/'):
        url = '/' + url
    return url


def get_all_urls(urllist, prefix=''):
    """
    Recursive generator that traverses entire tree of URLs, starting with
    urllist, yielding a tuple of (url_pattern, view_function) for each
    one.
    """
    for entry in urllist:
        if hasattr(entry, 'url_patterns'):
            for url in get_all_urls(entry.url_patterns,
                                    prefix + entry.regex.pattern):
                yield url
        else:
            yield (prefix + entry.regex.pattern, entry.callback)


# API endpoint decorator
# simple list of all 'registered' endpoints
endpoints = []


def api_endpoint(fn):
    """
    Decorator function to mark a view as allowed to authenticate via API key.

    Decorator must be used before login_required or has_perm to set
    request.user for those decorators.
    """
    # mark this function as an api endpoint for get_api_endpoints to find
    fn.is_api_endpoint = True
    global endpoints
    endpoints.append(fn)

    @wraps(fn)
    def _wrapped(request, *args, **kwargs):
        user = get_api_request_user(request)
        if user:
            request.is_api_request = True
            request.user = user

        return fn(request, *args, **kwargs)

    return _wrapped


def api_endpoint_class(fn):
    """
    Decorator function to mark a view as allowed to authenticate via API key.

    Decorator must be used before login_required or has_perm to set
    request.user for those decorators.
    """
    # mark this function as an api endpoint for get_api_endpoints to find
    fn.is_api_endpoint = True
    global endpoints
    endpoints.append(fn)

    @wraps(fn)
    def _wrapped(self, request, *args, **kwargs):
        user = get_api_request_user(request)
        if user:
            request.is_api_request = True
            request.user = user

        return fn(self, request, *args, **kwargs)

    return _wrapped


def drf_api_endpoint(fn):
    """
    Decorator to register a Django Rest Framework view with the list of API
    endpoints.  Marks it with `is_api_endpoint = True` as well as appending it
    to the global `endpoints` list.
    """
    fn.is_api_endpoint = True
    global endpoints
    endpoints.append(fn)

    return fn


def get_api_request_user(request):
    """
    Determines if this is an API request and returns the corresponding user
    if so.
    """
    if request.is_ajax():
        return False

    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        return False
    try:
        # late import
        from seed.landing.models import SEEDUser as User
        username, api_key = auth_header.split(':')
        return User.objects.get(api_key=api_key, username=username)
    except (ValueError, User.DoesNotExist):
        return False


class APIBypassCSRFMiddleware(object):
    """
    This middleware turns off CSRF protection for API clients.

    It must come before CsrfViewMiddleware in settings.MIDDLEWARE_CLASSES.
    """

    def process_view(self, request, *args, **kwargs):
        """
        If this request is an API request, bypass CSRF protection.
        """
        if get_api_request_user(request):
            request.csrf_processing_done = True
        return None

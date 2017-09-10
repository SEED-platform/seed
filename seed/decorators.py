# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
from functools import wraps

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest

from seed.lib.superperms.orgs.models import OrganizationUser
from seed.utils.cache import make_key, lock_cache, unlock_cache, get_lock

from quantityfield import ureg

SEED_CACHE_PREFIX = 'SEED:{0}'
LOCK_CACHE_PREFIX = SEED_CACHE_PREFIX + ':LOCK'
PROGRESS_CACHE_PREFIX = SEED_CACHE_PREFIX + ':PROG'


class PintJSONEncoder(DjangoJSONEncoder):
    """
    Converts pint Quantity objects for Angular's benefit.
    """
    def default(self, obj):
        if isinstance(obj, ureg.Quantity):
            # TODO handle unit conversion on the server per-org
            return "{:.2f}".format(obj.magnitude)
        return super(PintJSONEncoder, self).default(obj)


FORMAT_TYPES = {
    'application/json': lambda response: json.dumps(response, cls=PintJSONEncoder),
    'text/json': lambda response: json.dumps(response, cls=PintJSONEncoder),
}


def _get_cache_key(prefix, import_file_pk):
    """Makes a key like 'SEED:save_raw_data:LOCK:45'."""
    return make_key(
        '{0}:{1}'.format(prefix, import_file_pk)
    )


def _get_lock_key(func_name, import_file_pk):
    return _get_cache_key(
        LOCK_CACHE_PREFIX.format(func_name), import_file_pk
    )


def get_prog_key(func_name, import_file_pk):
    """Return the progress key for the cache"""
    return _get_cache_key(
        PROGRESS_CACHE_PREFIX.format(func_name), import_file_pk
    )


def lock_and_track(fn, *args, **kwargs):
    """Decorator to lock tasks to single executor and provide progress url."""
    func_name = fn.__name__

    @wraps(fn)
    def _wrapped(import_file_pk, *args, **kwargs):
        """Lock and return progress url for updates."""
        lock_key = _get_lock_key(func_name, import_file_pk)
        prog_key = get_prog_key(func_name, import_file_pk)
        is_locked = get_lock(lock_key)
        # If we're already processing a given task, don't proceed.
        if is_locked:
            return {'error': 'locked'}

        # Otherwise, set the lock for 1 minute.
        lock_cache(lock_key)
        try:
            response = fn(import_file_pk, *args, **kwargs)
        finally:
            # Unset our lock
            unlock_cache(lock_key)

        # If our response is a dict, add our progress URL to it.
        if isinstance(response, dict):
            response['progress_key'] = prog_key

        return response

    return _wrapped


def ajax_request(func):
    """
    * Copied from django-annoying, with a small modification. Now we also check for 'status' or 'success' keys and \
    return correct status codes

    If view returned serializable dict, returns response in a format requested
    by HTTP_ACCEPT header. Defaults to JSON if none requested or match.

    Currently supports JSON or YAML (if installed), but can easily be extended.

    Example::

        @ajax_request
        def my_view(request):
            news = News.objects.all()
            news_titles = [entry.title for entry in news]
            return { 'news_titles': news_titles }
    """

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        for accepted_type in request.META.get('HTTP_ACCEPT', '').split(','):
            if accepted_type in FORMAT_TYPES.keys():
                format_type = accepted_type
                break
        else:
            format_type = 'application/json'

        response = func(request, *args, **kwargs)

        # determine the status code if the object is a dictionary
        status_code = 200
        if isinstance(response, dict):
            if response.get('status') == 'error' or response.get(
                    'success') is False:
                status_code = 400

        # convert the response into an HttpResponse if it is not already.
        if not isinstance(response, HttpResponse):
            data = FORMAT_TYPES[format_type](response)
            response = HttpResponse(data, content_type=format_type,
                                    status=status_code)
            response['content-length'] = len(data)
        return response

    return wrapper


def ajax_request_class(func):
    """
    * Copied from django-annoying, with a small modification. Now we also check for 'status' or
    'success' keys and return correct status codes

    If view returned serializable dict, returns response in a format requested
    by HTTP_ACCEPT header. Defaults to JSON if none requested or match.

    Currently supports JSON or YAML (if installed), but can easily be extended.

    Example::

        @ajax_request
        def my_view(self, request):
            news = News.objects.all()
            news_titles = [entry.title for entry in news]
            return { 'news_titles': news_titles }
    """

    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        for accepted_type in request.META.get('HTTP_ACCEPT', '').split(','):
            if accepted_type in FORMAT_TYPES.keys():
                format_type = accepted_type
                break
        else:
            format_type = 'application/json'

        response = func(self, request, *args, **kwargs)

        # determine the status code if the object is a dictionary
        status_code = 200
        if isinstance(response, dict):
            if response.get('status') == 'error' or response.get(
                    'success') is False:
                status_code = 400

        # convert the response into an HttpResponse if it is not already.
        if not isinstance(response, HttpResponse):
            data = FORMAT_TYPES[format_type](response)
            response = HttpResponse(data, content_type=format_type,
                                    status=status_code)
            response['content-length'] = len(data)
        return response

    return wrapper


def require_organization_id(func):
    """
    Validate that organization_id is in the GET params and it's an int.
    """

    @wraps(func)
    def _wrapped(request, *args, **kwargs):
        error = False
        try:
            int(request.GET['organization_id'])
        except (ValueError, KeyError):
            error = True
            pass

        if error:
            format_type = 'application/json'
            message = {
                'status': 'error',
                'message': 'Invalid organization_id: either blank or not an integer'
            }

            # NL: I think the error code should be 401: unauthorized, not 400: bad request.
            # Leaving as 400 for now in case this breaks something else.
            return HttpResponse(json.dumps(message), content_type=format_type,
                                status=400)
        else:
            return func(request, *args, **kwargs)

    return _wrapped


def require_organization_id_class(fn):
    """
    Validate that organization_id is in the GET params and it's an int.
    """

    @wraps(fn)
    def _wrapped(self, request, *args, **kwargs):
        org_id = request.query_params.get('organization_id', None)
        if org_id is None:
            return HttpResponseBadRequest(
                'Valid organization_id is required in the query parameters.')
        try:
            int(org_id)
        except (TypeError, ValueError):
            return HttpResponseBadRequest(
                'Invalid organization_id in the query parameters, must be integer')
        return fn(self, request, *args, **kwargs)

    return _wrapped


def require_organization_membership(fn):
    """
    Validate that the organization_id passed in GET is valid for request user.
    """

    @wraps(fn)
    def _wrapped(request, *args, **kwargs):
        if not OrganizationUser.objects.filter(
                organization_id=request.GET['organization_id'],
                user=request.user).exists():
            return HttpResponseForbidden()

        return fn(request, *args, **kwargs)

    return _wrapped


def DecoratorMixin(decorator):
    """
    Converts a decorator written for a function view into a mixin for a class-based view.

    Example::

        LoginRequiredMixin = DecoratorMixin(login_required)
        class MyView(LoginRequiredMixin):
            pass

        class SomeView(DecoratorMixin(some_decorator), DecoratorMixin(something_else)):
            pass
    """

    class Mixin(object):
        __doc__ = decorator.__doc__

        @classmethod
        def as_view(cls, *args, **kwargs):
            view = super(Mixin, cls).as_view(*args, **kwargs)
            return decorator(view)

    Mixin.__name__ = 'DecoratorMixin{0}'.format(decorator.__name__)
    return Mixin

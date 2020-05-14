# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""
import re
from collections import namedtuple
from functools import wraps
from importlib import import_module

from django.conf import settings
from django.core.exceptions import (
    ObjectDoesNotExist,
    PermissionDenied,
    ValidationError
)
from django.http import JsonResponse
from past.builtins import basestring
from rest_framework import status, exceptions

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.permissions import get_org_id, get_user_org
from seed.models import (
    Column,
    ColumnListSetting,
    ColumnListSettingColumn,
    VIEW_LIST,
    VIEW_LIST_PROPERTY)

OrgValidator = namedtuple('OrgValidator', ['key', 'field'])


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
    whitespace_regex = r'\s+'
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
                                    prefix + entry.pattern.regex.pattern):
                try:
                    yield url
                except StopIteration:
                    return
        else:
            try:
                yield (prefix + entry.pattern.regex.pattern, entry.callback)
            except StopIteration:
                return


# pylint: disable=global-variable-not-assigned
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
    Determines if this is an API request and returns the corresponding user if so.
    """
    if request.is_ajax():
        return False

    return User.process_header_request(request)


# pylint: disable=too-few-public-methods
class APIBypassCSRFMiddleware(object):
    """
    This middleware turns off CSRF protection for API clients.

    It must come before CsrfViewMiddleware in settings.MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            if get_api_request_user(request):
                request.csrf_processing_done = True
        except exceptions.AuthenticationFailed as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e),
            }, status=status.HTTP_401_UNAUTHORIZED)
        return response


def rgetattr(obj, lst):
    """This enables recursive getattr look ups.
    given obj, ['a', 'b', 'c'] as params it will look up:
    obj.a, a.b, b.c returning b.c unless one of the previous
    values was None, in which case it returns None immediately.

    :param obj: initial object to examine
    :type obj: object
    :param lst: list of successive attributes to look up
    :type lst: list
    """
    field = lst.pop(0)
    val = getattr(obj, field, None)
    if len(lst) == 0 or val is None:
        return val
    else:
        return rgetattr(val, lst)


def get_org_id_from_validator(instance, field):
    """
    For querysets Django enables you to do things like:

    .. example:

        obj = MyModel.get(org__id=1)

    note double underscore. However you can't do:

    .. example:

        obj.org__id only obj.org.id

    This presents an issue as getattr only works 1 level deep:

        getattr(obj, 'org.id') does not work either.

    This can be worked around using rgetattr (above).
    This functions mimics getattr(obj, 'org__id') by
    splitting field on __ and calling rgetattr on the result.
    """
    fields = field.split('__')
    return rgetattr(instance, fields)


class ProfileIdMixin(object):
    """
    Provides methods to get the columns to show based on a profile ID
    """

    def get_show_columns(self, org_id, profile_id):
        """Get list of columns from the profile_id. The result will be in the form of

        show_columns = {
            'fields': ['field_1', 'field_2', ...]
            'extra_data': ['extra_data_field_1', 'extra_data_field_2', ...]
        }

        :param org_id: str, id of organization
        :param profile_id: str, id of profile to retrieve
        :return: dist of lists
        """
        show_columns = {
            # TODO: decide if we want to make these visible in the result
            'fields': ['extra_data', 'id'],  # , 'bounding_box', 'long_lat', 'centroid',
            'extra_data': []
        }
        profile_exists = ColumnListSetting.objects.filter(
            organization_id=org_id,
            id=profile_id,
            settings_location=VIEW_LIST,
            inventory_type=VIEW_LIST_PROPERTY
        ).exists()
        if profile_id is None or profile_id == -1 or not profile_exists:
            show_columns['fields'] += list(Column.objects.filter(
                organization_id=org_id,
                table_name='PropertyState',
                is_extra_data=False).values_list('column_name', flat=True))
            show_columns['extra_data'] += list(Column.objects.filter(
                organization_id=org_id,
                table_name='PropertyState',
                is_extra_data=True).values_list('column_name', flat=True))
        else:
            profile = ColumnListSetting.objects.get(
                organization_id=org_id,
                id=profile_id,
                settings_location=VIEW_LIST,
                inventory_type=VIEW_LIST_PROPERTY
            )
            for col in list(ColumnListSettingColumn.objects.filter(column_list_setting_id=profile.id).values(
                    'column__column_name', 'column__is_extra_data')):
                if col['column__is_extra_data']:
                    show_columns['extra_data'].append(col['column__column_name'])
                else:
                    show_columns['fields'].append(col['column__column_name'])

        return show_columns


class OrgMixin(object):
    """
    Provides get_organization and get_parent_org method
    """

    def get_organization(self, request, return_obj=False):
        """Get org from query param or request.user.
        :param request: request object.
        :param return_obj: bool. Set to True if obj vs pk is desired.
        :return: int representing a valid organization pk or
            organization object.
        """
        # print("my return obj is set to %s" % return_obj)
        if not request.user:
            return None

        if not getattr(self, '_organization', None):
            org_id = get_org_id(request)
            org = None
            if not org_id:
                org = get_user_org(request.user)
                org_id = int(getattr(org, 'pk'))
            if return_obj:
                if not org:
                    try:
                        org = request.user.orgs.get(pk=org_id)
                        self._organization = org
                    except ObjectDoesNotExist:
                        raise PermissionDenied('Incorrect org id.')
                else:
                    self._organization = org
            else:
                self._organization = org_id
        return self._organization

    def get_parent_org(self, request):
        """Gets parent organization of org from query param or request.
        :param request: Request object.
        :return: organization object.
        """
        org = self.get_organization(request, return_obj=True)
        return getattr(org.get_parent(), 'pk')


class OrgCreateMixin(OrgMixin):
    """
    Mixin to add organization when creating model instance
    """

    def perform_create(self, serializer):
        """Override to add org"""
        org_id = self.get_organization(self.request)
        serializer.save(organization_id=org_id)


class OrgUpdateMixin(OrgMixin):
    """
    Mixin to add organization when updating model instance
    """

    def perform_update(self, serializer):
        """Override to add org"""
        org_id = self.get_organization(self.request)
        serializer.save(organization_id=org_id)


class OrgCreateUpdateMixin(OrgCreateMixin, OrgUpdateMixin):
    """
    Mixin to add organization when creating/updating model instance
    """
    pass


class OrgValidateMixin(object):
    """
    Mixin to provide a validate() method organization to ensure users belongs
    to the same org as the instance referenced by a foreign key..

    You must set org_validators on the Serializer that uses this Mixin.
    This is a list of OrgValidator named tuples (where key is the key
    on request data representing the foreign key,  and field the foreign key
    that represents the organization on the corresponding model.

    my_validator = OrgValidator(key='foreign_key, field='organization_id')

    ..example:

        class MySerializer(OrgValidateMixin, serializers.ModelSerializer):
            foreign_key= serializers.PrimaryKeyRelatedField(
                query_set=MyModel.objects.all()
            )
            org_validators = [my_validator]

    This ensures request.user belongs to the org MyModel.organization

    You can traverse foreign key relationships by using a double underscore
    in validator.field

    In the example above setting validator field to be 'property__org_id'
    is equivalent to MyModel.property.org_id

    If you use this Mixin and write a validate method, you must call super
    to ensure validation takes place.
    """

    def validate_org(self, instance, user, validator):
        """
        Raise error if orgs do not match.
        :param instance: value in request.data.get(key) to check against
        :type instance: model instance
        :param: org_id of user, from get_org_id(request)
        :type org_id:  int
        :param validator: validator to user
        :type: OrgValidator named tuple
        """
        pk = get_org_id_from_validator(instance, validator.field)
        try:
            user.orgs.get(pk=pk)
        except ObjectDoesNotExist:
            msg = 'User is not a member of {} organization.'.format(
                validator.key
            )
            raise PermissionDenied(msg)

    def validate(self, data):
        """
        Object level validation.
        Checks for self.org_validators on Serializers and
        ensures users belongs to org corresponding to the foreign key
        being set.
        """
        org_validators = getattr(self, 'org_validators', None)
        if not org_validators:
            raise ValidationError(
                'org_validators attribute not set on serializer'
            )
        else:
            for validator in org_validators:
                instance = data.get(validator.key)
                if instance:
                    user = self.context['request'].user
                    self.validate_org(instance, user, validator)
        return data


class OrgQuerySetMixin(OrgMixin):
    """
    Mixin proving a get_queryset method that filters on organization.

    In order to use this mixin you must specify the model attributes on the
    View[Set] class. By default it assumes there is an organization field
    on the model. You can override this by setting the orgfilter attribute
    to the appropriate fieldname. This also allows nested fields e.g.
    foreign_key.organization
    By default this retrieves organization from query string param OR the
    default_organization or first returned organization of the logged in user.
    You can force it to return the appropriate "parent" organization by setting
    the force_parent attribute to True.
    """

    def get_queryset(self):
        """"get_queryset filtered on organization"""
        # pylint:disable=invalid-name
        # raises Attribute Error if not set
        Model = self.model
        qsfilter = getattr(self, 'orgfilter', 'organization_id')
        qs = getattr(self, 'queryset', None)
        force_parent = getattr(self, 'force_parent', False)
        if force_parent:
            query_dict = {qsfilter: self.get_parent_org(self.request)}
        else:
            query_dict = {qsfilter: self.get_organization(self.request)}

        if qs:
            query = qs.filter(**query_dict)
        else:
            query = Model.objects.filter(**query_dict)
        return query

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Fable Turas <fable@raintechpdx.com>
"""
from rest_framework.compat import unicode_to_repr

from seed.utils.api import OrgMixin


class CurrentOrganizationIdDefault(OrgMixin):
    """Gets organization to set relevant field default input."""

    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        self.organization_id = self.get_organization_id(request)

    def __call__(self):
        return self.organization_id

    def __repr__(self):
        return unicode_to_repr('%s()' % self.__class__.__name__)


class CurrentParentOrgIdDefault(CurrentOrganizationIdDefault):
    """Gets parent level organization to set relevant field default input."""

    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        self.organization_id = self.get_parent_org_id(request)

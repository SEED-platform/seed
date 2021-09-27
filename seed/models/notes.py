# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import gettext_lazy as _

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    PropertyView,
    TaxLotView,
)
from seed.models.projects import Project
from seed.utils.generic import obj_to_dict


class Note(models.Model):
    # Audit Log types
    NOTE = 0
    LOG = 1

    NOTE_TYPES = (
        (NOTE, 'Note'),
        (LOG, 'Log'),
    )

    name = models.CharField(_('name'), max_length=Project.PROJECT_NAME_MAX_LENGTH)
    note_type = models.IntegerField(choices=NOTE_TYPES, default=NOTE, null=True)

    text = models.TextField()

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, related_name='notes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='notes')  # who added the note
    property_view = models.ForeignKey(PropertyView, on_delete=models.CASCADE, null=True, related_name='notes')
    taxlot_view = models.ForeignKey(TaxLotView, on_delete=models.CASCADE, null=True, related_name='notes')

    # in the near future track the changes to the Property View records by storing the changes in JSON. Proposed format:
    # {
    #    "property_state": [ {
    #       "field": "address_line_1",
    #       "previous_value": "123 Main Street",
    #       "new_value": "742 Evergreen Terrace"
    #       },
    #       {}],
    #    "property: [ { ... } ],
    #    "tax_lot_state": [ { ... } ],
    # }
    #
    log_data = JSONField(default=dict, null=True)

    # Track when the entry was created and when it was updated
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']
        index_together = [['organization', 'note_type']]

    @classmethod
    def create_from_edit(self, user_id, view, new_values, previous_values):
        """
        Create a Log Note given before and after edit values for a -View's
        -State at the time.

        new_values and previous_values expected format:
            {
                "address_line_1": "742 Evergreen Terrace",
                "extra_data": {"Some Extra Data": "111"}
            }

        Note, state_id and user_id are captured for historical purposes, even
        though it's possible that the state_id might change for a -View or a
        user might be disassociated with an organization.
        """
        log_data = []
        # Build out 2 dimensional log data
        for column_name, value in new_values.items():
            if column_name == 'extra_data':
                for ed_column_name, ed_value in value.items():
                    log_data.append({
                        "field": ed_column_name,
                        "previous_value": previous_values.get('extra_data', {}).get(ed_column_name, None),
                        "new_value": ed_value,
                        "state_id": view.state_id
                    })
            else:
                log_data.append({
                    "field": column_name,
                    "previous_value": previous_values.get(column_name, None),
                    "new_value": value,
                    "state_id": view.state_id
                })

        # Create note attributes to be then updated with appropriate -View "type".
        note_attrs = {
            "name": "Automatically Created",
            "note_type": self.LOG,
            "organization_id": view.cycle.organization_id,
            "user_id": user_id,
            "log_data": log_data
        }

        if view.__class__ == PropertyView:
            note_attrs["property_view_id"] = view.id
        elif view.__class__ == TaxLotView:
            note_attrs["taxlot_view_id"] = view.id

        return self.objects.create(**note_attrs)

    def to_dict(self):
        return obj_to_dict(self)

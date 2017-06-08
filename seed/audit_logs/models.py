# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models.query import QuerySet
from django_extensions.db.models import TimeStampedModel

from seed.lib.superperms.orgs.models import Organization

USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', User)

# Audit Log types
LOG = 0
NOTE = 1

AUDIT_CHOICES = (
    (LOG, 'Log'),
    (NOTE, 'Note'),
)

ACTION_OPTIONS = {
    '/app/update_building/': 'Edited building.',
}


class AuditLogQuerySet(QuerySet):
    def update(self, *args, **kwargs):
        """only notes should be updated, so filter out non-notes"""
        self = self.filter(audit_type=NOTE)
        return super(AuditLogQuerySet, self).update(*args, **kwargs)


class AuditLogManager(models.Manager):
    """ExpressionManager with ``update`` preventing the update of non-notes"""
    use_for_related_fields = True

    def get_queryset(self):
        return AuditLogQuerySet(model=self.model, using=self._db)

    def log_action(self, request, conent_object, organization_id,
                   action_note=None, audit_type=LOG):
        if not action_note:
            action_note = ACTION_OPTIONS.get(request.path)
        return AuditLog.objects.create(
            user=request.user,
            content_object=conent_object,
            audit_type=audit_type,
            action=request.path,
            action_note=action_note,
            organization_id=organization_id,
        )


class AuditLog(TimeStampedModel):
    """An audit log of events and notes.
    Inherits ``created`` and ``modified`` from TimeStampedModel
    """
    user = models.ForeignKey(USER_MODEL)
    # Generic Foreign Key next three fields
    content_type = models.ForeignKey(ContentType, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    audit_type = models.IntegerField(default=LOG, choices=AUDIT_CHOICES)
    action = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text='method triggering audit',
        db_index=True,
    )
    action_response = JSONField(default=dict, help_text='HTTP response from action')
    action_note = models.TextField(
        blank=True,
        null=True,
        help_text='either the note text or a description of the action',
    )
    organization = models.ForeignKey(
        Organization,
        related_name='audit_logs'
    )

    class Meta:
        ordering = ('-created',)

    objects = AuditLogManager()

    def __unicode__(self):
        return u'{0} <{1}> ({2})'.format(
            self.get_audit_type_display(), self.user, self.pk
        )

    def save(self, *args, **kwargs):
        """Ensure that only notes are saved"""
        if self.audit_type != NOTE and self.pk:
            raise PermissionDenied('AuditLogs cannot be edited, only notes')

        return super(AuditLog, self).save(*args, **kwargs)

    def to_dict(self):
        """serializes an audit_log"""
        # avoid cyclical import
        from seed.models import obj_to_dict
        log_dict = obj_to_dict(self)
        log_dict['audit_type'] = self.get_audit_type_display()
        log_dict['user'] = {
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'email': self.user.email,
            'id': self.user.pk,
        }
        log_dict['organization'] = {
            'id': self.organization.pk,
            'name': self.organization.name,
        }
        log_dict['content_type'] = self.content_object._meta.model_name
        return log_dict

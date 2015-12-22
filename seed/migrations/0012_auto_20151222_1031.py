# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def merge_extra_data(b1, b2, default=None):
    """
    This is a frozen version of `seed.mappings.mapper.merge_extra_data`
    """
    default = default or b1
    non_default = b2
    if default != b1:
        non_default = b1

    extra_data_sources = {}
    default_extra_data = getattr(default, 'extra_data', {})
    non_default_extra_data = getattr(non_default, 'extra_data', {})

    all_keys = set(default_extra_data.keys() + non_default_extra_data.keys())
    extra_data = {
        k: default_extra_data.get(k) or non_default_extra_data.get(k)
        for k in all_keys
    }

    for item in extra_data:
        if item in default_extra_data and default_extra_data[item]:
            extra_data_sources[item] = default.pk
        elif item in non_default_extra_data and non_default_extra_data[item]:
            extra_data_sources[item] = non_default.pk
        else:
            extra_data_sources[item] = default.pk

    return extra_data, extra_data_sources


def recover_extra_data(app, schema_editor, **kwargs):
    """
    Populate the default labels for each organization.
    """
    BuildingSnapshot = app.get_model("seed", "BuildingSnapshot")

    # Get all snapshots which are the canonical snapshot which also have parent
    # buildings and which DO NOT have any children.
    leaves = BuildingSnapshot.objects.filter(
        pk__in=BuildingSnapshot.objects.filter(
            parents__isnull=False,
            children__isnull=True,
            canonicalbuilding__isnull=False,
        ).values_list('pk', flat=True),
    )
    for leaf_snapshot in leaves:
        merge_extra_data_from_parents(leaf_snapshot)


def merge_extra_data_from_parents(bs):
    for parent in bs.parents.order_by('created').all():
        # First do a recursive call to do a recursive merge of all extra_data
        # fields deeper down the tree.
        merge_extra_data_from_parents(parent)

        # Now do a merge with this bs, prioritizing the data that is already in
        # place which will merge in any non-blank data from deeper down the
        # tree.
        extra_data, extra_data_sources = merge_extra_data(bs, parent)
        bs.extra_data = extra_data
        bs.extra_data_sources = extra_data_sources
        bs.save()


def stub(*args, **kwargs):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('seed', '0011_auto_20151209_0821'),
    ]

    operations = [
        migrations.RunPython(recover_extra_data, stub),
    ]

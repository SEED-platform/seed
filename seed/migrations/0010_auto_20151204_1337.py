# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


DEFAULT_LABELS = [
    "Residential",
    "Non-Residential",
    "Violation",
    "Compliant",
    "Missing Data",
    "Questionable Report",
    "Update Bldg Info",
    "Call",
    "Email",
    "High EUI",
    "Low EUI",
    "Exempted",
    "Extension",
    "Change of Ownership",
]


def populate_default_labels(app, schema_editor, **kwargs):
    """
    Populate the default labels for each organization.
    """
    Label = app.get_model("seed", "StatusLabel")
    SuperOrganization = app.get_model("orgs", "Organization")

    for org in SuperOrganization.objects.all():
        for label in DEFAULT_LABELS:
            Label.objects.get_or_create(
                name=label,
                color='blue',
                super_organization=org,
            )


def stub(*args, **kwargs):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('seed', '0009_merge'),
        ('orgs', '__first__'),
    ]

    operations = [
        migrations.RunPython(populate_default_labels, stub),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

#some of the project buildings point at building snapshot records that are not canonical buildings
#This probably shouldn't be but before the migration for the label changes record them here
#so the users can be alerted that the label changes will not be applied.
def save_non_canonical_project_buildings(app, schema_editor):
    project_building_model = app.get_model("seed", "ProjectBuilding")
    canonical_building_model = app.get_model("seed", "CanonicalBuilding")
    non_canonical_project_buildings_model = app.get_model("seed", "NonCanonicalProjectBuildings")
    
    for building_with_labels in project_building_model.objects.filter(status_label__isnull=False):
        if not canonical_building_model.objects.filter(canonical_snapshot = building_with_labels.building_snapshot.id).exists():
            non_canonical_project_buildings_model.objects.create(projectbuilding = building_with_labels)

class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0004_noncanonicalprojectbuildings'),
    ]

    operations = [migrations.RunPython(save_non_canonical_project_buildings), 
    ]

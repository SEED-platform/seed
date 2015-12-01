# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

#assuming all building_snapshot_ids in seed_projectbuilding point at the canonical building
#For any records that do no point at canonical buildings the labels will be dropped
#but a record is kept via migration 005_auto_20151201_1510
def move_labels(app, schema_editor):
    project_building_model = app.get_model("seed", "ProjectBuilding")
    canonical_building_model = app.get_model("seed", "CanonicalBuilding")
    
    for building_with_labels in project_building_model.objects.filter(status_label__isnull=False):
        for canonical_building in canonical_building_model.objects.filter(canonical_snapshot = building_with_labels.building_snapshot.id):
            canonical_building.labels.add(building_with_labels.status_label)
    


class Migration(migrations.Migration):
    
    
    dependencies = [
        ('seed', '0006_canonicalbuilding_labels'),
    ]

    operations = [ migrations.RunPython(move_labels),
    ]

    
    
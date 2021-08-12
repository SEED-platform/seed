
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.jsonb
import django_extensions.db.fields
# import autoslug.fields
import django.utils.timezone
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

# How to refer to seed_propertystate table for dependencies
    dependencies = [
        # seed_propertystate
    ]

    operations = [
    #   migrations.CreateModel(
    #         name='seed_propertystate',
    #         fields=[
    #             ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
    #             ('ubid', models.CharField(null=False, blank=False)),
    #             ('address_line_1', models.CharField(null=False, blank=False)),
    #             ('state', models.CharField(null=False, blank=False)),
    #             ('postal_code', models.IntegerField(null=False, blank=False)),
    #             ('lot_number', models.IntegerField(null=False, blank=False)),
    #             ('extra_data', models.JSONField()),
    #             ('borough', models.CharField(null=False, blank=False)),
    #             ('block', models.CharField(null=False, blank=False)),
    #             ('dob_bldg_type', models.CharField(null=False, blank=False)),
    #             ('latitude', models.FloatField(null=False, blank=False)),
    #             ('longitude', models.FloatField(null=False, blank=False)),
    #         ],
    #          options={
    #         },
    #         bases=(models.Model,),
    #     ),

# From my understanding, we have a many to one relationship with the foreign keys here.
# There are many permits to one bin
# There are many job applications to one permit
# If my understanding of the foreign keys is correct, is the syntax of the foreign keys written correctly?
        migrations.CreateModel(
            name='permit_issuance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, \
                    auto_created=True, primary_key=True)),
                ('bin', models.ForeignKey(to='seed_propertystate', on_delete=models.CASCADE)),
                ('job_number', models.ForeignKey(to='job_application', on_delete=models.CASCADE)),
                ('work_type', models.CharField(null=True, blank=True)),
                ('permit_status', models.CharField(null=True, blank=True)),
                ('permit_subtype', models.CharField(null=True, blank=True)),
                ('oil_gas', models.CharField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),

# Is job number the primary key on this table? If so, why do we have ID ? Or are they both primary keys?
         migrations.CreateModel(
            name='job_application',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, \
                    auto_created=True, primary_key=True)),
                ('bin', models.IntegerField(null=False, blank=False)),
                ('job_number', models.AutoField(verbose_name='Job_Number', serialize=False, \
                    auto_created=True, primary_key=True)),
                ('job_type', models.CharField(null=True, blank=True)),
                ('doc_number', models.CharField(null=True, blank=True)),
                ('city_owned', models.CharField(null=True, blank=True)),
                ('filed_type', models.CharField(null=True, blank=True)),
                ('plumbing', models.CharField(null=True, blank=True)),
                ('mechanical', models.CharField(null=True, blank=True)),
                ('boiler', models.CharField(null=True, blank=True)),
                ('fuel_burning', models.CharField(null=True, blank=True)),
                ('fuel_Storage', models.CharField(null=True, blank=True)),
                ('equipment', models.CharField(null=True, blank=True)),
                ('other_work_type', models.CharField(null=True, blank=True)),
                ('other_work_type_desc', models.CharField(null=True, blank=True)),
                ('pre_filing_date', models.CharField(null=True, blank=True)),
                ('approved', models.CharField(null=True, blank=True)),
                ('fully_permitted', models.CharField(null=True, blank=True)),
                ('initial_cost', models.CharField(null=True, blank=True)),
                ('existing_zoning_sqft', models.CharField(null=True, blank=True)),
                ('proposed_zoning_sqft', models.CharField(null=True, blank=True)),
                ('enlargement_sq_footage', models.CharField(null=True, blank=True)),
                ('street_frontage', models.CharField(null=True, blank=True)),
                ('current_num_floors', models.IntegerField(null=True, blank=True)),
                ('proposed_num_floors', models.IntegerField(null=True, blank=True)),
                ('current_height', models.IntegerField(null=True, blank=True)),
                ('proposed_height', models.IntegerField(null=True, blank=True)),
                ('proposed_dwelling_units', models.IntegerField(null=True, blank=True)),
                ('current_occupancy', models.IntegerField(null=True, blank=True)),
                ('proposed_occupancy', models.IntegerField(null=True, blank=True)),
                ('total_construction_floor_area', models.IntegerField(null=True, blank=True)),
                ('signoff_date', models.DateField(null=True)),
                ('building_class', models.CharField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
         ),
    ]
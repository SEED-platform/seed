# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def get_cycle(apps, year_ending, org):
    from datetime import datetime
    
    Cycle = apps.get_model("seed", "Cycle")
    year_ending = year_ending.year
    name = "{y} Calendar Year".format(y = year_ending) 
    year_start = datetime(year_ending, 1, 1)
    year_end = datetime(year_ending, 12, 31, 23, 59, 59, 999999)
    obj, created = Cycle.objects.get_or_create(organization = org, name = name, start = year_start, end = year_end)
    obj.save()
    
    return obj

def create_property_record(apps, org, campus, parent_property):
    PropertyModel = apps.get_model("seed", "property")
    rec = PropertyModel.objects.create(organization = org, campus = campus, parent_property = parent_property)
    rec.save()
    return rec

def create_taxlot_record(apps, org):
    TaxLot = apps.get_model("seed", "TaxLot")
    rec = TaxLot.objects.create(organization = org)
    rec.save()
    return rec

def create_property_view_record(apps, property, cycle, property_state):
    PropertyView = apps.get_model("seed", "PropertyView")
    rec = PropertyView.objects.create(property = property, cycle = cycle, state = property_state)
    rec.save()
    return rec

def create_taxlot_view_record(apps, taxlot, cycle, taxlot_state):
    TaxLotView = apps.get_model("seed", "TaxLotView")
    rec = TaxLotView.objects.create(taxlot = taxlot, cycle = cycle, state = taxlot_state)
    rec.save()
    return rec

def create_taxlot_property_record(apps, cycle, property_view, taxlot_view, primary):
    TaxLotProperty = apps.get_model("seed", "TaxLotProperty")
    rec = TaxLotProperty.objects.create(property_view = property_view, taxlot_view = taxlot_view, cycle = cycle, primary = primary)
    rec.save()
    return rec

    
def get_unknown_mappings():
    unknown_mappings = {}
    unknown_mappings[""] ="jurisdiction_property_identifier"    
    unknown_mappings[""] ="building_portfolio_manager_identifier"
    unknown_mappings[""] ="building_home_energy_saver_identifier"
    return unknown_mappings

def get_table_to_table_field_mappings(t_1, t_2, t_2_to_t_1_mappings_name_change):
    get_field_names_from_table = lambda t : [x.attname for x in t._meta.local_fields]
    t_1_fields = get_field_names_from_table(t_1) 
    t_2_fields = get_field_names_from_table(t_2) 
    
    t_1_to_t_2_mappings = {}
    t_2_fields_to_check_for_in_extra_data = []
    
    for t_2_field in t_2_fields:
        idx = None
        try:
            idx = t_1_fields.index(t_2_field)
        except:
            pass
        if idx is not None:
            t_1_to_t_2_mappings[t_1_fields[idx]] = t_2_field 
        else:
            old_field_name = t_2_to_t_1_mappings_name_change.get(t_2_field, None)
            if old_field_name:
                t_1_to_t_2_mappings[old_field_name] = t_2_field
            else:
                t_2_fields_to_check_for_in_extra_data.append(t_2_field)
                
    return t_1_to_t_2_mappings, t_2_fields_to_check_for_in_extra_data  

def get_property_state_to_building_snapshot_field_mapping(apps):
    PropertyState = apps.get_model("seed", "PropertyState")
    BuildingSnapshot = apps.get_model("seed", "BuildingSnapshot")
     
    new_to_old_mappings_name_change = {}
    new_to_old_mappings_name_change["state"] ="state_province"
    
    return get_table_to_table_field_mappings(BuildingSnapshot, PropertyState, new_to_old_mappings_name_change)

def get_taxlot_state_to_building_snapshot_field_mapping(apps):
    TaxLotState = apps.get_model("seed", "TaxLotState")
    BuildingSnapshot = apps.get_model("seed", "BuildingSnapshot")
     
    new_to_old_mappings_name_change = {}
    new_to_old_mappings_name_change["state"] ="state_province"
    
    return get_table_to_table_field_mappings(BuildingSnapshot, TaxLotState, new_to_old_mappings_name_change)
    

def create_new_record(apps, bs_record, new_table, old_to_new_mappings, new_fields_to_check_for_in_extra_data):
    PropertyState = apps.get_model("seed", "PropertyState")
    record_data = {}    
  
    for old_field_name, new_field_name in old_to_new_mappings.items():
        record_data[new_field_name] = getattr(bs_record, old_field_name)
    for field_name in new_fields_to_check_for_in_extra_data:
        record_data[field_name] = bs_record.extra_data.get(field_name, None)
        
    try:
        rec, created = new_table.objects.get_or_create(**record_data)
        rec.save()
    except Exception as e:
        print str(e)
        
    return rec
    
        
def create_property_state_record(apps, bs_record, old_to_new_mappings, new_fields_to_check_for_in_extra_data):
    PropertyState = apps.get_model("seed", "PropertyState")
    return create_new_record(apps, bs_record, PropertyState, old_to_new_mappings, new_fields_to_check_for_in_extra_data)

def create_taxlot_state_record(apps, bs_record, old_to_new_mappings, new_fields_to_check_for_in_extra_data):
    TaxLotState = apps.get_model("seed", "TaxLotState")
    return create_new_record(apps, bs_record, TaxLotState, old_to_new_mappings, new_fields_to_check_for_in_extra_data)



def process_record(apps, bs_record, buildingsnapshot_to_propertystate_mappings, propertystate_fields_to_check_for_in_extra_data, buildingsnapshot_to_taxlot_mappings, taxlot_fields_to_check_for_in_extra_data):
    if bs_record.year_ending is None:
        with open ("/tmp/canonical_with_no_year_ending", "a") as f:
            f.write(str(bs_record.id) + "\n")
            return
        
    org = bs_record.super_organization
    
    property_state_record = create_property_state_record(apps, bs_record, buildingsnapshot_to_propertystate_mappings, propertystate_fields_to_check_for_in_extra_data)
    taxlot_state_record = create_taxlot_state_record(apps, bs_record, buildingsnapshot_to_taxlot_mappings, taxlot_fields_to_check_for_in_extra_data)
    
    #Just default organization for now
    cycle = get_cycle(apps, bs_record.year_ending, org)
    
    #just default the organization, campus, and parent_property fields for now
    property_record = create_property_record(apps, org, campus = False, parent_property = None) 
    
    #just default the organization for now
    taxlot_record = create_taxlot_record(apps, org)
    
    property_view_record = create_property_view_record(apps, property_record, cycle, property_state_record)
    taxlot_view_record = create_taxlot_view_record(apps, taxlot_record, cycle, taxlot_state_record)
    
    #setting primary to True for now
    taxlot_propery_record = create_taxlot_property_record(apps, cycle, property_view_record, taxlot_view_record, primary=True)
        
def process_records(apps, bs_records):
    buildingsnapshot_to_propertystate_mappings, propertystate_fields_to_check_for_in_extra_data = get_property_state_to_building_snapshot_field_mapping(apps)
    buildingsnapshot_to_taxlot_mappings, taxlot_fields_to_check_for_in_extra_data = get_taxlot_state_to_building_snapshot_field_mapping(apps)
        
    for bs_record in bs_records.iterator():
        process_record(apps, bs_record, buildingsnapshot_to_propertystate_mappings, propertystate_fields_to_check_for_in_extra_data, buildingsnapshot_to_taxlot_mappings, taxlot_fields_to_check_for_in_extra_data)    
        
        
    

def migrate_data(apps, schema_editor):
    BuildingSnapshot = apps.get_model("seed", "BuildingSnapshot")
    records_to_migrate = BuildingSnapshot.objects.filter(canonicalbuilding__active=True)    
    process_records(apps, records_to_migrate)

    
class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0014_auto_20160503_1335'),
    ]

    operations = [
                  migrations.RunPython(migrate_data),
    ]

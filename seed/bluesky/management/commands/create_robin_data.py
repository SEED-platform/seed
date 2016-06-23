from __future__ import unicode_literals

from django.db import models, migrations
from django.core.management.base import BaseCommand
from seed.lib.superperms.orgs.models import Organization
from django.apps import apps
import pdb
import copy
import collections
import os
import datetime
#import networkx as nx
#import matplotlib.pyplot as plt
#import pygraphviz
import logging
import itertools
# from IPython import embed
#from networkx.drawing.nx_agraph import graphviz_layout
import seed.bluesky.models
# import numpy as np
# from scipy.sparse import dok_matrix
# from scipy.sparse.csgraph import connected_components
from _localtools import projection_onto_index
from _localtools import get_static_building_snapshot_tree_file
from _localtools import read_building_snapshot_tree_structure
from _localtools import get_core_organizations
from _localtools import get_node_sinks

logging.basicConfig(level=logging.DEBUG)


# tax_lot_columns = tax_lot_extra_data_map.keys()[0]
# property_columns = property_extra_data_map.keys()[0]

tax_lot_extra_data_map = {}
tax_lot_extra_data_map["1552813"] = {"Owner City": "Rust",
                                     "Tax Year": "2012",
                                     "Parcel Gross Area": "25522",
                                     "Use Class": "Hotel",
                                     "Ward": "5",
                                     "X Coordinate": "",
                                     "Y Coordinate": "",
                                     "Owner Name": "Univerity Inn LLC",
                                     "Owner Address": "50 Willow Ave SE",
                                     "Owner State": "CA",
                                     "Owner Zip": "94930",
                                     "Tax Class": "5",
                                     "City Code": "392-129"}

tax_lot_extra_data_map["11160509"] = {"Owner City": "Cleveland",
                                      "Tax Year": "2015",
                                      "Parcel Gross Area": "2,000,000",
                                      "Use Class": "Mixed Use",
                                      "Ward": "6",
                                      "X Coordinate": "",
                                      "Y Coordinate": "",
                                      "Owner Name": "Shops R Us LLC",
                                      "Owner Address": "39200 Wilmington Blvd",
                                      "Owner State": "OH",
                                      "Owner Zip": "93029",
                                      "Tax Class": "4",
                                      "City Code": "502-561"}

tax_lot_extra_data_map["33366555"] =  {"Owner City": "Seattle",
                                       "Tax Year": "2016",
                                       "Parcel Gross Area": "500,000",
                                       "Use Class": "School",
                                       "Ward": "2",
                                       "X Coordinate": "",
                                       "Y Coordinate": "",
                                       "Owner Name": "Montessori Inc",
                                       "Owner Address": "555 East Shore Hwy",
                                       "Owner State": "WA",
                                       "Owner Zip": "",
                                       "Tax Class": "4",
                                       "City Code": "562-123"}



tax_lot_extra_data_map["33366125"] = {"Owner City": "Rust",
                                      "Tax Year": "2011",
                                      "Parcel Gross Area": "25,000",
                                      "Use Class": "School",
                                      "Ward": "2",
                                      "X Coordinate": "",
                                      "Y Coordinate": "",
                                      "Owner Name": "Harry Wills",
                                      "Owner Address": "31 Main",
                                      "Owner State": "CA",
                                      "Owner Zip": "",
                                      "Tax Class": "2",
                                      "City Code": "612-846"}

tax_lot_extra_data_map["33366148"] = {"Owner City": "Seattle",
                                      "Tax Year": "2015",
                                      "Parcel Gross Area": "10,000",
                                      "Use Class": "School",
                                      "Ward": "2",
                                      "X Coordinate": "",
                                      "Y Coordinate": "",
                                      "Owner Name": "Loretta Wilkins",
                                      "Owner Address": "3311253 Highway 56",
                                      "Owner State": "WA",
                                      "Owner Zip": "",
                                      "Tax Class": "4",
                                      "City Code": "955-225N"}

property_extra_data_map = {}
property_extra_data_map[2264] = { "CoStar Property ID": "2312456",
                                  "Organization": "",
                                  "Compliance Required": "Y",
                                  "County": "Contra Costa",
                                  "Date / Last Personal Correspondence": "2/5/2016",
                                  "Does Not Need to Comply": "" }

property_extra_data_map[3020139] = {"CoStar Property ID" : "2453125", 
                                    "Organization" : "",
                                    "Compliance Required" : "Y",
                                    "County" : "Contra Costa",
                                    "Date / Last Personal Correspondence" : "5/6/2016",
                                    "Does Not Need to Comply" : ""}

property_extra_data_map[4828379] = {"CoStar Property ID" : "1245683", 
                                    "Organization" : "",
                                    "Compliance Required" : "Y",
                                    "County" : "Contra Costa",
                                    "Date / Last Personal Correspondence" : "5/12/2016",
                                    "Does Not Need to Comply" : ""}

property_extra_data_map[1154623] = {"CoStar Property ID" : "4467856", 
                                    "Organization" : "",
                                    "Compliance Required" : "Y",
                                    "County" : "Contra Costa",
                                    "Date / Last Personal Correspondence" : "5/6/2016",
                                    "Does Not Need to Comply" : ""}

property_extra_data_map[5233255] = {"CoStar Property ID" : "1234856", 
                                    "Organization" : "",
                                    "Compliance Required" : "Y",
                                    "County" : "Contra Costa",
                                    "Date / Last Personal Correspondence" : "3/15/2016",
                                    "Does Not Need to Comply" : ""}

property_extra_data_map[1311523] = {"CoStar Property ID" : "5412648", 
                                    "Organization" : "Lucky University",
                                    "Compliance Required" : "Y",
                                    "County" : "Contra Costa",
                                    "Date / Last Personal Correspondence" : "",
                                    "Does Not Need to Comply" : ""}

property_extra_data_map[1311524] = {"CoStar Property ID" : "5123456", 
                                    "Organization" : "Lucky University",
                                    "Compliance Required" : "Y",
                                    "County" : "Contra Costa",
                                    "Date / Last Personal Correspondence" : "",
                                    "Does Not Need to Comply" : ""}

property_extra_data_map[1311525] = {"CoStar Property ID" : "2154532", 
                                    "Organization" : "Lucky University",
                                    "Compliance Required" : "Y",
                                    "County" : "Contra Costa",
                                    "Date / Last Personal Correspondence" : "",
                                    "Does Not Need to Comply" : ""}

property_extra_data_map[1311526] = {"CoStar Property ID" : "754863", 
                                    "Organization" : "Lucky University",
                                    "Compliance Required" : "Y",
                                    "County" : "Contra Costa",
                                    "Date / Last Personal Correspondence" : "",
                                    "Does Not Need to Comply" : ""}

property_extra_data_map[1311527] = {"CoStar Property ID" : "1154286", 
                                    "Organization" : "Lucky University",
                                    "Compliance Required" : "Y",
                                    "County" : "Contra Costa",
                                    "Date / Last Personal Correspondence" : "5/5/2015",
                                    "Does Not Need to Comply" : ""}
                                    
property_extra_data_map[1311528] = {"CoStar Property ID" : "2145954", 
                                    "Organization" : "",
                                    "Compliance Required" : "N",
                                    "County" : "",
                                    "Date / Last Personal Correspondence" : "",
                                    "Does Not Need to Comply" : "X"}

property_extra_data_map[6798215] = {"CoStar Property ID" : "", 
                                    "Organization" : "",
                                    "Compliance Required" : "",
                                    "County" : "Contra Costa",
                                    "Date / Last Personal Correspondence" : "",
                                    "Does Not Need to Comply" : ""}


def create_structure():
    org = Organization.objects.create(name = "SampleDataDemo_caseA")
    create_cycle(org)
    create_case_A_objects(org)

    org, _ = Organization.objects.get_or_create(name = "SampleDataDemo_caseB")
    create_cycle(org)
    create_case_B_objects(org)

    org, _ = Organization.objects.get_or_create(name = "SampleDataDemo_caseC")
    create_cycle(org)
    create_case_C_objects(org)

    org, _ = Organization.objects.get_or_create(name = "SampleDataDemo_caseD")
    create_cycle(org)
    create_case_D_objects(org)

    org, _ = Organization.objects.get_or_create(name = "SampleDataDemo_caseALL")
    create_cycle(org)
    create_case_A_objects(org)
    create_case_B_objects(org)
    create_case_C_objects(org)
    create_case_D_objects(org)

    return


def create_cycle(org):
    seed.bluesky.models.Cycle.objects.get_or_create(name="2015 Annual",
                                                    organization = org,
                                                    start=datetime.datetime(2015,1,1),
                                                    end=datetime.datetime(2016,1,1)-datetime.timedelta(seconds=1))
    return


def create_cases(org, tax_lots, properties):
    cycle = seed.bluesky.models.Cycle.objects.filter(organization=org).first()

    for (tl_def, prop_def) in itertools.product(tax_lots, properties):
        property, _ = seed.bluesky.models.Property.objects.get_or_create(organization=org)
        taxlot, _ = seed.bluesky.models.TaxLot.objects.get_or_create(organization=org)

        # Doesn't match
        # LINE 1: ...1'::date AND "bluesky_propertystate"."extra_data" = '{"Does ...
        # HINT:  No operator matches the given name and argument type(s). You might need to add explicit type casts.

        tax_extra_data = tax_lot_extra_data_map[tl_def["jurisdiction_taxlot_identifier"]]
        prop_extra_data = property_extra_data_map[prop_def["building_portfolio_manager_identifier"]]

        prop_state, _ = seed.bluesky.models.PropertyState.objects.get_or_create(**prop_def)

        for k in prop_extra_data:
            prop_state.extra_data[k] = prop_extra_data[k]

        prop_state.save()

        taxlot_state, _ = seed.bluesky.models.TaxLotState.objects.get_or_create(**tl_def)

        for k in tax_extra_data:
            taxlot_state.extra_data[k] = tax_extra_data[k]

        taxlot_state.save()


        taxlot_view, _ = seed.bluesky.models.TaxLotView.objects.get_or_create(taxlot = taxlot, cycle=cycle, state = taxlot_state)
        prop_view, _ = seed.bluesky.models.PropertyView.objects.get_or_create(property=property, cycle=cycle, state = prop_state)

        seed.bluesky.models.TaxLotProperty.objects.get_or_create(property_view = prop_view, taxlot_view = taxlot_view, cycle = cycle)

    return



def create_case_A_objects(org):
    tax_lots = [ {"jurisdiction_taxlot_identifier":"1552813",
                  "address": "050 Willow Ave SE",
                  "city": "Rust",
                  "number_properties": 1}]

    properties = [{ "building_portfolio_manager_identifier": 2264,
                    "property_name": "University Inn",
                    "address_line_1": "50 Willow Ave SE",
                    "city": "Rust",
                    "use_description": "Hotel",
                    "energy_score": 75,
                    "site_eui": 125,
                    "year_ending": datetime.datetime(2015,12,31),
                    "gross_floor_area":12555,
                    "owner": "ULLC",
                    "owner_email": "ULLC@gmail.com",
                    "owner_telephone": "213-852-1238",
                    "property_notes": "Case A-1: 1 Property, 1 Tax Lot"}]

    create_cases(org, tax_lots, properties)
    return


def create_case_B_objects(org):
    tax_lots = [ {"jurisdiction_taxlot_identifier":"11160509",
                  "address": "2655 Welstone Ave NE",
                  "city": "Rust",
                  "number_properties": 2 }]


    properties = [{ "building_portfolio_manager_identifier": 3020139,
                    "property_name": "Hilltop Condos",
                    "address_line_1": "2655 Welstone Ave NE",
                    "city": "Rust",
                    "use_description": "Multi-family housing",
                    "energy_score": 1,
                    "site_eui": 652.3,
                    "year_ending": datetime.datetime(2015,12,31),
                    "gross_floor_area":513852,
                    "owner": "Hilltop LLC",
                    "owner_email": "Hilltop@llc.com",
                    "owner_telephone": "426-512-4533",
                    "property_notes": "Case B-1: Multiple (3) Properties, 1 Tax Lot"},
                  { "building_portfolio_manager_identifier": 4828379,
                    "property_name": "Hilltop Condos",
                    "address_line_1": "2650 Welstone Ave NE",
                    "city": "Rust",
                    "use_description": "Office",
                    "energy_score": None,
                    "site_eui": None,
                    "year_ending": datetime.datetime(2015,12,31),
                    "gross_floor_area":55121,
                    "owner": "Hilltop LLC",
                    "owner_email": "Hilltop@llc.com",
                    "owner_telephone": "213-859-8465",
                    "property_notes": "Case B-1: Multiple (3) Properties, 1 Tax Lot"},
                  { "building_portfolio_manager_identifier": 1154623,
                    "property_name": "Hilltop Condos",
                    "address_line_1": "2700 Welstone Ave NE",
                    "city": "Rust",
                    "use_description": "Retail",
                    "energy_score": 63,
                    "site_eui": 1202,
                    "year_ending": datetime.datetime(2015,12,31),
                    "gross_floor_area":23543,
                    "owner": "Hilltop LLC",
                    "owner_email": "Hilltop@llc.com",
                    "owner_telephone": "213-546-9755",
                    "property_notes": "Case B-1: Multiple (3) Properties, 1 Tax Lot"}
    ]

    create_cases(org, tax_lots, properties)
    return



def create_case_C_objects(org):
    tax_lots = [ {"jurisdiction_taxlot_identifier":"33366555",
                  "address": "521 Elm Street",
                  "city": "Rust"},
                 {"jurisdiction_taxlot_identifier":"33366125",
                  "address": "525 Elm Street",
                  "city": "Rust"
                 },
                 {"jurisdiction_taxlot_identifier":"33366148",
                  "address": "530 Elm Street",
                  "city": "Rust"}]

    properties = [{ "building_portfolio_manager_identifier": 5233255,
                    "property_name": "Montessori Day School",
                    "address_line_1": "512 Elm Street",
                    "city": "Rust",
                    "use_description": "K-12 School",
                    "energy_score": 55,
                    "site_eui": 1358,
                    "year_ending": datetime.datetime(2015,12,31),
                    "gross_floor_area": "20000",
                    "owner": "Norton Schools",
                    "owner_email": "Lee@norton.com",
                    "owner_telephone": "213-555-4368",
                    "property_notes": "Case C: 1 Property, Multiple (3) Tax Lots"}]

    create_cases(org, tax_lots, properties)
    return


def create_case_D_objects(org):
    tax_lots = [ {"jurisdiction_taxlot_identifier":"24651456",
                  "address": "11 Ninth Street",
                  "city": "Rust",
                  "number_properties": 5
                  },
                 {"jurisdiction_taxlot_identifier":"13334485",
                  "address": "93029 Wellington Blvd",
                  "city": "Rust",
                  "number_properties": None,
                 },
                 {"jurisdiction_taxlot_identifier":"23810533",
                  "address": "94000 Wellington Blvd",
                  "city": "Rust",
                  "number_properties": None,
                 }]

    campus = [{ "building_portfolio_manager_identifier": 1311523,
                "property_name": "Lucky University ",
                "address_line_1": "11 Ninth Street",
                "city": "Rust",
                "use_description": "College/University",
                "energy_score": None,
                "site_eui": None,
                "year_ending": datetime.datetime(2015,12,31),
                "gross_floor_area": None,
                "owner": "Lucky University",
                "owner_email": "ralph@lucky.edu",
                "owner_telephone": "224-587-5602",
                "property_notes": "Case D: Campus with Multiple associated buildings"}]

    properties = [
        { "building_portfolio_manager_identifier": 1311524,
          "property_name": "Grange Hall ",
          "address_line_1": "12 Ninth Street",
          "city": "Rust",
          "use_description": "Performing Arts",
          "energy_score": 77,
          "site_eui": 219,
          "year_ending": datetime.datetime(2015,12,31),
          "gross_floor_area": 124523,
          "owner": "Lucky University",
          "owner_email": "ralph@lucky.edu",
          "owner_telephone": "224-587-5602",
          "property_notes": "Case D: Campus with Multiple associated buildings"},
        { "building_portfolio_manager_identifier": 1311525,
          "property_name": "Biology Hall ",
          "address_line_1": "20 Tenth Street",
          "city": "Rust",
          "use_description": "Laboratory",
          "energy_score": 43,
          "site_eui": 84,
          "year_ending": datetime.datetime(2015,12,31),
          "gross_floor_area": 421351,
          "owner": "Lucky University",
          "owner_email": "ralph@lucky.edu",
          "owner_telephone": "224-587-5602",
          "property_notes": "Case D: Campus with Multiple associated buildings"},

                  { "building_portfolio_manager_identifier": 1311526,
                    "property_name": "Rowling Gym ",
                    "address_line_1": "35 Tenth Street",
                    "city": "Rust",
                    "use_description": "Fitness Center/Health Club/Gym",
                    "energy_score": 59,
                    "site_eui": 72,
                    "year_ending": datetime.datetime(2015,12,31),
                    "gross_floor_area": 1234,
                    "owner": "Lucky University",
                    "owner_email": "ralph@lucky.edu",
                    "owner_telephone": "224-587-5602",
                    "property_notes": "Case D: Campus with Multiple associated buildings"},

                  { "building_portfolio_manager_identifier": 1311527,
                    "property_name": "East Computing Hall ",
                    "address_line_1": "93029 Wellington Blvd",
                    "city": "Rust",
                    "use_description": "College/University",
                    "energy_score": 34,
                    "site_eui": 45,
                    "year_ending": datetime.datetime(2015,12,31),
                    "gross_floor_area": 45324,
                    "owner": "Lucky University",
                    "owner_email": "ralph@lucky.edu",
                    "owner_telephone": "224-587-5602",
                    "property_notes": "Case D: Campus with Multiple associated buildings"},
        { "building_portfolio_manager_identifier": 1311528,
          "property_name": "International House",
          "address_line_1": "93029 Wellington Blvd",
          "city": "Rust",
          "use_description": "Residence",
          "energy_score": None,
          "site_eui": None,
          "year_ending": datetime.datetime(2015,12,31),
          "gross_floor_area": 482215,
          "owner": "Lucky University",
          "owner_email": "ralph@lucky.edu",
          "owner_telephone": "224-587-5602",
          "property_notes": "Case D: Campus with Multiple associated buildings"}]

    # I manually create everything here
    cycle = seed.bluesky.models.Cycle.objects.filter(organization=org).first()

    campus_property, __ = seed.bluesky.models.Property.objects.get_or_create(organization=org, campus=True)
    property_objs  = [seed.bluesky.models.Property.objects.get_or_create(organization=org, parent_property=campus_property)[0] for p in properties]

    property_objs.insert(0, campus_property)
    taxlot_objs = [seed.bluesky.models.TaxLot.objects.get_or_create(organization=org)[0] for t in tax_lots]

    property_states = [seed.bluesky.models.PropertyState.objects.get_or_create(**prop_def)[0] for prop_def in itertools.chain(campus, properties)]
    property_views = [seed.bluesky.models.PropertyView.objects.get_or_create(property=property, cycle=cycle, state = prop_state)[0] for (property, prop_state) in zip(property_objs, property_states)]

    taxlot_states = [seed.bluesky.models.TaxLotState.objects.get_or_create(**lot_def)[0] for lot_def in tax_lots]
    taxlot_views = [seed.bluesky.models.TaxLotView.objects.get_or_create(taxlot=taxlot, cycle=cycle, state = taxlot_state)[0] for (taxlot, taxlot_state) in zip(taxlot_objs, taxlot_states)]

    seed.bluesky.models.TaxLotProperty.objects.get_or_create(property_view = property_views[0], taxlot_view = taxlot_views[0], cycle = cycle)
    seed.bluesky.models.TaxLotProperty.objects.get_or_create(property_view = property_views[1], taxlot_view = taxlot_views[0], cycle = cycle)
    seed.bluesky.models.TaxLotProperty.objects.get_or_create(property_view = property_views[2], taxlot_view = taxlot_views[0], cycle = cycle)
    seed.bluesky.models.TaxLotProperty.objects.get_or_create(property_view = property_views[3], taxlot_view = taxlot_views[0], cycle = cycle)

    seed.bluesky.models.TaxLotProperty.objects.get_or_create(property_view = property_views[4], taxlot_view = taxlot_views[1], cycle = cycle)
    seed.bluesky.models.TaxLotProperty.objects.get_or_create(property_view = property_views[4], taxlot_view = taxlot_views[2], cycle = cycle)

    seed.bluesky.models.TaxLotProperty.objects.get_or_create(property_view = property_views[5], taxlot_view = taxlot_views[1], cycle = cycle)
    seed.bluesky.models.TaxLotProperty.objects.get_or_create(property_view = property_views[5], taxlot_view = taxlot_views[2], cycle = cycle)

    return



class Command(BaseCommand):
    def handle(self, *args, **options):
        create_structure()
        return

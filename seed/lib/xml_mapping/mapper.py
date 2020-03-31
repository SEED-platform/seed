# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from __future__ import absolute_import
import logging

_log = logging.getLogger(__name__)

# This is duplicated from BuildingSync.BRICR_STRUCT to avoid cyclical dependencies
# NOTE: this is not a long term solution as the next task is to refactor the parser itself
BRICR_STRUCT = {
    "root": "auc:BuildingSync.auc:Facilities.auc:Facility",
    "return": {
        "address_line_1": {
            "path": "auc:Sites.auc:Site.auc:Address.auc:StreetAddressDetail.auc:Simplified.auc:StreetAddress",
            "required": True,
            "type": "string",
        },
        "city": {
            "path": "auc:Sites.auc:Site.auc:Address.auc:City",
            "required": True,
            "type": "string",
        },
        "state": {
            "path": "auc:Sites.auc:Site.auc:Address.auc:State",
            "required": True,
            "type": "string",
        },
        "postal_code": {
            "path": "auc:Sites.auc:Site.auc:Address.auc:PostalCode",
            "required": True,
            "type": "string",
        },
        "longitude": {
            "path": "auc:Sites.auc:Site.auc:Longitude",
            "required": False,
            "type": "double"
        },
        "latitude": {
            "path": "auc:Sites.auc:Site.auc:Latitude",
            "required": False,
            "type": "double",
        },
        "property_name": {
            "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.@ID",
            "required": True,
            "type": "string",
        },
        "property_type": {
            "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:Sections.auc:Section.auc:OccupancyClassification",
            "required": True,
            "type": "string",
        },
        "year_built": {
            "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:YearOfConstruction",
            "required": True,
            "type": "integer",
        },
        "floors_above_grade": {
            "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:FloorsAboveGrade",
            "required": False,
            "type": "integer",
        },
        "floors_below_grade": {
            "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:FloorsBelowGrade",
            "required": False,
            "type": "integer",
        },
        "premise_identifier": {
            "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:PremisesIdentifiers.auc:PremisesIdentifier",
            "key_path_name": "auc:IdentifierLabel",
            "key_path_value": "Assessor parcel number",
            "value_path_name": "auc:IdentifierValue",
            "required": False,  # temporarily make this False until AT can handle it correctly.
            "type": "string",
        },
        "custom_id_1": {
            "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:PremisesIdentifiers.auc:PremisesIdentifier",
            "key_path_name": "auc:IdentifierCustomName",
            "key_path_value": "Custom ID 1",
            "value_path_name": "auc:IdentifierValue",
            "required": False,
            "type": "string",
        },
        "gross_floor_area": {
            "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:FloorAreas.auc:FloorArea",
            "key_path_name": "auc:FloorAreaType",
            "key_path_value": "Gross",
            "value_path_name": "auc:FloorAreaValue",
            "required": True,
            "type": "double",
        },
        "net_floor_area": {
            "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:FloorAreas.auc:FloorArea",
            "key_path_name": "auc:FloorAreaType",
            "key_path_value": "Net",
            "value_path_name": "auc:FloorAreaValue",
            "required": False,
            "type": "double",
        },
        "footprint_floor_area": {
            "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:FloorAreas.auc:FloorArea",
            "key_path_name": "auc:FloorAreaType",
            "key_path_value": "Footprint",
            "value_path_name": "auc:FloorAreaValue",
            "required": False,
            "type": "double",
        },
    }
}


def build_column_mapping(import_file):
    root_path = BRICR_STRUCT['root']
    return {
        f"{root_path}.{mapping['path']}": ('PropertyState', db_column, 100)
        for db_column, mapping in BRICR_STRUCT['return'].items()
    }

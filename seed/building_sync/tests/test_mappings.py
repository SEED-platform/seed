# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from io import StringIO
import random

from django.test import TestCase
from lxml import etree

from seed.building_sync.building_sync import BuildingSync
from seed.building_sync.mappings import (
    BUILDINGSYNC_URI,
    NAMESPACES,
    build_path,
    children_sorter_factory,
    find_last_in_xpath,
    update_tree,
)


class TestXMLHelpers(TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestXMLHelpers, cls).setUpClass()
        cls.raw_xml = """<?xml version="1.0"?>
        <auc:BuildingSync xmlns:auc="http://buildingsync.net/schemas/bedes-auc/2019">
            <auc:Facilities>
                <auc:Facility ID="Facility-70267093073500">
                    <auc:Sites>
                        <auc:Site ID="SiteType-70267093067900">
                            <auc:Buildings>
                                <auc:Building ID="BuildingType-70267092643620">
                                    <!-- <auc:PremisesName>Example San Francisco Audit Report</auc:PremisesName> -->
                                    <auc:PremisesNotes>Example San Francisco audit report building for import/export.  Input data entered may not necessarily be considered reflective of a typical building.  </auc:PremisesNotes>
                                    <auc:FloorAreas>
                                        <auc:FloorArea>
                                            <auc:FloorAreaType>Cooled only</auc:FloorAreaType>
                                            <auc:FloorAreaValue>40000.0</auc:FloorAreaValue>
                                        </auc:FloorArea>
                                    </auc:FloorAreas>
                                </auc:Building>
                            </auc:Buildings>
                        </auc:Site>
                    </auc:Sites>
                </auc:Facility>
            </auc:Facilities>
        </auc:BuildingSync>
        """

        # setup schema and validate our raw data
        cls.xmlschema = BuildingSync.get_schema(BuildingSync.BUILDINGSYNC_V2_0)
        cls.xmlschema.validate(cls.raw_xml)

    def setUp(self):
        self.tree = etree.parse(StringIO(self.raw_xml))

    def test_find_last_in_xpath_finds_last_element(self):
        # -- Setup
        # auc:PremisesName does not exist in the tree, but everything up to auc:Building does
        xpath = '/'.join([
            '',
            'auc:BuildingSync',
            'auc:Facilities',
            'auc:Facility',
            'auc:Sites',
            'auc:Site',
            'auc:Buildings',
            'auc:Building',
            'auc:PremisesName'])

        # -- Act
        last_element, xpath_remainder = find_last_in_xpath(self.tree, xpath, NAMESPACES)

        # -- Assert
        self.assertEqual(f'{{{BUILDINGSYNC_URI}}}Building', last_element.tag)
        self.assertEqual('auc:PremisesName', xpath_remainder)

    def test_find_last_in_xpath_no_path_remainder(self):
        # -- Setup
        # Full xpath should exist
        xpath = '/'.join([
            '',
            'auc:BuildingSync',
            'auc:Facilities',
            'auc:Facility',
            'auc:Sites',
            'auc:Site',
            'auc:Buildings',
            'auc:Building',
            'auc:PremisesNotes'])

        # -- Act
        last_element, xpath_remainder = find_last_in_xpath(self.tree, xpath, NAMESPACES)

        # -- Assert
        self.assertEqual(f'{{{BUILDINGSYNC_URI}}}PremisesNotes', last_element.tag)
        self.assertEqual('', xpath_remainder)

    def test_build_path_with_single_element_path(self):
        """should be able to build a single element with build_path"""
        # -- Setup
        # element we will build off of
        base_element = self.tree.xpath('/auc:BuildingSync', namespaces=NAMESPACES)
        self.assertEqual(1, len(base_element))
        base_element = base_element[0]

        # path to build (single element)
        path = 'auc:Foo'
        match = base_element.xpath('/auc:BuildingSync/' + path, namespaces=NAMESPACES)
        self.assertEqual(0, len(match))

        # -- Act
        foo_element = build_path(base_element, path)

        # -- Assert
        self.assertEqual(f'{{{BUILDINGSYNC_URI}}}Foo', foo_element.tag)
        match = base_element.xpath('/auc:BuildingSync/auc:Foo', namespaces=NAMESPACES)
        self.assertEqual(1, len(match))

    def test_build_path_with_multielement_path(self):
        """should be able to build multiple elements in a path with build_path"""
        # -- Setup
        # element we will build off of
        base_element = self.tree.xpath('/auc:BuildingSync', namespaces=NAMESPACES)
        self.assertEqual(1, len(base_element))
        base_element = base_element[0]

        # path to build - none of the elements should already exist
        path = 'auc:Foo/auc:Bar/auc:Goo'
        match = base_element.xpath('/auc:BuildingSync/' + path, namespaces=NAMESPACES)
        self.assertEqual(0, len(match))

        # -- Act
        foo_element = build_path(base_element, path)

        # -- Assert
        self.assertEqual(f'{{{BUILDINGSYNC_URI}}}Goo', foo_element.tag)
        match = base_element.xpath('/auc:BuildingSync/' + path, namespaces=NAMESPACES)
        self.assertEqual(1, len(match))

    def test_build_path_with_conditional_elements(self):
        # -- Setup
        # element we will build off of
        base_element = self.tree.xpath('/auc:BuildingSync', namespaces=NAMESPACES)
        self.assertEqual(1, len(base_element))
        base_element = base_element[0]

        # path to build - Foo, nor Bar with text "Hello", nor Goo exist
        # Note that Bar and Goo are siblings here, and both should be created
        path = 'auc:Foo[auc:Bar="Hello"]/auc:Goo'
        match = base_element.xpath('/auc:BuildingSync/' + path, namespaces=NAMESPACES)
        self.assertEqual(0, len(match))

        # -- Act
        foo_element = build_path(base_element, path)

        # -- Assert
        self.assertEqual(f'{{{BUILDINGSYNC_URI}}}Goo', foo_element.tag)
        match = base_element.xpath('/auc:BuildingSync/' + path, namespaces=NAMESPACES)
        self.assertEqual(1, len(match))

    def test_children_sorter_factory_sorts_building_element_children(self):
        # -- Setup
        xpath = '/'.join([
            '',
            'auc:BuildingSync',
            'auc:Facilities',
            'auc:Facility',
            'auc:Sites',
            'auc:Site',
            'auc:Buildings',
            'auc:Building'])
        building_element = self.tree.xpath(xpath, namespaces=NAMESPACES)
        self.assertEqual(1, len(building_element))
        building_element = building_element[0]

        # some of the first subelement tags of Building in sorted order
        sorted_tag_order = [
            'PremisesName',
            'PremisesNotes',
            'Address',
            'ClimateZoneType',
            'eGRIDRegionCode',
            'WeatherDataStationID',
        ]

        elements = [etree.Element(f'{{{BUILDINGSYNC_URI}}}{tag}') for tag in sorted_tag_order]
        # shuffle elements -- already verified seed doesn't result in same ordered list
        random.seed(4)
        random.shuffle(elements)

        # -- Act
        getkey = children_sorter_factory(self.xmlschema, self.tree, building_element)
        sorted_elements = sorted(elements, key=getkey)

        # -- Assert
        actual_tag_order = [
            element.tag.replace(f'{{{BUILDINGSYNC_URI}}}', '')
            for element in sorted_elements
        ]
        self.assertListEqual(sorted_tag_order, actual_tag_order)

    def test_update_tree_changes_text_on_existing_element(self):
        # -- Setup
        # Full xpath should exist
        xpath = '/'.join([
            '',
            'auc:BuildingSync',
            'auc:Facilities',
            'auc:Facility',
            'auc:Sites',
            'auc:Site',
            'auc:Buildings',
            'auc:Building',
            'auc:PremisesNotes'])
        self.assertEqual(1, len(self.tree.xpath(xpath, namespaces=NAMESPACES)))

        # -- Act
        value = 'FooBar123'
        update_tree(self.xmlschema, self.tree, xpath, 'text', value, NAMESPACES)

        # -- Assert
        notes_element = self.tree.xpath(xpath, namespaces=NAMESPACES)
        self.assertEqual(1, len(notes_element))
        notes_element = notes_element[0]
        self.assertEqual(value, notes_element.text)
        # tree should remain valid as well after inserting
        self.xmlschema.validate(etree.tostring(self.tree).decode())

    def test_update_tree_changes_text_on_nonexisting_element(self):
        # -- Setup
        # auc:PremisesName does not exist in the tree
        xpath = '/'.join([
            '',
            'auc:BuildingSync',
            'auc:Facilities',
            'auc:Facility',
            'auc:Sites',
            'auc:Site',
            'auc:Buildings',
            'auc:Building',
            'auc:PremisesName'])
        self.assertEqual(0, len(self.tree.xpath(xpath, namespaces=NAMESPACES)))

        # -- Act
        value = 'FooBar123'
        update_tree(self.xmlschema, self.tree, xpath, 'text', value, NAMESPACES)

        # -- Assert
        name_element = self.tree.xpath(xpath, namespaces=NAMESPACES)
        self.assertEqual(1, len(name_element))
        name_element = name_element[0]
        self.assertEqual(value, name_element.text)
        # tree should remain valid as well after inserting
        self.xmlschema.validate(etree.tostring(self.tree).decode())

    def test_update_tree_changes_attribute_on_existing_element(self):
        # -- Setup
        # Full xpath should exist
        xpath = '/'.join([
            '',
            'auc:BuildingSync',
            'auc:Facilities',
            'auc:Facility',
            'auc:Sites',
            'auc:Site',
            'auc:Buildings',
            'auc:Building'])
        self.assertEqual(1, len(self.tree.xpath(xpath, namespaces=NAMESPACES)))

        # -- Act
        value = 'NewID'
        update_tree(self.xmlschema, self.tree, xpath, '@ID', value, NAMESPACES)

        # -- Assert
        building_element = self.tree.xpath(xpath, namespaces=NAMESPACES)
        self.assertEqual(1, len(building_element))
        building_element = building_element[0]
        self.assertEqual(value, building_element.get('ID'))
        # tree should remain valid as well after inserting
        self.xmlschema.validate(etree.tostring(self.tree).decode())

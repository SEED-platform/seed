import copy
from datetime import datetime

import pytz
from lxml import etree


BUILDINGSYNC_URI = 'http://buildingsync.net/schemas/bedes-auc/2019'
NAMESPACES = {
    'auc': BUILDINGSYNC_URI
}
etree.register_namespace('auc', BUILDINGSYNC_URI)

"""
A BuildingSync mapping is expected to be structured like this
    {
        'xpath': <xpath>,
        'type': 'value' | 'list' | 'object',
        ('properties'): <dict of mapping objects>,
        ('items'): <dict of mapping objects>,
        ('value'): 'text' | '@<attribute name' | 'exist' | 'tag',
        ('formatter'): <formatter function>
    }
xpath: the xpath to the target element (relative to the parent mapping if there is one)
type: determines what's returned from the mapping.
  - 'value' returns a simple value (string, int)
  - 'list' indicates this is an element with multiple instances (e.g. auc:Scenario), and will return a mapping for each one. these list 'items' are indicated by the 'items' array
  - 'object' returns a dict. the dict properties come from the 'properties' field
properties: a dict of mapping objects used for the 'object' type. If the type is 'object', this field must be defined.
  - the key will be used in the resulting dict to point to the mapped value
  - value is the mapped result
items: a dict of mapping objects used for the 'list' type. If the type is 'list', this field must be defined.
  - the key will be used in each resulting dict to point to the mapped value
  - the value is the mapped result for a single element
value: a string indicating what value to grab from the element
  - 'text' returns the text content
  - '@<attribute>' returns the value of an attribute. e.g. if we wanted IDref, we'd use '@IDref'
  - 'exist' returns a boolean as to whether or not the targeted element exists
  - 'tag' returns the tag of the element
formatter: a function which takes a string and returns another value. e.g. parsing a datetime string
"""


#
# -- GENERAL functions
#
def table_mapping_to_buildingsync_mapping(table_mapping):
    """Converts a mapping returned from ColumnMapping.get_column_mappings_by_table_name
    into the structure expected by the BuildingSync functions

    expected structure of table_mapping:
    {
      'PropertyState': {
        <full xpath>: ('PropertyState', <db column>),
        ....
      }
    }

    :param table_mapping: dict, a table mapping
    :return: dict, a buildingsync style mapping
    """
    # NOTE: currently only looks at property state mappings
    property_state_mapping = table_mapping.get('PropertyState')
    if property_state_mapping is None:
        return None

    property_base_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site'
    bsync_property_mapping = {}
    for full_xpath, mapping_info in property_state_mapping.items():
        # since get_column_mappings_by_table_name might return mappings not related
        # to xml mapping, we need to skip any raw column names that aren't actually xml paths
        if not full_xpath.startswith('/auc:BuildingSync'):
            continue

        db_column = mapping_info[1]
        sub_xpath = full_xpath.replace(property_base_xpath, '').lstrip('/')
        bsync_property_mapping[db_column] = {
            'xpath': sub_xpath
        }

    if bsync_property_mapping:
        return {
            'property': {
                'xpath': property_base_xpath,
                'properties': bsync_property_mapping
            }
        }

    # no mappings for xml found
    return None


#
# -- IMPORT functions
#
def get_terminal_value(element, mapping):
    """returns a value for an element given a mapping rule

    :param element: ElementTree.Element, element to evaluate
    :param mapping: dict, should have key 'value' specifying how to evaluate the element

    :return: mixed
    """
    if mapping['value'] == 'text':
        return element.text

    if mapping['value'].startswith('@'):
        return element.get(mapping['value'].replace('@', ''))

    if mapping['value'] == 'exist':
        return element is not None

    if mapping['value'] == 'tag':
        prefix, has_namespace, postfix = element.tag.partition('}')
        if has_namespace:
            return postfix
        return prefix

    raise Exception(f'Unrecognized value type \"{mapping["value"]}\"')


def apply_mapping(element, mapping, messages, namespaces, xpaths_as_keys=False):
    """Recursively applies xpath rules to tree elements in order to parse values

    :param element: Element, the base node to apply xpaths to
    :param mapping: dict, a dictionary defining a mapping
    :param xpaths_as_keys: bool, if True then the xpaths are used as keys in the result
    :return: dict, the processed node
    """
    result = {}
    for key, value_map in mapping.items():
        if xpaths_as_keys:
            key = value_map['xpath']
        try:
            selection = element.xpath(value_map['xpath'], namespaces=namespaces)
        except Exception as e:
            raise Exception(f'Error on {value_map["xpath"]}: {e}')

        if len(selection) == 0:
            if value_map['type'] == 'value':
                result[key] = None
            elif value_map['type'] == 'list':
                result[key] = []
            else:
                result[key] = {}

            continue

        if value_map['type'] == 'list':
            result[key] = []
            for selected_element in selection:
                result[key].append(apply_mapping(selected_element, value_map['items'], messages, namespaces, xpaths_as_keys))

        elif value_map['type'] == 'object':
            selected_element = selection[0]
            result[key] = apply_mapping(selected_element, value_map['properties'], messages, namespaces, xpaths_as_keys)

        elif value_map['type'] == 'value':
            selected_element = selection[0]
            value = get_terminal_value(selected_element, value_map)
            # apply formatter if one was provided
            value = value_map['formatter'](value) if value_map.get('formatter') else value
            result[key] = value

        else:
            raise Exception(f"Unknown node type {value_map['type']}")

    return result


def merge_mappings(base_mapping, custom_mapping):
    """merges two mapping dicts into one. Currently only merges the 'property' mapping
    objects as those are the only ones we allow users to modify currently

    :param base_mapping: dict, a base mapping
    :param custom_mapping: dict, a user-defined mapping. higher priority over the base mapping
    :return: dict, merged mapping
    """
    if custom_mapping is None or custom_mapping.get('property') is None:
        return copy.deepcopy(base_mapping)

    merged_mappings = copy.deepcopy(base_mapping)
    for field, mapping in custom_mapping['property']['properties'].items():
        merged_mappings['property']['properties'][field]['xpath'] = mapping['xpath']

    return merged_mappings


def xpath_to_column_map(mapping):
    """creates a reverse mapping with xpaths (full path) as the keys and column
    names as the values

    :param mapping: dict, a mapping
    """
    # NOTE: current implementation only returns information for property (no meters, scenarios, etc)
    base_path = mapping['property']['xpath'].rstrip('/')
    result = {}
    for col_name, col_info in mapping['property']['properties'].items():
        sub_path = col_info['xpath'].replace('./', '')
        full_path = f'{base_path}/{sub_path}'
        result[full_path] = col_name

    return result


def to_energy_type(energy_type):
    """converts an energy type from BuildingSync into one allowed by SEED

    :param energy_type: string, building sync energy type
    :return: int | None
    """
    # avoid circular dependency
    from seed.models import Meter

    if energy_type is None:
        return energy_type

    # valid energy type values from the schema (<xs:simpleType name="FuelTypes">) and their maps
    # non-trivial or non-obvious mappings currently map to "Other:" and are flagged with a comment
    # this mapping is important for unit generation... see "kbtu_thermal_conversion_factors"
    energy_name = {
        'Electricity': 'Electric - Grid',
        'Electricity-Exported': 'Electric - Grid',
        'Electricity-Onsite generated': 'Other:',                   # other?
        'Natural gas': 'Natural Gas',
        'Fuel oil': 'Other:',                                       # other?
        'Fuel oil no 1': 'Fuel oil (No. 1)',
        'Fuel oil no 2': 'Fuel Oil (No. 2)',
        'Fuel oil no 4': 'Fuel Oil (No. 4)',
        'Fuel oil no 5': 'Other:',                                  # other?
        'Fuel oil no 5 (light)': 'Other:',                          # other?
        'Fuel oil no 5 (heavy)': 'Other:',                          # other?
        'Fuel oil no 6': 'Fuel Oil (No. 5 and No. 6)',              # other?
        'Fuel oil no 5 and no 6': 'Fuel Oil (No. 5 and No. 6)',
        'District steam': 'District Steam',
        'District hot water': 'District Hot Water',
        'District chilled water': 'District Chilled Water - Other',  # correct mapping?
        'Propane': 'Propane',
        'Liquid propane': 'Propane',
        'Kerosene': 'Kerosene',
        'Diesel': 'Diesel',
        'Coal': 'Other:',                                           # other?
        'Coal anthracite': 'Coal (anthracite)',
        'Coal bituminous': 'Coal (bituminous)',
        'Coke': 'Coke',
        'Wood': 'Wood',
        'Wood pellets': 'Wood',
        'Hydropower': 'Other:',                                     # other?
        'Biofuel': 'Other:',                                        # other?
        'Biofuel B5': 'Other:',                                     # other?
        'Biofuel B10': 'Other:',                                    # other?
        'Biofuel B20': 'Other:',                                    # other?
        'Wind': 'Electric - Wind',
        'Geothermal': 'Other:',                                     # other?
        'Solar': 'Electric - Solar',
        'Biomass': 'Other:',                                        # other?
        'Hydrothermal': 'Other:',                                   # other?
        'Dry steam': 'Other:',                                      # other?
        'Flash steam': 'Other:',                                    # other?
        'Ethanol': 'Other:',                                        # other?
        'Biodiesel': 'Other:',                                      # other?
        'Waste heat': 'Other:',                                     # other?
        'Dual fuel': 'Other:',                                      # other?
        'Gasoline': 'Other:',                                       # other?
        'Thermal-Exported': 'Other:',                               # other?
        'Thermal-Onsite generated': 'Other:',                       # other?
        'Other delivered-Exported': 'Other:',                       # other?
        'Other delivered-Onsite generated': 'Other:',               # other?
        'Other metered-Exported': 'Other:',                         # other?
        'Other metered-Onsite generated': 'Other:',                 # other?
        'Other': 'Other:',
        'Unknown': 'Other:',                                        # other?
    }.get(energy_type, energy_type).lower()
    for energy_pair in Meter.ENERGY_TYPES:
        if energy_pair[1].lower() == energy_name:
            return energy_pair[0]

    # couldn't find this energy type... default to "Other:"
    return Meter.ENERGY_TYPES.OTHER


def to_energy_units(units):
    """converts energy units from BuildingSync into one allowed by SEED

    :param units: string, building sync units
    :return: string | None
    """

    if units is None:
        return None

    # valid energy unit values from the schema (<xs:element name="ResourceUnits">) and their maps
    # non-trivial or non-obvious mappings currently map to "Unknown" and are flagged with a comment
    # this mapping is important for unit generation... see "kbtu_thermal_conversion_factors"
    return {
        'Cubic Meters': 'cm (cubic meters)',
        'kcf': 'kcf (thousand cubic feet)',
        'MCF': 'Mcf (million cubic feet)',
        'Gallons': 'Gallons (US)',
        'Wh': 'Wh (Watt-hours)',
        'kWh': 'kWh (thousand Watt-hours)',
        'MWh': 'MWh (million Watt-hours)',
        'Btu': 'Btu',
        'kBtu': 'kBtu (thousand Btu)',
        'MMBtu': 'MBtu/MMBtu (million Btu)',
        'therms': 'therms',
        'lbs': 'Lbs. (pounds)',
        'Klbs': 'kLbs. (thousand pounds)',
        'Mlbs': 'MLbs. (million pounds)',
        'Mass ton': 'Tons',                     # assuming "Tons" over "Tonnes (metric)"
        'Ton-hour': 'ton hours',
        'Other': 'Unknown',
        'Unknown': 'Unknown',
        'None': 'None',
    }.get(units, "Unknown")


def to_float(value):
    return float(value)


def to_int(value):
    return int(value)


def to_bool(value):
    return value.lower() == "true"


def to_datetime(value):
    try:
        res = pytz.utc.localize(datetime.strptime(value, "%Y-%m-%dT%H:%M:%S"))
        return res
    except ValueError as e:
        # parsing datetime with a timezone containing a colon is problematic for python < 3.7
        # https://stackoverflow.com/questions/30999230/how-to-parse-timezone-with-colon
        if ":" == value[-3:-2]:
            value = value[:-3] + value[-2:]
            res = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
            return res
        raise e


def snake_case(value):
    # avoid circular dependency
    from seed.models.measures import _snake_case

    return _snake_case(value)


def to_application_scale(app_scale):
    return app_scale


def to_impl_status(impl_status):
    return impl_status


#
# -- EXPORT functions
#
def find_last_in_xpath(tree, xpath, namespaces):
    """Returns the element which matches the most of the xpath in addition to the remaining
    path after that element. E.g. if the tree had /Foo1/Bar1 defined, and our xpath was
    '/Foo1/Bar1/Foo2/Bar2', it'd return Bar1 as well as 'Foo2/Bar2'

    :param tree: lxml.ElementTree, tree to search
    :param xpath: string, an absolute xpath (ie should start with /auc:BuildingSync/...)
    """
    remainder = []
    xpath_list = xpath.split('/')
    match = tree.xpath('/' + '/'.join(xpath_list), namespaces=namespaces)
    while xpath_list and not match:
        remainder.insert(0, xpath_list.pop())
        match = tree.xpath('/' + '/'.join(xpath_list), namespaces=namespaces)

    if not match:
        raise Exception(f'Failed to find any elements, xpath is probably invalid: "{xpath}"')

    return match[0], '/'.join(remainder)


def parse_xpath_part(xpath_part):
    """parses a single part of an xpath into its parts: primary tag, conditional
    child tag name, and conditional child value. Namespaces are stripped from the tags

    e.g. 'auc:FloorArea[auc:FloorAreaType="Net"]' returns "FloorArea", "FloorAreaType", "Net"
    e.g. 'auc:FloorArea' returns "FloorArea", None, None

    :param xpath_part: string, a single part of an xpath
    :returns: tuple, [string, string | None, string | None]
    """
    tag = xpath_part.replace('auc:', '')

    child_tag, child_value = None, None
    if '[' in tag:
        tag, xpath_condition = tag.split('[')
        child_tag, child_value = xpath_condition.replace(']', '').split('=')
        child_tag = child_tag.replace('auc:', '')
        child_value = child_value.replace('"', '')

    return tag, child_tag, child_value


def _build_path(element, xpath_list):
    """Internal implementation of build_path. Refer to its docs

    :param element: lxml.Element, element to build off of
    :param xpath_list: list, a list of strings which represent parts of the xpath (ie xpath split on "/")
    """
    if not xpath_list:
        # terminal case, everything has been built
        return element

    next_xpath_part = xpath_list.pop(0)
    tag, child_tag, child_value = parse_xpath_part(next_xpath_part)

    new_element = etree.SubElement(element, f'{{{BUILDINGSYNC_URI}}}{tag}')
    if child_tag:
        new_element_child = etree.SubElement(new_element, f'{{{BUILDINGSYNC_URI}}}{child_tag}')
        new_element_child.text = child_value

    return _build_path(new_element, xpath_list)


def build_path(element, xpath):
    """creates all elements in the xpath, starting from the given element.
    NOTE: it does not check if any elements in the xpath already exist, it creates
    them indiscriminantly.

    It is able to handle xpaths with simple conditionals. E.g. if the xpath was
    Foo[BarColor="Yellow"]/BarFont, it would create the elements that'd look
    like this:
    <baseelement>
        <Foo>
            <BarColor>Yellow</BarColor>
            <BarFont></BarFont>
        </Foo>
    </baseelement>

    :param element: lxml.Element, element to build off
    :param xpath: string, xpath to create
    """
    xpath_list = xpath.split('/')
    return _build_path(element, xpath_list)


def children_sorter_factory(schema, tree, element):
    """returns a function for getting a key value for sorting elements

    Used to sort an elements children after inserting a new element to ensure
    it meets the schema sequence specification

    :param schema: xmlschema.XmlSchema, the schema to follow
    :param tree: ElementTree, the tree from which the element came from
    :param element: Element, the element whose children are to be sorted
    """
    # get the element from the schema
    element_path = tree.getpath(element)
    schema_element = schema.find(element_path)
    if schema_element is None:
        raise Exception(f'Unable to find path in schema: "{element_path}"')

    ordered_children = [child.name for child in schema_element.iterchildren()]

    # construct a function for sorting an element's children by returning the index of the
    # child according to the ordering of the schema
    def _getkey(element):
        if isinstance(element, etree._Comment):
            # put comments at the end
            return 1e10
        elif not isinstance(element, etree._Element):
            raise Exception(f'Unknown type while sorting: "{type(element)}"')

        if element.tag not in ordered_children:
            # a more helpful exception that the one raised by .index()
            raise Exception(f'Failed to find "{element.tag}" in {ordered_children}')

        return ordered_children.index(element.tag)

    return _getkey


def update_element(element, target, value):
    """updates an element's text or attribute with a value

    :param element: lxml.Element, element to update
    :param target: string, an attribute as "@<attribute>" or "text"
    :param value: string, value to set for target
    """
    if target.startswith('@'):
        element.set(target[1:], value)
    elif target == 'text':
        element.text = value
    else:
        raise Exception(f'Unrecognized target "{target}"')


def update_tree(schema, tree, xpath, target, value, namespaces):
    """updates the tree at the xpath with the given value

    :param schema: xmlschema.XmlSchema, schema for determining sequence ordering
    :param tree: lxml.ElementTree, tree to update
    :param xpath: string, absolute xpath to the element to update (i.e. starts with /auc:BuildingSync/...)
    :param target: string, an attribute, "@<attribute>", or "text" to indicate what to update on the element
    :param value: string, the value to set for that node
    """
    last_element, xpath_remainder = find_last_in_xpath(tree, xpath, namespaces)

    if xpath_remainder:
        # build out the remaining path and then update the value
        new_element = build_path(last_element, xpath_remainder)
        update_element(new_element, target, value)

        # since we added new elements, we need to reorder at the base of our addition
        getkey = children_sorter_factory(schema, tree, last_element)
        last_element[:] = sorted(last_element, key=getkey)
    else:
        # element already exists, update its value
        update_element(last_element, target, value)


# Base mapping for BuildingSync schema version 2.x
BASE_MAPPING_V2 = {
    'property': {
        'xpath': '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site',
        'type': 'object',
        'properties': {
            'address_line_1': {
                'xpath': './auc:Buildings/auc:Building/auc:Address/auc:StreetAddressDetail/auc:Simplified/auc:StreetAddress',
                'type': 'value',
                'value': 'text',
            },
            'city': {
                'xpath': './auc:Buildings/auc:Building/auc:Address/auc:City',
                'type': 'value',
                'value': 'text',
            },
            'state': {
                'xpath': './auc:Buildings/auc:Building/auc:Address/auc:State',
                'type': 'value',
                'value': 'text',
            },
            'postal_code': {
                'xpath': './auc:Buildings/auc:Building/auc:Address/auc:PostalCode',
                'type': 'value',
                'value': 'text',
            },
            'longitude': {
                'xpath': './auc:Buildings/auc:Building/auc:Longitude',
                'type': 'value',
                'value': 'text',
                'formatter': to_float,
            },
            'latitude': {
                'xpath': './auc:Buildings/auc:Building/auc:Latitude',
                'type': 'value',
                'value': 'text',
                'formatter': to_float,
            },
            'property_name': {
                'xpath': './auc:Buildings/auc:Building',
                'type': 'value',
                'value': '@ID',
            },
            'property_type': {
                'xpath': './auc:Buildings/auc:Building/auc:Sections/auc:Section/auc:OccupancyClassification',
                'type': 'value',
                'value': 'text',
            },
            'year_built': {
                'xpath': './auc:Buildings/auc:Building/auc:YearOfConstruction',
                'type': 'value',
                'value': 'text',
                'formatter': to_int,
            },
            'floors_above_grade': {
                'xpath': './auc:Buildings/auc:Building/auc:FloorsAboveGrade',
                'type': 'value',
                'value': 'text',
                'formatter': to_int,
            },
            'floors_below_grade': {
                'xpath': './auc:Buildings/auc:Building/auc:FloorsBelowGrade',
                'type': 'value',
                'value': 'text',
                'formatter': to_int,
            },
            'premise_identifier': {
                'xpath': './auc:Buildings/auc:Building/auc:PremisesIdentifiers/auc:PremisesIdentifier[auc:IdentifierLabel="Assessor parcel number"]/auc:IdentifierValue',
                'type': 'value',
                'value': 'text',
            },
            'custom_id_1': {
                'xpath': './auc:Buildings/auc:Building/auc:PremisesIdentifiers/auc:PremisesIdentifier[auc:IdentifierCustomName="Custom ID 1"]/auc:IdentifierValue',
                'type': 'value',
                'value': 'text',
            },
            'gross_floor_area': {
                'xpath': './auc:Buildings/auc:Building/auc:FloorAreas/auc:FloorArea[auc:FloorAreaType="Gross"]/auc:FloorAreaValue',
                'type': 'value',
                'value': 'text',
                'formatter': to_float,
                'units': 'ft**2',
            },
            'net_floor_area': {
                'xpath': './auc:Buildings/auc:Building/auc:FloorAreas/auc:FloorArea[auc:FloorAreaType="Net"]/auc:FloorAreaValue',
                'type': 'value',
                'value': 'text',
                'formatter': to_float,
            },
            'footprint_floor_area': {
                'xpath': './auc:Buildings/auc:Building/auc:FloorAreas/auc:FloorArea[auc:FloorAreaType="Footprint"]/auc:FloorAreaValue',
                'type': 'value',
                'value': 'text',
                'formatter': to_float,
            }
        }
    },
    'measures': {
        'xpath': '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Measures/auc:Measure',
        'type': 'list',
        'items': {
            'property_measure_name': {
                'xpath': '.',
                'type': 'value',
                'value': '@ID'
            },
            'category': {
                'xpath': './auc:TechnologyCategories/auc:TechnologyCategory/*[1]',
                'type': 'value',
                'value': 'tag',
                'formatter': snake_case
            },
            'name': {
                'xpath': './auc:TechnologyCategories/auc:TechnologyCategory/*[1]//auc:MeasureName',
                'type': 'value',
                'value': 'text',
                'formatter': snake_case
            },
            'implementation_status': {
                'xpath': './auc:ImplementationStatus',
                'type': 'value',
                'value': 'text',
                'formatter': to_impl_status
            },
            'application_scale_of_application': {
                'xpath': './auc:MeasureScaleOfApplication',
                'type': 'value',
                'value': 'text',
            },
            'system_category_affected': {
                'xpath': './auc:SystemCategoryAffected',
                'type': 'value',
                'value': 'text',
                'formatter': to_application_scale
            },
            'recommended': {
                'xpath': './auc:Recommended',
                'type': 'value',
                'value': 'text',
                'formatter': to_bool
            },
            'measure_total_first_cost': {
                'xpath': './auc:MeasureTotalFirstCost',
                'type': 'value',
                'value': 'text',
                'formatter': to_float
            },
            'measure_installation_cost': {
                'xpath': './auc:MeasureInstallationCost',
                'type': 'value',
                'value': 'text',
                'formatter': to_float
            },
            'measure_material_cost': {
                'xpath': './auc:MeasureMaterialCost',
                'type': 'value',
                'value': 'text',
                'formatter': to_float
            },
            'mv_cost': {
                'xpath': './auc:MVCost',
                'type': 'value',
                'value': 'text',
                'formatter': to_float
            },
            'useful_life': {
                'xpath': './auc:UsefulLife',
                'type': 'value',
                'value': 'text',
                'formatter': to_float
            }
        }
    },
    'scenarios': {
        'xpath': '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Reports/auc:Report/auc:Scenarios/auc:Scenario',
        'type': 'list',
        'items': {
            'id': {
                'xpath': '.',
                'type': 'value',
                'value': '@ID'
            },
            'name': {
                'xpath': './auc:ScenarioName',
                'type': 'value',
                'value': 'text'
            },
            'reference_case': {
                'xpath': './auc:ScenarioType/auc:PackageOfMeasures/auc:ReferenceCase',
                'type': 'value',
                'value': '@IDref'
            },
            'annual_site_energy_savings': {
                'xpath': './auc:ScenarioType/auc:PackageOfMeasures/auc:AnnualSavingsSiteEnergy',
                'type': 'value',
                'value': 'text',
            },
            'annual_source_energy_savings': {
                'xpath': './auc:ScenarioType/auc:PackageOfMeasures/auc:AnnualSavingsSourceEnergy',
                'type': 'value',
                'value': 'text',
            },
            'annual_cost_savings': {
                'xpath': './auc:ScenarioType/auc:PackageOfMeasures/auc:AnnualSavingsCost',
                'type': 'value',
                'value': 'text',
            },
            'annual_electricity_savings': {
                'xpath': './auc:ScenarioType/auc:PackageOfMeasures/auc:AnnualSavingsByFuels/auc:AnnualSavingsByFuel[auc:EnergyResource="Electricity"]/auc:AnnualSavingsNativeUnits',
                'type': 'value',
                'value': 'text'
            },
            'annual_natural_gas_savings': {
                'xpath': './auc:ScenarioType/auc:PackageOfMeasures/auc:AnnualSavingsByFuels/auc:AnnualSavingsByFuel[auc:EnergyResource="Natural gas"]/auc:AnnualSavingsNativeUnits',
                'type': 'value',
                'value': 'text'
            },
            'annual_site_energy': {
                'xpath': './auc:AllResourceTotals/auc:AllResourceTotal[auc:EndUse="All end uses"]/auc:SiteEnergyUse',
                'type': 'value',
                'value': 'text'
            },
            'annual_site_energy_use_intensity': {
                'xpath': './auc:AllResourceTotals/auc:AllResourceTotal[auc:EndUse="All end uses"]/auc:SiteEnergyUseIntensity',
                'type': 'value',
                'value': 'text'
            },
            'annual_source_energy': {
                'xpath': './auc:AllResourceTotals/auc:AllResourceTotal[auc:EndUse="All end uses"]/auc:SourceEnergyUse',
                'type': 'value',
                'value': 'text'
            },
            'annual_source_energy_use_intensity': {
                'xpath': './auc:AllResourceTotals/auc:AllResourceTotal[auc:EndUse="All end uses"]/auc:SourceEnergyUseIntensity',
                'type': 'value',
                'value': 'text'
            },
            'annual_electricity_energy': {
                'xpath': './auc:ResourceUses/auc:ResourceUse[auc:EnergyResource="Electricity"]/auc:AnnualFuelUseConsistentUnits',
                'type': 'value',
                'value': 'text'
            },
            'annual_peak_demand': {
                'xpath': './auc:ResourceUses/auc:ResourceUse[auc:EnergyResource="Electricity"]/auc:AnnualPeakConsistentUnits',
                'type': 'value',
                'value': 'text'
            },
            'annual_peak_electricity_reduction': {
                'xpath': './auc:ScenarioType/auc:PackageOfMeasures/auc:AnnualPeakElectricityReduction',
                'type': 'value',
                'value': 'text'
            },
            'annual_natural_gas_energy': {
                'xpath': './auc:ResourceUses/auc:ResourceUse[auc:EnergyResource="Natural gas"]/auc:AnnualFuelUseConsistentUnits',
                'type': 'value',
                'value': 'text'
            },
            'is_virtual': {
                'xpath': './auc:ScenarioType/auc:PackageOfMeasures/auc:CalculationMethod/auc:Modeled',
                'type': 'value',
                'value': 'exist'
            },
            'measure_ids': {
                'xpath': './auc:ScenarioType/auc:PackageOfMeasures/auc:MeasureIDs/auc:MeasureID',
                'type': 'list',
                'items': {
                    'id': {
                        'xpath': '.',
                        'type': 'value',
                        'value': '@IDref'
                    }
                }
            },
            'resource_uses': {
                'xpath': './auc:ResourceUses/auc:ResourceUse',
                'type': 'list',
                'items': {
                    'source_id': {
                        'xpath': '.',
                        'type': 'value',
                        'value': '@ID',
                    },
                    'type': {
                        'xpath': './auc:EnergyResource',
                        'type': 'value',
                        'value': 'text',
                        'formatter': to_energy_type
                    },
                    'units': {
                        'xpath': './auc:ResourceUnits',
                        'type': 'value',
                        'value': 'text',
                        'formatter': to_energy_units
                    }
                }
            },
            'time_series': {
                'xpath': './auc:TimeSeriesData/auc:TimeSeries',
                'type': 'list',
                'items': {
                    'id': {
                        'xpath': '.',
                        'type': 'value',
                        'value': '@ID',
                    },
                    'start_time': {
                        'xpath': './auc:StartTimestamp',
                        'type': 'value',
                        'value': 'text',
                        'formatter': to_datetime
                    },
                    'end_time': {
                        'xpath': './auc:EndTimestamp',
                        'type': 'value',
                        'value': 'text',
                        'formatter': to_datetime
                    },
                    'reading': {
                        'xpath': './auc:IntervalReading',
                        'type': 'value',
                        'value': 'text'
                    },
                    'source_id': {
                        'xpath': './auc:ResourceUseID',
                        'type': 'value',
                        'value': '@IDref'
                    }
                }
            },
            # Audit Template stores some meter readings in AllResourceTotals...
            'audit_template_all_resource_totals': {
                'xpath': './auc:AllResourceTotals/auc:AllResourceTotal[auc:UserDefinedFields/auc:UserDefinedField/auc:FieldName="Linked Time Series ID"]',
                'type': 'list',
                'items': {
                    'linked_time_series_id': {
                        'xpath': './auc:UserDefinedFields/auc:UserDefinedField[auc:FieldName="Linked Time Series ID"]/auc:FieldValue',
                        'type': 'value',
                        'value': 'text',
                    },
                    'site_energy_use': {
                        'xpath': './auc:SiteEnergyUse',
                        'type': 'value',
                        'value': 'text',
                        'formatter': to_float,
                    }
                }
            }
        }
    }
}

from lxml import etree
from lxml.builder import ElementMaker

from seed.analysis_pipelines.pipeline import AnalysisPipelineException
from seed.building_sync.mappings import BUILDINGSYNC_URI, NAMESPACES
from seed.models import Meter

from quantityfield.units import ureg


# PREMISES_ID_NAME is the name of the custom ID used within a BuildingSync document
# to link it to SEED's AnalysisPropertyViews
PREMISES_ID_NAME = 'seed_analysis_property_view_id'

# BETTER and ESPM use different names for property types than BEDES and BSync
BETTER_TO_BSYNC_PROPERTY_TYPE = {
    'Office': 'Office',
    'Hotel': 'Lodging',
    'K-12 School': 'Education',
    'Hospital (General Medical & Surgical)': 'Health care-Inpatient hospital',
    'Bank Branch': 'Bank',
    'Courthouse': 'Courthouse',
    'Data Center': 'Data Center',
    'Distribution Center': 'Distribution Center',
    'Financial Office': 'Office-Financial',
    'Multifamily Housing': 'Multifamily',
    'Non-Refrigerated Warehouse': 'Warehouse unrefrigerated',
    'Refrigerated Warehouse': 'Warehouse refrigerated',
    'Retail Store': 'Retail',
    'Senior Care Community': 'Health care-Skilled nursing facility',
    'Supermarket/Grocery Store': 'Food sales-Grocery store',
    'Other': 'Other'
}

# maps SEED Meter types to BuildignSync ResourceUse types
# NOTE: this is semi-redundant with to_energy_type dict in building_sync/mappings.py
SEED_TO_BSYNC_RESOURCE_TYPE = {
    Meter.ELECTRICITY_GRID: 'Electricity',
    Meter.NATURAL_GAS: 'Natural gas',
    Meter.DIESEL: 'Diesel',
    Meter.PROPANE: 'Propane',
    Meter.COAL_ANTHRACITE: 'Coal anthracite',
    Meter.COAL_BITUMINOUS: 'Coal bituminous',
    Meter.COKE: 'Coke',
    Meter.FUEL_OIL_NO_1: 'Fuel oil no 1',
    Meter.FUEL_OIL_NO_2: 'Fuel oil no 2',
    Meter.FUEL_OIL_NO_4: 'Fuel oil no 4',
    Meter.FUEL_OIL_NO_5_AND_NO_6: 'Fuel oil no 5 and no 6',
    Meter.DISTRICT_STEAM: 'District steam',
    Meter.DISTRICT_HOT_WATER: 'District hot water',
    Meter.DISTRICT_CHILLED_WATER_ELECTRIC: 'District chilled water',
    Meter.KEROSENE: 'Kerosene',
    Meter.WOOD: 'Wood'
}


def _build_better_input(analysis_property_view, meters):
    """Constructs a BuildingSync document to be used as input for a BETTER analysis.
    The function returns a tuple, the first value being the XML document as a byte
    string. The second value is a list of error messages.

    :param analysis_property_view: AnalysisPropertyView
    :param meter: Meter
    :returns: tuple(bytes, list[str])
    """
    errors = []
    property_state = analysis_property_view.property_state

    if property_state.property_name is None:
        errors.append("BETTER analysis requires the property's name.")
    if property_state.city is None:
        errors.append("BETTER analysis requires the property's city.")
    if property_state.state is None:
        errors.append("BETTER analysis requires the property's state.")
    if property_state.gross_floor_area is None:
        errors.append("BETTER analysis requires the property's gross floor area.")
    if property_state.property_type is None:
        errors.append("BETTER analysis requires the property's type (office, retail, etc).")
    if property_state.property_type not in BETTER_TO_BSYNC_PROPERTY_TYPE:
        errors.append(
            f"BETTER analysis requires the property's type must be one of the following: {', '.join(BETTER_TO_BSYNC_PROPERTY_TYPE.keys())}")

    valid_meters_and_readings = []
    for meter in meters:
        readings = meter.meter_readings.filter(reading__gte=1.0).order_by('start_time')
        if readings.count() >= 12:
            valid_meters_and_readings.append({
                'meter': meter,
                'readings': readings,
            })
    if len(valid_meters_and_readings) == 0:
        errors.append(
            'BETTER analysis requires at least one meter with 12 consecutive readings with values >= 1.0'
        )

    if errors:
        return None, errors

    # clean inputs
    # BETTER will default if eGRIDRegion is not explicitly set
    try:
        eGRIDRegion = property_state.extra_data['eGRIDRegion']
    except KeyError:
        eGRIDRegion = ""

    property_type = BETTER_TO_BSYNC_PROPERTY_TYPE[property_state.property_type]

    gfa = property_state.gross_floor_area
    if gfa.units != ureg.feet**2:
        gross_floor_area = str(gfa.to(ureg.feet ** 2).magnitude)
    else:
        gross_floor_area = str(gfa.magnitude)

    XSI_URI = 'http://www.w3.org/2001/XMLSchema-instance'
    nsmap = {
        'xsi': XSI_URI,
    }
    nsmap.update(NAMESPACES)
    E = ElementMaker(
        namespace=BUILDINGSYNC_URI,
        nsmap=nsmap
    )

    doc = (
        E.BuildingSync(
            {
                etree.QName(XSI_URI,
                            'schemaLocation'): 'http://buildingsync.net/schemas/bedes-auc/2019 https://raw.github.com/BuildingSync/schema/v2.3.0/BuildingSync.xsd',
                'version': '2.3.0'
            },
            E.Facilities(
                E.Facility(
                    {'ID': 'Facility-1'},
                    E.Sites(
                        E.Site(
                            {'ID': 'Site-1'},
                            E.Buildings(
                                E.Building(
                                    {'ID': 'Building-1'},
                                    E.PremisesName(property_state.property_name),
                                    E.PremisesIdentifiers(
                                        E.PremisesIdentifier(
                                            E.IdentifierLabel('Custom'),
                                            E.IdentifierCustomName(PREMISES_ID_NAME),
                                            E.IdentifierValue(str(analysis_property_view.id)),
                                        )
                                    ),
                                    E.Address(
                                        E.City(property_state.city),
                                        E.State(property_state.state),
                                        E.PostalCode(property_state.postal_code)
                                    ),
                                    E.eGRIDRegionCode(eGRIDRegion),
                                    E.Longitude(str(analysis_property_view.property_state.longitude)),
                                    E.Latitude(str(analysis_property_view.property_state.latitude)),
                                    E.OccupancyClassification(property_type),
                                    E.FloorAreas(
                                        E.FloorArea(
                                            E.FloorAreaType("Gross"),
                                            E.FloorAreaValue(gross_floor_area)
                                        )
                                    ),
                                )
                            )
                        )
                    ),
                    E.Reports(
                        E.Report(
                            {'ID': 'Report-1'},
                            E.Scenarios(
                                E.Scenario(
                                    {'ID': 'Scenario-Measured'},
                                    E.ScenarioType(
                                        E.CurrentBuilding(
                                            E.CalculationMethod(
                                                E.Measured()
                                            )
                                        )
                                    ),
                                    E.ResourceUses(
                                        *[
                                            E.ResourceUse(
                                                {'ID': f'ResourceUse-{meter_idx:03}'},
                                                E.EnergyResource(SEED_TO_BSYNC_RESOURCE_TYPE[meter_and_readings['meter'].type]),
                                                # SEED stores all meter readings as kBtu
                                                E.ResourceUnits('kBtu'),
                                                E.EndUse('All end uses')
                                            )
                                            for meter_idx, meter_and_readings in enumerate(valid_meters_and_readings)
                                        ]
                                    ),
                                    E.TimeSeriesData(
                                        *[
                                            E.TimeSeries(
                                                {'ID': f'TimeSeries-{meter_idx:03}-{reading_idx:03}'},
                                                E.ReadingType('Total'),
                                                E.StartTimestamp(reading.start_time.isoformat()),
                                                E.EndTimestamp(reading.end_time.isoformat()),
                                                E.IntervalFrequency('Month'),
                                                E.IntervalReading(str(reading.reading)),
                                                E.ResourceUseID({'IDref': f'ResourceUse-{meter_idx:03}'}),
                                            )
                                            for meter_idx, meter_and_readings in enumerate(valid_meters_and_readings) \
                                            for reading_idx, reading in enumerate(meter_and_readings['readings'])
                                        ]
                                    ),
                                    E.LinkedPremises(
                                        E.Building(
                                            E.LinkedBuildingID({'IDref': 'Building-1'})
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
    )
    return etree.tostring(doc, pretty_print=True), []


def _parse_analysis_property_view_id(filepath):
    input_file_tree = etree.parse(filepath)
    id_xpath = f'//auc:PremisesIdentifier[auc:IdentifierCustomName = "{PREMISES_ID_NAME}"]/auc:IdentifierValue'
    analysis_property_view_id_elem = input_file_tree.xpath(id_xpath, namespaces=NAMESPACES)

    if len(analysis_property_view_id_elem) != 1:
        raise AnalysisPipelineException(
            f'Expected BuildlingSync file to have exactly one "{PREMISES_ID_NAME}" PremisesIdentifier')
    return int(analysis_property_view_id_elem[0].text)

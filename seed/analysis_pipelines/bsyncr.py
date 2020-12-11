# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from seed.models import Analysis, AnalysisPropertyView, AnalysisInputFile, Meter
from seed.analysis_pipelines.pipeline import AnalysisPipeline, task_create_analysis_property_views
from seed.lib.mcm.utils import batch
from seed.building_sync.mappings import BUILDINGSYNC_URI, NAMESPACES

from celery import shared_task, chain, group
from lxml import etree
from lxml.builder import ElementMaker


# PREMISES_ID_NAME is the name of the custom ID used within a BuildingSync document
# to link it to SEED's AnalysisPropertyViews
PREMISES_ID_NAME = 'seed_analysis_property_view_id'


def _build_bsyncr_input(analysis_property_view, meter):
    """Constructs a BuildingSync document to be used as input for a bsyncr analysis.
    The function returns a tuple, the first value being the XML document as a byte
    string. The second value is a list of error messages.

    :param analysis_property_view: AnalysisPropertyView
    :param meter: Meter
    :returns: tuple(bytes, list[str])
    """
    errors = []
    property_state = analysis_property_view.property_state
    if property_state.longitude is None:
        errors.append('Linked PropertyState is missing longitude')
    if property_state.latitude is None:
        errors.append('Linked PropertyState is missing latitude')
    for meter_reading in meter.meter_readings.all():
        if meter_reading.reading is None:
            errors.append(f'MeterReading starting at {meter_reading.start_time} has no reading value')
    if errors:
        return None, errors

    XSI_URI = 'http://www.w3.org/2001/XMLSchema-instance'
    nsmap = {
        'xsi': XSI_URI,
    }
    nsmap.update(NAMESPACES)
    E = ElementMaker(
        namespace=BUILDINGSYNC_URI,
        nsmap=nsmap
    )

    elec_resource_id = 'Resource-Elec'
    doc = (
        E.BuildingSync(
            {
                etree.QName(XSI_URI, 'schemaLocation'): 'http://buildingsync.net/schemas/bedes-auc/2019 https://raw.github.com/BuildingSync/schema/v2.2.0/BuildingSync.xsd',
                'version': '2.2.0'
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
                                    E.PremisesName('My-Building'),
                                    E.PremisesIdentifiers(
                                        E.PremisesIdentifier(
                                            E.IdentifierLabel('Custom'),
                                            E.IdentifierCustomName(PREMISES_ID_NAME),
                                            E.IdentifierValue(str(analysis_property_view.id)),
                                        )
                                    ),
                                    E.Longitude(str(analysis_property_view.property_state.longitude)),
                                    E.Latitude(str(analysis_property_view.property_state.latitude)),
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
                                        E.ResourceUse(
                                            {'ID': elec_resource_id},
                                            E.EnergyResource('Electricity'),
                                            E.ResourceUnits('kWh'),
                                            E.EndUse('All end uses')
                                        )
                                    ),
                                    E.TimeSeriesData(
                                        *[
                                            E.TimeSeries(
                                                {'ID': f'TimeSeries-{i}'},
                                                E.StartTimestamp(reading.start_time.isoformat()),
                                                E.IntervalFrequency('Month'),
                                                E.IntervalReading(str(reading.reading)),
                                                E.ResourceUseID({'IDref': elec_resource_id}),
                                            )
                                            for i, reading in enumerate(meter.meter_readings.all())
                                        ]
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

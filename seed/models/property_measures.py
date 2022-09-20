# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from __future__ import unicode_literals

import logging

from django.db import models

logger = logging.getLogger(__name__)


class PropertyMeasure(models.Model):
    """
    A PropertyMeasure is the join between a measure and a PropertyState with the added information
    to fully define a unique measure instance. Scenarios reference these PropertyMeasures to define
    list of measures for the PropertyState.
    """
    MEASURE_PROPOSED = 1
    MEASURE_EVALUATED = 2
    MEASURE_SELECTED = 3
    MEASURE_INITIATED = 4
    MEASURE_DISCARDED = 5
    MEASURE_IN_PROGRESS = 6
    MEASURE_COMPLETED = 7
    MEASURE_MV = 8
    MEASURE_VERIFIED = 9
    MEASURE_UNSATISFACTORY = 10

    IMPLEMENTATION_TYPES = (
        (MEASURE_PROPOSED, 'Proposed'),
        (MEASURE_EVALUATED, 'Evaluated'),
        (MEASURE_SELECTED, 'Selected'),
        (MEASURE_INITIATED, 'Initiated'),
        (MEASURE_DISCARDED, 'Discarded'),
        (MEASURE_IN_PROGRESS, 'In Progress'),
        (MEASURE_COMPLETED, 'Completed'),
        (MEASURE_MV, 'MV'),
        (MEASURE_VERIFIED, 'Verified'),
        (MEASURE_UNSATISFACTORY, 'Unsatisfactory'),
    )

    SCALE_INDIVIDUAL_SYSTEM = 1
    SCALE_MULTIPLE_SYSTEM = 2
    SCALE_INDIVIDUAL_PREMISE = 3
    SCALE_MULTIPLE_PREMISES = 4
    SCALE_ENTIRE_FACILITY = 5
    SCALE_ENTIRE_SITE = 6
    SCALE_ENTIRE_BUILDING = 7
    SCALE_COMMON_AREAS = 8
    SCALE_TENANT_AREAS = 9

    APPLICATION_SCALE_TYPES = (
        (SCALE_INDIVIDUAL_SYSTEM, 'Individual system'),
        (SCALE_MULTIPLE_SYSTEM, 'Multiple systems'),
        (SCALE_INDIVIDUAL_PREMISE, 'Individual premise'),
        (SCALE_MULTIPLE_PREMISES, 'Multiple premises'),
        (SCALE_ENTIRE_FACILITY, 'Entire facility'),
        (SCALE_ENTIRE_SITE, 'Entire site'),
        (SCALE_ENTIRE_BUILDING, 'Entire building'),
        (SCALE_COMMON_AREAS, 'Common areas'),
        (SCALE_TENANT_AREAS, 'Tenant areas'),
    )

    CATEGORY_AIR_DISTRIBUTION = 0
    CATEGORY_HEATING_SYSTEM = 1
    CATEGORY_COOLING_SYSTEM = 2
    CATEGORY_OTHER_HVAC = 3
    CATEGORY_LIGHTING = 4
    CATEGORY_DOMESTIC_HOT_WATER = 5
    CATEGORY_COOKING = 6
    CATEGORY_REFRIGERATION = 7
    CATEGORY_DISHWASHER = 8
    CATEGORY_LAUNDRY = 9
    CATEGORY_PUMP = 10
    CATEGORY_FAN = 11
    CATEGORY_MOTOR = 12
    CATEGORY_HEAT_RECOVERY = 13
    CATEGORY_WALL = 14
    CATEGORY_ROOF = 15
    CATEGORY_CEILING = 16
    CATEGORY_FENESTRATION = 17
    CATEGORY_FOUNDATION = 18
    CATEGORY_CONTROLS = 19
    CATEGORY_CRITICAL_IT_SYSTEM = 20
    CATEGORY_PLUG_LOAD = 21
    CATEGORY_PROCESS_LOAD = 22
    CATEGORY_CONVEYANCE = 23
    CATEGORY_ONSITE_STORAGE_GENERATION = 24
    CATEGORY_POOL = 25
    CATEGORY_WATER_USE = 26
    CATEGORY_OTHER = 27

    CATEGORY_AFFECTED_TYPE = (
        (CATEGORY_AIR_DISTRIBUTION, 'Air Distribution'),
        (CATEGORY_HEATING_SYSTEM, 'Heating System'),
        (CATEGORY_COOLING_SYSTEM, 'Cooling System'),
        (CATEGORY_OTHER_HVAC, 'Other HVAC'),
        (CATEGORY_LIGHTING, 'Lighting'),
        (CATEGORY_DOMESTIC_HOT_WATER, 'Domestic Hot Water'),
        (CATEGORY_COOKING, 'Cooking'),
        (CATEGORY_REFRIGERATION, 'Refrigeration'),
        (CATEGORY_DISHWASHER, 'Dishwasher'),
        (CATEGORY_LAUNDRY, 'Laundry'),
        (CATEGORY_PUMP, 'Pump'),
        (CATEGORY_FAN, 'Fan'),
        (CATEGORY_MOTOR, 'Motor'),
        (CATEGORY_HEAT_RECOVERY, 'Heat Recovery'),
        (CATEGORY_WALL, 'Wall'),
        (CATEGORY_ROOF, 'Roof'),
        (CATEGORY_CEILING, 'Ceiling'),
        (CATEGORY_FENESTRATION, 'Fenestration'),
        (CATEGORY_FOUNDATION, 'Foundation'),
        (CATEGORY_CONTROLS, 'General Controls and Operations'),
        (CATEGORY_CRITICAL_IT_SYSTEM, 'Critical IT System'),
        (CATEGORY_PLUG_LOAD, 'Plug Load'),
        (CATEGORY_PROCESS_LOAD, 'Process Load'),
        (CATEGORY_CONVEYANCE, 'Conveyance'),
        (CATEGORY_ONSITE_STORAGE_GENERATION, 'On-Site Storage, Transmission, Generation'),
        (CATEGORY_POOL, 'Pool'),
        (CATEGORY_WATER_USE, 'Water Use'),
        (CATEGORY_OTHER, 'Other'),
    )

    # pointer to the actual measure as defined by the list of BuildingSync measures
    measure = models.ForeignKey('Measure', on_delete=models.DO_NOTHING)

    # User defined name of the measure that is in the BuildingSync file, used for tracking measures
    # within properties. This is typically the IDref.
    property_measure_name = models.CharField(max_length=255, null=False)
    property_state = models.ForeignKey('PropertyState', on_delete=models.DO_NOTHING)
    description = models.TextField(null=True)
    implementation_status = models.IntegerField(choices=IMPLEMENTATION_TYPES, default=MEASURE_PROPOSED)
    application_scale = models.IntegerField(choices=APPLICATION_SCALE_TYPES, default=SCALE_ENTIRE_FACILITY)
    recommended = models.BooleanField(default=True)
    cost_mv = models.FloatField(null=True)
    cost_total_first = models.FloatField(null=True)
    cost_installation = models.FloatField(null=True)
    cost_material = models.FloatField(null=True)
    cost_capital_replacement = models.FloatField(null=True)
    cost_residual_value = models.FloatField(null=True)
    category_affected = models.IntegerField(choices=CATEGORY_AFFECTED_TYPE, default=CATEGORY_OTHER)
    useful_life = models.FloatField(null=True)

    class Meta:
        unique_together = ('property_measure_name', 'property_state', 'measure', 'application_scale', 'implementation_status')
        index_together = [
            ['property_measure_name', 'property_state'],
        ]

    @classmethod
    def str_to_impl_status(cls, impl_status):
        if not impl_status:
            return None

        if isinstance(impl_status, int):
            return impl_status

        value = [y[0] for x, y in enumerate(cls.IMPLEMENTATION_TYPES) if y[1] == impl_status]
        if len(value) == 1:
            return value[0]
        else:
            return None

    @classmethod
    def str_to_category_affected(cls, category):
        if not category:
            return None

        if isinstance(category, int):
            return category

        value = [y[0] for x, y in enumerate(cls.CATEGORY_AFFECTED_TYPE) if y[1] == category]
        if len(value) == 1:
            return value[0]
        else:
            return None

    @classmethod
    def str_to_application_scale(cls, app_scale):
        if not app_scale:
            return None

        if isinstance(app_scale, int):
            return app_scale

        value = [y[0] for x, y in enumerate(cls.APPLICATION_SCALE_TYPES) if y[1] == app_scale]
        if len(value) == 1:
            return value[0]
        else:
            return None

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
"""
Utility methods pertaining to data import tasks (save, mapping, matching).
"""
from collections import defaultdict

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone


def get_core_pk_column(table_column_mappings, primary_field):
    for tcm in table_column_mappings:
        if tcm.destination_field == primary_field:
            return tcm.order - 1
    raise ValidationError("This file does not appear to contain a column mapping to %s" % primary_field)


def acquire_lock(name, expiration=None):
    """
    Tries to acquire a lock from the cache.
    Also sets the lock's value to the current time, allowing us to see how long
    it has been held.

    Returns False if lock already belongs by another process.
    """
    return cache.add(name, timezone.now(), expiration)


def release_lock(name):
    """
    Frees a lock.
    """
    return cache.delete(name)


def get_lock_time(name):
    """
    Examines a lock to see when it was acquired.
    """
    return cache.get(name)


def chunk_iterable(iterlist, chunk_size):
    """
    Breaks an iterable (e.g. list) into smaller chunks,
    returning a generator of the chunk.
    """
    assert hasattr(iterlist, "__iter__"), "iter is not an iterable"
    for i in range(0, len(iterlist), chunk_size):
        yield iterlist[i:i + chunk_size]


def kbtu_thermal_conversion_factors(country):
    # Conversion factors taken from https://portfoliomanager.energystar.gov/pdf/reference/Thermal%20Conversions.pdf
    factors = defaultdict(lambda: {})

    if country == "US":
        factors["Electricity"]["kBtu"] = 1.00000000000
        factors["Electricity"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["Electricity"]["kWh"] = 3.41200000000
        factors["Electricity"]["MWh (million Watt-hours)"] = 3412.00000000000
        factors["Electricity"]["GJ"] = 947.81700000000
        factors["Natural Gas"]["kBtu"] = 1.00000000000
        factors["Natural Gas"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["Natural Gas"]["cf"] = 1.02600000000
        factors["Natural Gas"]["Ccf (hundred cubic feet)"] = 102.60000000000
        factors["Natural Gas"]["Kcf (thousand cubic feet)"] = 1026.00000000000
        factors["Natural Gas"]["Mcf (million cubic feet)"] = 1026000.00000000000
        factors["Natural Gas"]["Therms"] = 100.00000000000
        factors["Natural Gas"]["cubic meters"] = 36.30300000000
        factors["Natural Gas"]["GJ"] = 947.81700000000
        factors["Fuel Oil (No. 1)"]["kBtu"] = 1.00000000000
        factors["Fuel Oil (No. 1)"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["Fuel Oil (No. 1)"]["Gallons (US)"] = 139.00000000000
        factors["Fuel Oil (No. 1)"]["Gallons (UK)"] = 166.92700000000
        factors["Fuel Oil (No. 1)"]["liters"] = 36.72000000000
        factors["Fuel Oil (No. 1)"]["GJ"] = 947.81700000000
        factors["Fuel Oil (No. 2)"]["kBtu"] = 1.00000000000
        factors["Fuel Oil (No. 2)"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["Fuel Oil (No. 2)"]["Gallons (US)"] = 138.00000000000
        factors["Fuel Oil (No. 2)"]["Gallons (UK)"] = 165.72600000000
        factors["Fuel Oil (No. 2)"]["liters"] = 36.45600000000
        factors["Fuel Oil (No. 2)"]["GJ"] = 947.81700000000
        factors["Fuel Oil (No. 4)"]["kBtu"] = 1.00000000000
        factors["Fuel Oil (No. 4)"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["Fuel Oil (No. 4)"]["Gallons (US)"] = 146.00000000000
        factors["Fuel Oil (No. 4)"]["Gallons (UK)"] = 175.33300000000
        factors["Fuel Oil (No. 4)"]["liters"] = 38.56900000000
        factors["Fuel Oil (No. 4)"]["GJ"] = 947.81700000000
        factors["Fuel Oil (No. 5 & No. 6)"]["kBtu"] = 1.00000000000
        factors["Fuel Oil (No. 5 & No. 6)"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["Fuel Oil (No. 5 & No. 6)"]["Gallons (US)"] = 150.00000000000
        factors["Fuel Oil (No. 5 & No. 6)"]["Gallons (UK)"] = 180.13700000000
        factors["Fuel Oil (No. 5 & No. 6)"]["liters"] = 39.62600000000
        factors["Fuel Oil (No. 5 & No. 6)"]["GJ"] = 947.81700000000
        factors["Diesel"]["kBtu"] = 1.00000000000
        factors["Diesel"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["Diesel"]["Gallons (US)"] = 138.00000000000
        factors["Diesel"]["Gallons (UK)"] = 165.72600000000
        factors["Diesel"]["liters"] = 36.45600000000
        factors["Diesel"]["GJ"] = 947.81700000000
        factors["Kerosene"]["kBtu"] = 1.00000000000
        factors["Kerosene"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["Kerosene"]["Gallons (US)"] = 135.00000000000
        factors["Kerosene"]["Gallons (UK)"] = 162.12300000000
        factors["Kerosene"]["liters"] = 35.66300000000
        factors["Kerosene"]["GJ"] = 947.81700000000
        factors["Propane"]["kBtu"] = 1.00000000000
        factors["Propane"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["Propane"]["cf"] = 2.51600000000
        factors["Propane"]["Ccf (hundred cubic feet)"] = 251.60000000000
        factors["Propane"]["Kcf (thousand cubic feet)"] = 2516.00000000000
        factors["Propane"]["Gallons (US)"] = 92.00000000000
        factors["Propane"]["Gallons (UK)"] = 110.48400000000
        factors["Propane"]["liters"] = 24.30400000000
        factors["Propane"]["GJ"] = 947.81700000000
        factors["District Steam"]["kBtu"] = 1.00000000000
        factors["District Steam"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["District Steam"]["Lbs"] = 1.19400000000
        factors["District Steam"]["kLbs (thousand pounds)"] = 1194.00000000000
        factors["District Steam"]["MLbs (million pounds)"] = 1194000.00000000000
        factors["District Steam"]["therms"] = 100.00000000000
        factors["District Steam"]["GJ"] = 947.81700000000
        factors["District Steam"]["kg"] = 2.63200000000
        factors["District Hot Water"]["kBtu"] = 1.00000000000
        factors["District Hot Water"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["District Hot Water"]["Therms"] = 100.00000000000
        factors["District Hot Water"]["GJ"] = 947.81700000000
        factors["District Chilled Water"]["kBtu"] = 1.00000000000
        factors["District Chilled Water"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["District Chilled Water"]["Ton Hours"] = 12.00000000000
        factors["District Chilled Water"]["GJ"] = 947.81700000000
        factors["Coal (anthracite)"]["kBtu"] = 1.00000000000
        factors["Coal (anthracite)"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["Coal (anthracite)"]["Tons"] = 25090.00000000000
        factors["Coal (anthracite)"]["Lbs"] = 12.54500000000
        factors["Coal (anthracite)"]["kLbs (thousand pounds)"] = 12545.00000000000
        factors["Coal (anthracite)"]["MLbs (million pounds)"] = 12545000.00000000000
        factors["Coal (anthracite)"]["Tonnes (metric)"] = 27658.35500000000
        factors["Coal (anthracite)"]["GJ"] = 947.81700000000
        factors["Coal (bituminous)"]["kBtu"] = 1.00000000000
        factors["Coal (bituminous)"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["Coal (bituminous)"]["Tons"] = 24930.00000000000
        factors["Coal (bituminous)"]["Lbs"] = 12.46500000000
        factors["Coal (bituminous)"]["kLbs (thousand pounds)"] = 12465.00000000000
        factors["Coal (bituminous)"]["MLbs (million pounds)"] = 12465000.00000000000
        factors["Coal (bituminous)"]["Tonnes (metric)"] = 27482.00000000000
        factors["Coal (bituminous)"]["GJ"] = 947.81700000000
        factors["Coke"]["kBtu"] = 1.00000000000
        factors["Coke"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["Coke"]["Tons"] = 24800.00000000000
        factors["Coke"]["Lbs"] = 12.40000000000
        factors["Coke"]["kLbs (thousand pounds)"] = 12400.00000000000
        factors["Coke"]["MLbs (million pounds)"] = 12400000.00000000000
        factors["Coke"]["Tonnes (metric)"] = 27339.00000000000
        factors["Coke"]["GJ"] = 947.81700000000
        factors["Wood"]["kBtu"] = 1.00000000000
        factors["Wood"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
        factors["Wood"]["Tons"] = 17480.00000000000
        factors["Wood"]["Tonnes (metric)"] = 15857.00000000000
        factors["Wood"]["GJ"] = 947.81700000000
        factors["Other"]["kBtu"] = 1.00000000000
    # elif country == "CAN": finish once these numbers are confirmed

    return factors


class CoercionRobot(object):

    def __init__(self):
        self.values_hash = {}

    def lookup_hash(self, uncoerced_value, destination_model, destination_field):
        key = self.make_key(uncoerced_value, destination_model, destination_field)
        if key in self.values_hash:
            return self.values_hash[key]
        return None

    def make_key(self, value, model, field):
        return "%s|%s|%s" % (value, model, field)

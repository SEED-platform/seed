"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

Utility methods pertaining to data import tasks (save, mapping, matching).
"""

from collections import defaultdict


def kbtu_thermal_conversion_factors(country):
    """
    Returns thermal conversion factors provided by Portfolio Manager.
    In the PM app, using NREL's test account, a property was created for each US
    and CAN. All possible Meters of different Type and Units were added.
    Readings of value 1 were added to deduce the factors provided below.

    Consideration was given regarding having the provided 'country' value align with
    Organizations' thermal_conversion_assumption enums. Even though these two
    should be aligned, the concept and need for these factors are not specific
    solely to Orgs. So the 'country' value here is expected to be a string.
    Specifically, there are instances in the codebase where the factors are
    needed irrespective of any Organization's preferences.
    """

    factors = defaultdict(dict)

    if country == "US":
        factors["Coal (anthracite)"]["GJ"] = 947.82
        factors["Coal (anthracite)"]["Btu"] = 0.001
        factors["Coal (anthracite)"]["kBtu (thousand Btu)"] = 1.00
        factors["Coal (anthracite)"]["kLbs. (thousand pounds)"] = 12545.00
        factors["Coal (anthracite)"]["Lbs. (pounds)"] = 12.55
        factors["Coal (anthracite)"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Coal (anthracite)"]["MLbs. (million pounds)"] = 12545001.00
        factors["Coal (anthracite)"]["Tonnes (metric)"] = 27658.36
        factors["Coal (anthracite)"]["Tons"] = 25090.00
        factors["Coal (bituminous)"]["GJ"] = 947.82
        factors["Coal (bituminous)"]["Btu"] = 0.001
        factors["Coal (bituminous)"]["kBtu (thousand Btu)"] = 1.00
        factors["Coal (bituminous)"]["kLbs. (thousand pounds)"] = 12465.00
        factors["Coal (bituminous)"]["Lbs. (pounds)"] = 12.46
        factors["Coal (bituminous)"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Coal (bituminous)"]["MLbs. (million pounds)"] = 12465000.00
        factors["Coal (bituminous)"]["Tonnes (metric)"] = 27481.98
        factors["Coal (bituminous)"]["Tons"] = 24930.00
        factors["Coke"]["GJ"] = 947.82
        factors["Coke"]["Btu"] = 0.001
        factors["Coke"]["kBtu (thousand Btu)"] = 1.00
        factors["Coke"]["kLbs. (thousand pounds)"] = 12400.00
        factors["Coke"]["Lbs. (pounds)"] = 12.40
        factors["Coke"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Coke"]["MLbs. (million pounds)"] = 12399999.00
        factors["Coke"]["Tonnes (metric)"] = 27338.67
        factors["Coke"]["Tons"] = 24800.00
        factors["Default"]["GJ"] = 947.82
        factors["Default"]["Btu"] = 0.001
        factors["Default"]["kBtu (thousand Btu)"] = 1.00
        factors["Default"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Default"]["ton hours"] = 12.00
        factors["Diesel"]["Gallons (UK)"] = 165.73
        factors["Diesel"]["Gallons (US)"] = 138.00
        factors["Diesel"]["GJ"] = 947.82
        factors["Diesel"]["Btu"] = 0.001
        factors["Diesel"]["kBtu (thousand Btu)"] = 1.00
        factors["Diesel"]["Liters"] = 36.46
        factors["Diesel"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Chilled Water"]["GJ"] = 947.82
        factors["District Chilled Water"]["Btu"] = 0.001
        factors["District Chilled Water"]["kBtu (thousand Btu)"] = 1.00
        factors["District Chilled Water"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Chilled Water"]["ton hours"] = 12.00
        factors["District Chilled Water - Absorption"]["GJ"] = 947.82
        factors["District Chilled Water - Absorption"]["Btu"] = 0.001
        factors["District Chilled Water - Absorption"]["kBtu (thousand Btu)"] = 1.00
        factors["District Chilled Water - Absorption"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Chilled Water - Absorption"]["ton hours"] = 12.00
        factors["District Chilled Water - Electric"]["GJ"] = 947.82
        factors["District Chilled Water - Electric"]["Btu"] = 0.001
        factors["District Chilled Water - Electric"]["kBtu (thousand Btu)"] = 1.00
        factors["District Chilled Water - Electric"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Chilled Water - Electric"]["ton hours"] = 12.00
        factors["District Chilled Water - Engine"]["GJ"] = 947.82
        factors["District Chilled Water - Engine"]["Btu"] = 0.001
        factors["District Chilled Water - Engine"]["kBtu (thousand Btu)"] = 1.00
        factors["District Chilled Water - Engine"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Chilled Water - Engine"]["ton hours"] = 12.00
        factors["District Chilled Water - Other"]["GJ"] = 947.82
        factors["District Chilled Water - Other"]["Btu"] = 0.001
        factors["District Chilled Water - Other"]["kBtu (thousand Btu)"] = 1.00
        factors["District Chilled Water - Other"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Chilled Water - Other"]["ton hours"] = 12.00
        factors["District Hot Water"]["GJ"] = 947.82
        factors["District Hot Water"]["Btu"] = 0.001
        factors["District Hot Water"]["kBtu (thousand Btu)"] = 1.00
        factors["District Hot Water"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Hot Water"]["therms"] = 100.00
        factors["District Steam"]["GJ"] = 947.82
        factors["District Steam"]["Btu"] = 0.001
        factors["District Steam"]["kBtu (thousand Btu)"] = 1.00
        factors["District Steam"]["kg (kilograms)"] = 2.63
        factors["District Steam"]["kLbs. (thousand pounds)"] = 1194.00
        factors["District Steam"]["Lbs. (pounds)"] = 1.19
        factors["District Steam"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Steam"]["MLbs. (million pounds)"] = 1194000.00
        factors["District Steam"]["therms"] = 100.00
        factors["Electric"]["GJ"] = 947.82
        factors["Electric"]["Btu"] = 0.001
        factors["Electric"]["kBtu (thousand Btu)"] = 1.00
        factors["Electric"]["Wh (Watt-hours)"] = 0.00341
        factors["Electric"]["kWh (thousand Watt-hours)"] = 3.41
        factors["Electric"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Electric"]["MWh (million Watt-hours)"] = 3412.00
        factors["Electric - Grid"]["GJ"] = 947.82
        factors["Electric - Grid"]["Btu"] = 0.001
        factors["Electric - Grid"]["kBtu (thousand Btu)"] = 1.00
        factors["Electric - Grid"]["Wh (Watt-hours)"] = 0.00341
        factors["Electric - Grid"]["kWh (thousand Watt-hours)"] = 3.41
        factors["Electric - Grid"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Electric - Grid"]["MWh (million Watt-hours)"] = 3412.00
        factors["Electric - Solar"]["GJ"] = 947.82
        factors["Electric - Solar"]["Btu"] = 0.001
        factors["Electric - Solar"]["kBtu (thousand Btu)"] = 1.00
        factors["Electric - Solar"]["Wh (Watt-hours)"] = 0.00341
        factors["Electric - Solar"]["kWh (thousand Watt-hours)"] = 3.41
        factors["Electric - Solar"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Electric - Solar"]["MWh (million Watt-hours)"] = 3412.00
        factors["Electric - Wind"]["GJ"] = 947.82
        factors["Electric - Wind"]["Btu"] = 0.001
        factors["Electric - Wind"]["kBtu (thousand Btu)"] = 1.00
        factors["Electric - Wind"]["Wh (Watt-hours)"] = 0.00341
        factors["Electric - Wind"]["kWh (thousand Watt-hours)"] = 3.41
        factors["Electric - Wind"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Electric - Wind"]["MWh (million Watt-hours)"] = 3412.00
        factors["Electric - Unknown"]["GJ"] = 947.82
        factors["Electric - Unknown"]["Btu"] = 0.001
        factors["Electric - Unknown"]["kBtu (thousand Btu)"] = 1.00
        factors["Electric - Unknown"]["Wh (Watt-hours)"] = 0.00341
        factors["Electric - Unknown"]["kWh (thousand Watt-hours)"] = 3.41
        factors["Electric - Unknown"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Electric - Unknown"]["MWh (million Watt-hours)"] = 3412.00
        factors["Fuel Oil (No. 1)"]["Gallons (UK)"] = 166.93
        factors["Fuel Oil (No. 1)"]["Gallons (US)"] = 139.00
        factors["Fuel Oil (No. 1)"]["GJ"] = 947.82
        factors["Fuel Oil (No. 1)"]["Btu"] = 0.001
        factors["Fuel Oil (No. 1)"]["kBtu (thousand Btu)"] = 1.00
        factors["Fuel Oil (No. 1)"]["Liters"] = 36.72
        factors["Fuel Oil (No. 1)"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Fuel Oil (No. 2)"]["Gallons (UK)"] = 165.73
        factors["Fuel Oil (No. 2)"]["Gallons (US)"] = 138.00
        factors["Fuel Oil (No. 2)"]["GJ"] = 947.82
        factors["Fuel Oil (No. 2)"]["Btu"] = 0.001
        factors["Fuel Oil (No. 2)"]["kBtu (thousand Btu)"] = 1.00
        factors["Fuel Oil (No. 2)"]["Liters"] = 36.46
        factors["Fuel Oil (No. 2)"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Fuel Oil (No. 4)"]["Gallons (UK)"] = 175.33
        factors["Fuel Oil (No. 4)"]["Gallons (US)"] = 146.00
        factors["Fuel Oil (No. 4)"]["GJ"] = 947.82
        factors["Fuel Oil (No. 4)"]["Btu"] = 0.001
        factors["Fuel Oil (No. 4)"]["kBtu (thousand Btu)"] = 1.00
        factors["Fuel Oil (No. 4)"]["Liters"] = 38.57
        factors["Fuel Oil (No. 4)"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Fuel Oil (No. 5 and No. 6)"]["Gallons (UK)"] = 180.14
        factors["Fuel Oil (No. 5 and No. 6)"]["Gallons (US)"] = 150.00
        factors["Fuel Oil (No. 5 and No. 6)"]["GJ"] = 947.82
        factors["Fuel Oil (No. 5 and No. 6)"]["Btu"] = 0.001
        factors["Fuel Oil (No. 5 and No. 6)"]["kBtu (thousand Btu)"] = 1.00
        factors["Fuel Oil (No. 5 and No. 6)"]["Liters"] = 39.63
        factors["Fuel Oil (No. 5 and No. 6)"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Kerosene"]["Gallons (UK)"] = 162.12
        factors["Kerosene"]["Gallons (US)"] = 135.00
        factors["Kerosene"]["GJ"] = 947.82
        factors["Kerosene"]["Btu"] = 0.001
        factors["Kerosene"]["kBtu (thousand Btu)"] = 1.00
        factors["Kerosene"]["Liters"] = 35.66
        factors["Kerosene"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Natural Gas"]["ccf (hundred cubic feet)"] = 102.60
        factors["Natural Gas"]["cf (cubic feet)"] = 1.03
        factors["Natural Gas"]["cm (cubic meters)"] = 36.30
        factors["Natural Gas"]["GJ"] = 947.82
        factors["Natural Gas"]["Btu"] = 0.001
        factors["Natural Gas"]["kBtu (thousand Btu)"] = 1.00
        factors["Natural Gas"]["kcf (thousand cubic feet)"] = 1026.00
        factors["Natural Gas"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Natural Gas"]["Mcf (million cubic feet)"] = 1026000.00
        factors["Natural Gas"]["therms"] = 100.00
        factors["Other:"]["GJ"] = 947.82
        factors["Other:"]["Btu"] = 0.001
        factors["Other:"]["kBtu (thousand Btu)"] = 1.00
        factors["Propane"]["ccf (hundred cubic feet)"] = 251.60
        factors["Propane"]["cf (cubic feet)"] = 2.52
        factors["Propane"]["Gallons (UK)"] = 110.48
        factors["Propane"]["Gallons (US)"] = 92.00
        factors["Propane"]["GJ"] = 947.82
        factors["Propane"]["Btu"] = 0.001
        factors["Propane"]["kBtu (thousand Btu)"] = 1.00
        factors["Propane"]["kcf (thousand cubic feet)"] = 2516.00
        factors["Propane"]["Liters"] = 24.30
        factors["Propane"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Wood"]["GJ"] = 947.82
        factors["Wood"]["Btu"] = 0.001
        factors["Wood"]["kBtu (thousand Btu)"] = 1.00
        factors["Wood"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Wood"]["Tonnes (metric)"] = 15857.50
        factors["Wood"]["Tons"] = 17480.00
    elif country == "CAN":
        factors["Coal (anthracite)"]["GJ"] = 947.82
        factors["Coal (anthracite)"]["Btu"] = 0.001
        factors["Coal (anthracite)"]["kBtu (thousand Btu)"] = 1.00
        factors["Coal (anthracite)"]["kLbs. (thousand pounds)"] = 11909.06
        factors["Coal (anthracite)"]["Lbs. (pounds)"] = 11.91
        factors["Coal (anthracite)"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Coal (anthracite)"]["MLbs. (million pounds)"] = 11909055.00
        factors["Coal (anthracite)"]["Tonnes (metric)"] = 26254.53
        factors["Coal (anthracite)"]["Tons"] = 23818.11
        factors["Coal (bituminous)"]["GJ"] = 947.82
        factors["Coal (bituminous)"]["Btu"] = 0.001
        factors["Coal (bituminous)"]["kBtu (thousand Btu)"] = 1.00
        factors["Coal (bituminous)"]["kLbs. (thousand pounds)"] = 10748.25
        factors["Coal (bituminous)"]["Lbs. (pounds)"] = 10.75
        factors["Coal (bituminous)"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Coal (bituminous)"]["MLbs. (million pounds)"] = 10748244.00
        factors["Coal (bituminous)"]["Tonnes (metric)"] = 23695.42
        factors["Coal (bituminous)"]["Tons"] = 21496.49
        factors["Coke"]["GJ"] = 947.82
        factors["Coke"]["Btu"] = 0.001
        factors["Coke"]["kBtu (thousand Btu)"] = 1.00
        factors["Coke"]["kLbs. (thousand pounds)"] = 12394.88
        factors["Coke"]["Lbs. (pounds)"] = 12.39
        factors["Coke"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Coke"]["MLbs. (million pounds)"] = 12394875.00
        factors["Coke"]["Tonnes (metric)"] = 27325.56
        factors["Coke"]["Tons"] = 24789.75
        factors["Default"]["GJ"] = 947.82
        factors["Default"]["Btu"] = 0.001
        factors["Default"]["kBtu (thousand Btu)"] = 1.00
        factors["Default"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Default"]["ton hours"] = 12.00
        factors["Diesel"]["Gallons (UK)"] = 165.03
        factors["Diesel"]["Gallons (US)"] = 137.42
        factors["Diesel"]["GJ"] = 947.82
        factors["Diesel"]["Btu"] = 0.001
        factors["Diesel"]["kBtu (thousand Btu)"] = 1.00
        factors["Diesel"]["Liters"] = 36.30
        factors["Diesel"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Chilled Water"]["GJ"] = 947.82
        factors["District Chilled Water"]["Btu"] = 0.001
        factors["District Chilled Water"]["kBtu (thousand Btu)"] = 1.00
        factors["District Chilled Water"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Chilled Water"]["ton hours"] = 12.00
        factors["District Chilled Water - Absorption"]["GJ"] = 947.82
        factors["District Chilled Water - Absorption"]["Btu"] = 0.001
        factors["District Chilled Water - Absorption"]["kBtu (thousand Btu)"] = 1.00
        factors["District Chilled Water - Absorption"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Chilled Water - Absorption"]["ton hours"] = 12.00
        factors["District Chilled Water - Electric"]["GJ"] = 947.82
        factors["District Chilled Water - Electric"]["Btu"] = 0.001
        factors["District Chilled Water - Electric"]["kBtu (thousand Btu)"] = 1.00
        factors["District Chilled Water - Electric"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Chilled Water - Electric"]["ton hours"] = 12.00
        factors["District Chilled Water - Engine"]["GJ"] = 947.82
        factors["District Chilled Water - Engine"]["Btu"] = 0.001
        factors["District Chilled Water - Engine"]["kBtu (thousand Btu)"] = 1.00
        factors["District Chilled Water - Engine"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Chilled Water - Engine"]["ton hours"] = 12.00
        factors["District Chilled Water - Other"]["GJ"] = 947.82
        factors["District Chilled Water - Other"]["Btu"] = 0.001
        factors["District Chilled Water - Other"]["kBtu (thousand Btu)"] = 1.00
        factors["District Chilled Water - Other"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Chilled Water - Other"]["ton hours"] = 12.00
        factors["District Hot Water"]["GJ"] = 947.82
        factors["District Hot Water"]["Btu"] = 0.001
        factors["District Hot Water"]["kBtu (thousand Btu)"] = 1.00
        factors["District Hot Water"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Hot Water"]["therms"] = 100.00
        factors["District Steam"]["GJ"] = 947.82
        factors["District Steam"]["Btu"] = 0.001
        factors["District Steam"]["kBtu (thousand Btu)"] = 1.00
        factors["District Steam"]["kg (kilograms)"] = 2.63
        factors["District Steam"]["kLbs. (thousand pounds)"] = 1194.00
        factors["District Steam"]["Lbs. (pounds)"] = 1.19
        factors["District Steam"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["District Steam"]["MLbs. (million pounds)"] = 1194000.00
        factors["District Steam"]["therms"] = 100.00
        factors["Electric"]["GJ"] = 947.82
        factors["Electric"]["Btu"] = 0.001
        factors["Electric"]["kBtu (thousand Btu)"] = 1.00
        factors["Electric"]["Wh (Watt-hours)"] = 0.00341
        factors["Electric"]["kWh (thousand Watt-hours)"] = 3.41
        factors["Electric"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Electric"]["MWh (million Watt-hours)"] = 3412.00
        factors["Electric - Grid"]["GJ"] = 947.82
        factors["Electric - Grid"]["Btu"] = 0.001
        factors["Electric - Grid"]["kBtu (thousand Btu)"] = 1.00
        factors["Electric - Grid"]["Wh (Watt-hours)"] = 0.00341
        factors["Electric - Grid"]["kWh (thousand Watt-hours)"] = 3.41
        factors["Electric - Grid"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Electric - Grid"]["MWh (million Watt-hours)"] = 3412.00
        factors["Electric - Solar"]["GJ"] = 947.82
        factors["Electric - Solar"]["Btu"] = 0.001
        factors["Electric - Solar"]["kBtu (thousand Btu)"] = 1.00
        factors["Electric - Solar"]["Wh (Watt-hours)"] = 0.00341
        factors["Electric - Solar"]["kWh (thousand Watt-hours)"] = 3.41
        factors["Electric - Solar"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Electric - Solar"]["MWh (million Watt-hours)"] = 3412.00
        factors["Electric - Wind"]["GJ"] = 947.82
        factors["Electric - Wind"]["Btu"] = 0.001
        factors["Electric - Wind"]["kBtu (thousand Btu)"] = 1.00
        factors["Electric - Wind"]["Wh (Watt-hours)"] = 0.00341
        factors["Electric - Wind"]["kWh (thousand Watt-hours)"] = 3.41
        factors["Electric - Wind"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Electric - Wind"]["MWh (million Watt-hours)"] = 3412.00
        factors["Electric - Unknown"]["GJ"] = 947.82
        factors["Electric - Unknown"]["Btu"] = 0.001
        factors["Electric - Unknown"]["kBtu (thousand Btu)"] = 1.00
        factors["Electric - Unknown"]["Wh (Watt-hours)"] = 0.00341
        factors["Electric - Unknown"]["kWh (thousand Watt-hours)"] = 3.41
        factors["Electric - Unknown"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Electric - Unknown"]["MWh (million Watt-hours)"] = 3412.00
        factors["Fuel Oil (No. 1)"]["Gallons (UK)"] = 167.18
        factors["Fuel Oil (No. 1)"]["Gallons (US)"] = 139.21
        factors["Fuel Oil (No. 1)"]["GJ"] = 947.82
        factors["Fuel Oil (No. 1)"]["Btu"] = 0.001
        factors["Fuel Oil (No. 1)"]["kBtu (thousand Btu)"] = 1.00
        factors["Fuel Oil (No. 1)"]["Liters"] = 36.78
        factors["Fuel Oil (No. 1)"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Fuel Oil (No. 2)"]["Gallons (UK)"] = 167.18
        factors["Fuel Oil (No. 2)"]["Gallons (US)"] = 139.21
        factors["Fuel Oil (No. 2)"]["GJ"] = 947.82
        factors["Fuel Oil (No. 2)"]["Btu"] = 0.001
        factors["Fuel Oil (No. 2)"]["kBtu (thousand Btu)"] = 1.00
        factors["Fuel Oil (No. 2)"]["Liters"] = 36.78
        factors["Fuel Oil (No. 2)"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Fuel Oil (No. 4)"]["Gallons (UK)"] = 167.18
        factors["Fuel Oil (No. 4)"]["Gallons (US)"] = 139.21
        factors["Fuel Oil (No. 4)"]["GJ"] = 947.82
        factors["Fuel Oil (No. 4)"]["Btu"] = 0.001
        factors["Fuel Oil (No. 4)"]["kBtu (thousand Btu)"] = 1.00
        factors["Fuel Oil (No. 4)"]["Liters"] = 36.78
        factors["Fuel Oil (No. 4)"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Fuel Oil (No. 5 and No. 6)"]["Gallons (UK)"] = 183.13
        factors["Fuel Oil (No. 5 and No. 6)"]["Gallons (US)"] = 152.48
        factors["Fuel Oil (No. 5 and No. 6)"]["GJ"] = 947.82
        factors["Fuel Oil (No. 5 and No. 6)"]["Btu"] = 0.001
        factors["Fuel Oil (No. 5 and No. 6)"]["kBtu (thousand Btu)"] = 1.00
        factors["Fuel Oil (No. 5 and No. 6)"]["Liters"] = 40.28
        factors["Fuel Oil (No. 5 and No. 6)"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Kerosene"]["Gallons (UK)"] = 162.36
        factors["Kerosene"]["Gallons (US)"] = 135.19
        factors["Kerosene"]["GJ"] = 947.82
        factors["Kerosene"]["Btu"] = 0.001
        factors["Kerosene"]["kBtu (thousand Btu)"] = 1.00
        factors["Kerosene"]["Liters"] = 35.71
        factors["Kerosene"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Natural Gas"]["ccf (hundred cubic feet)"] = 103.10
        factors["Natural Gas"]["cf (cubic feet)"] = 103.10
        factors["Natural Gas"]["cf (cubic feet)"] = 1.03
        factors["Natural Gas"]["cm (cubic meters)"] = 36.42
        factors["Natural Gas"]["GJ"] = 947.82
        factors["Natural Gas"]["Btu"] = 0.001
        factors["Natural Gas"]["kBtu (thousand Btu)"] = 1.00
        factors["Natural Gas"]["kcf (thousand cubic feet)"] = 103.10
        factors["Natural Gas"]["kcf (thousand cubic feet)"] = 1031.00
        factors["Natural Gas"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Natural Gas"]["Mcf (million cubic feet)"] = 1031430.00
        factors["Natural Gas"]["therms"] = 100.00
        factors["Other:"]["GJ"] = 947.82
        factors["Other:"]["Btu"] = 0.001
        factors["Other:"]["kBtu (thousand Btu)"] = 1.00
        factors["Propane"]["ccf (hundred cubic feet)"] = 251.60
        factors["Propane"]["cf (cubic feet)"] = 2.52
        factors["Propane"]["Gallons (UK)"] = 109.06
        factors["Propane"]["Gallons (US)"] = 90.81
        factors["Propane"]["GJ"] = 947.82
        factors["Propane"]["Btu"] = 0.001
        factors["Propane"]["kBtu (thousand Btu)"] = 1.00
        factors["Propane"]["kcf (thousand cubic feet)"] = 2515.90
        factors["Propane"]["Liters"] = 23.99
        factors["Propane"]["MBtu/MMBtu (million Btu)"] = 100.00
        factors["Wood"]["GJ"] = 947.82
        factors["Wood"]["Btu"] = 0.001
        factors["Wood"]["kBtu (thousand Btu)"] = 1.00
        factors["Wood"]["MBtu/MMBtu (million Btu)"] = 1000.00
        factors["Wood"]["Tonnes (metric)"] = 17060.71
        factors["Wood"]["Tons"] = 15477.50

    return factors


def kgal_water_conversion_factors(coutry):
    """
    Returns water conversion factor provided by Portfolio Manager.
    Conversion factors taken from: https://www.kylesconverter.com/volume/kilogallons

    # should country be considered?
    """
    factors = defaultdict(dict)

    meter_types = [
        "Default",
        "Potable Indoor",
        "Potable: Mixed Indoor/Outdoor",
        "Potable Outdoor",
    ]
    # SHOULD THESE BE INCLUDED?
    # other_types = [
    #     "Other: Mixed Indoor/Outdoor",
    #     "Other Indoor",
    #     "Other Outdoor",
    #     "Reclaimed: Mixed Indoor/Outdoor"
    #     "Reclaimed: Indoor"
    #     "Reclaimed: Outdoor"
    #     "Well Water: Mixed Indoor/Outdoor"
    #     "Well Water: Indoor"
    #     "Well Water: Outdoor"
    # ]

    unit_conversion = {
        "ccf (hundred cubic feet)": 0.748,
        "cf (cubic feet)": 0.00748,
        "cGal (hundred gallons) (US)": 0.1,
        "cGal (hundred gallons) (UK)": 0.12,
        "cm (cubic meters)": 0.264172,
        "Gallons (US)": 0.001,
        "Gallons (UK)": 0.0012,
        "kcf (thousand cubic feet)": 7.48,
        "kcm (thousand cubit meters)": 264.172,
        "kGal (thousand gallons) (US)": 1.00,
        "kGal (thousand gallons) (UK)": 1.2,
        "Liters": 0.000264172,
        "Mcf (million cubic feed)": 7480.52,
        "MGal (million gallons) (UK)": 1000,
        "MGal (million gallons) (US)": 1200,
    }

    # Create dict of pattern {meter_type: {unit: conversion}, ...}
    for meter_type in meter_types:
        for unit, conversion in unit_conversion.items():
            factors[meter_type][unit] = conversion

    return factors


def fahrenheit_temperature_conversion_factors(coutry):
    """
    Returns water conversion factor provided by Portfolio Manager.
    Conversion factors taken from: https://www.kylesconverter.com/temperature/

    # should country be considered?
    """
    meter_types = ["Heating Degree Days", "Cooling Degree Days", "Average Temperature"]

    return {meter_type: {"F (Fahrenheit)": 1.00} for meter_type in meter_types}


def usage_point_id(raw_source_id):
    """
    Extracts and returns the usage point ID of a GreenButton full uri ID.
    """
    if raw_source_id and "/" in raw_source_id:
        id_split = raw_source_id.split("/")
        usage_point_index = next(i for i, substr in enumerate(id_split) if substr == "UsagePoint") + 1
        return id_split[usage_point_index]
    else:
        return raw_source_id

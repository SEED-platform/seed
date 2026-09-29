"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

Building Energy Surrogate Models analysis pipeline.

This pipeline runs building-energy surrogate (machine-learning) models from the
BEM-prediction-models project on each selected property to predict energy/cost
savings for building upgrade scenarios. The name is intentionally general so the
pipeline can host additional surrogate-model use cases over time; today it runs
the ``calculator_179d`` models and stores the 179D energy/cost savings and
tax-deduction results back on the property. The calculator's scientific-Python
dependencies are incompatible with SEED's, so it is executed out-of-process via
its own interpreter (see ``building_energy_surrogate_runner`` and the
``BUILDING_ENERGY_SURROGATE_PYTHON`` setting).

Per-property model inputs come from the 179D-portal export fields on the SEED
property: the building type (Property Type), gross floor area, and postal code
(used to derive the ASHRAE climate zone) from native columns, and HVAC System,
Number of Floors, Aspect Ratio, and Vertical Fenestration Percentage from
``extra_data``. The portal's "Building Information (continued)" advanced inputs
(envelope U-factors, window SHGC, lighting power density, HVAC efficiencies,
heating capacity, and service-hot-water specs) are also read from ``extra_data``
using the portal's field labels/IP units (see :data:`ADVANCED_INPUT_FIELDS`).
Any advanced input left blank falls back to a documented default "proposed
design" profile, and utility rates and the 179D tax-policy schedule (which the
portal does not collect per building) always come from that profile.
"""

import json
import logging
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from celery import chain, shared_task
from django.conf import settings
from django.db.models import Max
from quantityfield.units import ureg

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    AnalysisPipelineError,
    analysis_pipeline_task,
    task_create_analysis_property_views,
)
from seed.models import (
    Analysis,
    AnalysisMessage,
    AnalysisPropertyView,
    Column,
    ColumnListProfile,
    ColumnListProfileColumn,
    PropertyView,
)

logger = logging.getLogger(__name__)

RUNNER_PATH = Path(__file__).parent / "building_energy_surrogate_runner.py"

#: Square feet to square meters (matches calculator_179d.constants.FT2_TO_M2)
FT2_TO_M2 = 0.09290304

#: IP U-factor (Btu/h*ft^2*degF) to SI U-value (W/m^2*K). The 179D portal collects
#: envelope U-factors in IP units; ``PropertyInfo`` expects SI, so multiply.
BTU_FT2_F_TO_W_M2_K = 5.678263337

#: IP lighting power density (W/ft^2) to SI (W/m^2). The portal collects LPD in
#: W/ft^2; ``PropertyInfo.proposed_lpd_w_per_m2`` expects W/m^2, so multiply.
W_FT2_TO_W_M2 = 10.76391042

#: 179D-portal export field names (stored as SEED ``extra_data`` keys) for the
#: building inputs the portal collects. The remaining ``PropertyInfo`` inputs are
#: not exported by the portal and are supplied by :data:`DEFAULT_ENVELOPE_PROFILE`,
#: :data:`DEFAULT_LPD_W_PER_M2` and :data:`DEFAULT_HVAC_EFFICIENCY` below.
PORTAL_FIELD_ASPECT_RATIO = "Aspect Ratio"
PORTAL_FIELD_HVAC = "HVAC System"
PORTAL_FIELD_FLOORS = "Number of Floors"
PORTAL_FIELD_VF_PCT = "Vertical Fenestration Percentage"
PORTAL_FIELD_PLACED_IN_SERVICE = "Date Placed in Service"

#: Building types the surrogate models support (``calculator_179d.BuildingType``).
SUPPORTED_BUILDING_TYPES = {"small office", "retail stripmall"}

#: HVAC systems the surrogate models support (``calculator_179d.HVACSystemType``).
SUPPORTED_HVAC_SYSTEMS = {
    "PSZ-HP",
    "PSZ-AC with electric coil",
    "PSZ-AC with gas coil",
    "HP RTU",
    "MSHP DOAS",
    "VRF DOAS",
}

#: ``PropertyInfo`` fields that a property may override directly via extra_data
#: (advanced use: supply a measured value instead of the default profile).
OVERRIDE_FIELDS = [
    "shw_fuel_type",
    "erv_presence",
    "roof_u_value_w_per_m2_k",
    "wall_u_value_w_per_m2_k",
    "window_u_factor_w_per_m2_k",
    "window_shgc",
    "proposed_lpd_w_per_m2",
    "water_heating_standby_loss_btu_per_h",
    "water_heating_thermal_efficiency",
    "water_heating_first_hour_rating_gal_per_h",
    "water_heating_uef",
    "water_heating_capacity_btu_per_h",
    "SEER",
    "SEER2",
    "EER",
    "EER2",
    "gas_coil_average_efficiency",
    "boiler_average_efficiency",
    "HSPF",
    "HSPF2",
    "heatingCOP",
    "heating_capacity_btu_per_h",
    "electricity_rate_cents_per_kwh",
    "natural_gas_rate_usd_per_therm",
]

#: Default "proposed design" profile for the ``PropertyInfo`` inputs the 179D
#: portal does not export. Values mirror the calculator's documented portal input
#: example (``tests/test_data/portal_io_*.input.json`` in BEM-prediction-models):
#: a moderate high-performance envelope, commercial service hot water, and ERV.
#: In production the portal supplies these per building; this profile lets SEED
#: run the models from only the exported portal fields. Tune for your jurisdiction.
DEFAULT_ENVELOPE_PROFILE = {
    "shw_fuel_type": "naturalgas",
    # No energy-recovery ventilator by default. The 179D portal does not export
    # ERV presence and models these buildings without one; assuming an ERV
    # (erv_presence=1) over-credits ventilation heat recovery and inflates
    # predicted savings by ~6 points. With erv_presence=0 the surrogate matches
    # the portal's cost-savings % exactly for verified buildings.
    "erv_presence": 0,
    "roof_u_value_w_per_m2_k": 0.2839,
    "wall_u_value_w_per_m2_k": 0.45424,
    "window_u_factor_w_per_m2_k": 1.7034,
    "window_shgc": 0.3,
    "water_heating_standby_loss_btu_per_h": 1000.0,
    "water_heating_thermal_efficiency": 87.0,
}

#: Proposed lighting power density (W/m^2) by building type.
DEFAULT_LPD_W_PER_M2 = {
    "small office": 9.6875,
    "retail stripmall": 10.76,
}

#: Proposed HVAC efficiency metrics by system type. Heat-pump DOAS/RTU systems
#: are modeled without explicit efficiency inputs.
DEFAULT_HVAC_EFFICIENCY = {
    "PSZ-HP": {"SEER": 15.0, "HSPF": 8.5},
    "PSZ-AC with electric coil": {"SEER": 21.0},
    "PSZ-AC with gas coil": {"SEER": 15.0, "gas_coil_average_efficiency": 0.85},
    "HP RTU": {},
    "MSHP DOAS": {},
    "VRF DOAS": {},
}


def _hvac_is_gas(hvac_system):
    """Whether an HVAC system heats with natural gas (vs. all-electric).

    The 179D surrogate's supported systems are all-electric (heat pumps,
    electric-resistance coil) except those with a gas coil/furnace, whose name
    contains "gas" (e.g. "PSZ-AC with gas coil").
    """
    return "gas" in (hvac_system or "").lower()


#: Calculator water-heater inputs that only apply to natural-gas service hot
#: water. For electric SHW the calculator uses a fixed UA/efficiency and ignores
#: these, so they are dropped from an all-electric building's model inputs.
GAS_WATER_HEATER_FIELDS = (
    "water_heating_standby_loss_btu_per_h",
    "water_heating_thermal_efficiency",
    "water_heating_uef",
    "water_heating_first_hour_rating_gal_per_h",
    "water_heating_capacity_btu_per_h",
)

#: extra_data column names whose values only apply to gas-heated buildings
#: (natural-gas service hot water). Used to keep the inventory fuel-consistent.
GAS_ONLY_INPUT_COLUMNS = (
    "Water Heating Standby Loss",
    "Water Heating Thermal Efficiency",
)

#: extra_data column names whose values only apply to all-electric buildings
#: (heat-pump heating efficiency). Gas-heated buildings use a gas-coil/furnace
#: efficiency instead, so HSPF does not apply to them.
ELECTRIC_ONLY_INPUT_COLUMNS = (
    "Heating Efficiency (HSPF)",
)

#: ASHRAE 90.1 climate zone by 3-digit ZIP prefix. Covers the demo metros; extend
#: with an authoritative ZIP-to-climate-zone dataset for broader portal imports.
ZIP3_CLIMATE_ZONE = {
    "331": "1A", "332": "1A", "333": "1A", "334": "1A",  # Miami FL
    "770": "2A", "771": "2A", "772": "2A",  # Houston TX
    "850": "2B", "851": "2B", "852": "2B", "853": "2B",  # Phoenix AZ
    "303": "3A", "300": "3A", "301": "3A",  # Atlanta GA
    "900": "3B", "901": "3B", "902": "3B", "913": "3B",  # Los Angeles CA
    "891": "3B", "890": "3B",  # Las Vegas NV
    "941": "3C", "940": "3C", "943": "3C", "945": "3C",  # San Francisco Bay CA
    "212": "4A", "200": "4A", "201": "4A", "100": "4A", "104": "4A",  # Baltimore/DC/NYC
    "981": "4C", "982": "4C", "972": "4C", "973": "4C",  # Seattle/Portland
    "802": "5B", "800": "5B", "801": "5B",  # Denver CO
    "606": "5A", "607": "5A", "021": "5A", "022": "5A",  # Chicago/Boston
    "554": "6A", "553": "6A", "555": "6A",  # Minneapolis MN
    "597": "6B",  # Montana
    "832": "7", "836": "7",  # Idaho (cold)
    "997": "8",  # Fairbanks AK
}

#: Utility-rate defaults used when a property does not supply its own.
ECONOMICS_DEFAULTS = {
    "electricity_rate_cents_per_kwh": 11.58,
    # NOTE ON UNITS: despite the ``_per_therm`` name (inherited from the
    # calculator's PropertyInfo field), the calculator multiplies this rate by
    # ``KBTU_TO_THOUSAND_CUFT`` (1/1039), so energy is converted to *thousand
    # cubic feet* (MCF) before costing. The rate is therefore effectively
    # USD/MCF (~10x USD/therm). 11.38 USD/MCF ~= $1.10/therm ~ U.S. commercial
    # average. The calculator validates this field to [5, 50], so do NOT change
    # it to a per-therm value (~1.1) -- that both underestimates gas cost ~10x
    # and fails validation.
    "natural_gas_rate_usd_per_therm": 11.38,
}


#: 179D tax-deduction policy schedule (deduction $/ft^2 vs. % energy-cost savings).
#: These are policy constants, not per-building inputs. The IRS inflation-adjusts
#: the min/max deduction rates each year; the qualifying threshold stays 25% and
#: the maximum is reached at 50% savings, so each year's increment is
#: ``(max - min) / 25``.
def _tax_policy_schedule(energy_min, energy_max, all_min, all_max):
    return {
        "energy_tax_deduction_rate_min": energy_min,
        "energy_tax_deduction_rate_max": energy_max,
        "all_179d_tax_deduction_rate_min": all_min,
        "all_179d_tax_deduction_rate_max": all_max,
        "increment_energy": round((energy_max - energy_min) / 25.0, 6),
        "min_threshold_energy": 0.25,
        "increment_all_179d": round((all_max - all_min) / 25.0, 6),
        "min_threshold_all_179d": 0.25,
    }


#: Deduction $/ft^2 schedule keyed by the tax year the building is placed in
#: service. Rates are (energy_min, energy_max, all_179d_min, all_179d_max):
#:   2023 - IRS Rev. Proc. 2022-38
#:   2024 - IRS Rev. Proc. 2023-34 (verified against a real 179D Portal report:
#:          bonus $4.81/ft^2 at ~42.6% cost savings)
#:   2025 - IRS Rev. Proc. 2024-40
TAX_POLICY_BY_YEAR = {
    2023: _tax_policy_schedule(0.50, 1.00, 2.50, 5.00),
    2024: _tax_policy_schedule(0.57, 1.13, 2.83, 5.65),
    2025: _tax_policy_schedule(0.58, 1.16, 2.90, 5.81),
}

#: Fallback tax year used when the placed-in-service date is missing/unparseable.
DEFAULT_TAX_YEAR = max(TAX_POLICY_BY_YEAR)

#: Backwards-compatible alias for the default-year schedule.
TAX_POLICY_DEFAULTS = TAX_POLICY_BY_YEAR[DEFAULT_TAX_YEAR]


def _tax_year_from_date(raw):
    """Return the §179D tax year for a "Date Placed in Service" value.

    Accepts ISO ``YYYY-MM-DD``, ``MM/DD/YYYY`` and similar formats (or a bare
    year). Falls back to :data:`DEFAULT_TAX_YEAR` when missing/unparseable, and
    clamps to the range of known schedules (earliest for pre-2023 dates, latest
    for future years) so a valid deduction is always produced.
    """
    if raw in (None, ""):
        return DEFAULT_TAX_YEAR
    text = str(raw).strip()
    year = None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y"):
        try:
            year = datetime.strptime(text[:10], fmt).year
            break
        except ValueError:
            continue
    if year is None:
        match = re.search(r"(?:19|20)\d{2}", text)
        year = int(match.group(0)) if match else None
    if year is None:
        return DEFAULT_TAX_YEAR
    known_years = sorted(TAX_POLICY_BY_YEAR)
    if year <= known_years[0]:
        return known_years[0]
    if year >= known_years[-1]:
        return known_years[-1]
    if year in TAX_POLICY_BY_YEAR:
        return year
    return max(y for y in known_years if y <= year)


def _tax_policy_for_date(raw):
    """Return the §179D deduction schedule for a placed-in-service date value."""
    return TAX_POLICY_BY_YEAR[_tax_year_from_date(raw)]

#: 179D-portal "Building Information (continued)" advanced inputs (envelope,
#: lighting, HVAC efficiency, and service hot water). These are collected in the
#: SEED inventory as ``extra_data`` using the portal's field labels and IP units;
#: :func:`_build_calculator_input` converts each to the ``PropertyInfo`` (SI)
#: field named by ``target`` and lets it override the default profile. Fields left
#: blank fall back to the defaults, matching the portal's optional advanced inputs.
#: ``range`` is the portal's stated applicable range (in the column's own units).
ADVANCED_INPUT_FIELDS = [
    {
        "column_name": "Roof U-Factor",
        "display_name": "Roof U-Factor (Btu/ft\u00b2\u00b7\u00b0F\u00b7h)",
        "description": "179D portal envelope input: roof assembly U-factor (Btu/h\u00b7ft\u00b2\u00b7\u00b0F). Applicable range 0.02\u20130.048.",
        "target": "roof_u_value_w_per_m2_k",
        "factor": BTU_FT2_F_TO_W_M2_K,
        "range": (0.02, 0.048),
    },
    {
        "column_name": "Wall U-Factor",
        "display_name": "Wall U-Factor (Btu/ft\u00b2\u00b7\u00b0F\u00b7h)",
        "description": "179D portal envelope input: wall assembly U-factor (Btu/h\u00b7ft\u00b2\u00b7\u00b0F). Applicable range 0.033\u20130.064.",
        "target": "wall_u_value_w_per_m2_k",
        "factor": BTU_FT2_F_TO_W_M2_K,
        "range": (0.033, 0.064),
    },
    {
        "column_name": "Window U-Factor",
        "display_name": "Window U-Factor (Btu/ft\u00b2\u00b7\u00b0F\u00b7h)",
        "description": "179D portal envelope input: window U-factor (Btu/h\u00b7ft\u00b2\u00b7\u00b0F). Applicable range 0.2\u20130.45.",
        "target": "window_u_factor_w_per_m2_k",
        "factor": BTU_FT2_F_TO_W_M2_K,
        "range": (0.2, 0.45),
    },
    {
        "column_name": "Window SHGC",
        "display_name": "Window SHGC",
        "description": "179D portal envelope input: window solar heat gain coefficient. Applicable range 0.224\u20130.45.",
        "target": "window_shgc",
        "factor": 1.0,
        "range": (0.224, 0.45),
    },
    {
        "column_name": "Lighting Power Density",
        "display_name": "Lighting Power Density (W/ft\u00b2)",
        "description": "179D portal lighting input: lighting power density (W/ft\u00b2). Applicable range 0.418\u20131.0.",
        "target": "proposed_lpd_w_per_m2",
        "factor": W_FT2_TO_W_M2,
        "range": (0.418, 1.5),
    },
    {
        "column_name": "Heating Capacity",
        "display_name": "Heating Capacity (Btu/h)",
        "description": "179D portal HVAC input: heating capacity (Btu/h). Applicable range 27,741.995\u20131,928,112.",
        "target": "heating_capacity_btu_per_h",
        "factor": 1.0,
        "range": (27741.995, 1928112.0),
    },
    {
        "column_name": "Cooling Efficiency (SEER)",
        "display_name": "Cooling Efficiency (SEER)",
        "description": "179D portal HVAC input: cooling efficiency SEER (Btu/W\u00b7h). Applicable range 10.014\u201321.283.",
        "target": "SEER",
        "factor": 1.0,
        "range": (10.014, 21.283),
    },
    {
        "column_name": "Heating Efficiency (HSPF)",
        "display_name": "Heating Efficiency (HSPF)",
        "description": "179D portal HVAC input: heating efficiency HSPF (Btu/W\u00b7h). Applicable range 6.966\u201311.507.",
        "target": "HSPF",
        "factor": 1.0,
        "range": (6.966, 11.507),
    },
    {
        "column_name": "Water Heating Standby Loss",
        "display_name": "Water Heating Standby Loss (Btu/h)",
        "description": "179D portal hot-water input: commercial water-heater standby loss (Btu/h). Applicable range 800\u20131600.",
        "target": "water_heating_standby_loss_btu_per_h",
        "factor": 1.0,
        "range": (800.0, 1600.0),
    },
    {
        "column_name": "Water Heating Thermal Efficiency",
        "display_name": "Water Heating Thermal Efficiency (%)",
        "description": "179D portal hot-water input: commercial water-heater thermal efficiency (%). Applicable range 80\u201397.",
        "target": "water_heating_thermal_efficiency",
        "factor": 1.0,
        "range": (80.0, 97.0),
    },
]

#: Name of the column list profiles (List View + Detail View) that the 179D
#: result columns are added to when an analysis runs. The result columns are not
#: pre-created, so the analysis output fields only appear on the inventory and
#: property detail pages after the analysis has been run. No-op if no profile
#: with this name exists for the analysis's organization.
RESULT_PROFILE_NAME = "179D"

RESULT_COLUMNS = [
    {
        "column_name": "Energy & Power Cost Percent Savings",
        "display_name": "Energy & Power Cost Percent Savings",
        "description": "Percent total energy-cost savings computed by the 179D surrogate model in SEED",
        "result_key": "savings_total_cost_percent",
    },
    {
        "column_name": "Annual Site EUI Savings",
        "display_name": "Annual Site EUI Savings",
        "description": "Annual site EUI savings (kBtu/ft^2) computed by the 179D surrogate model in SEED",
        "result_key": "savings_total_energy_kbtu_per_sqft",
    },
    {
        "column_name": "Electricity Savings",
        "display_name": "Electricity Savings",
        "description": "Annual electricity savings (kBtu) computed by the 179D surrogate model in SEED",
        "result_key": "savings_electricity_kbtu",
    },
    {
        "column_name": "Energy & Power Cost Savings per SqFt",
        "display_name": "Energy & Power Cost Savings per SqFt",
        "description": "Annual energy-cost savings ($/ft^2) computed by the 179D surrogate model in SEED",
        "result_key": "savings_total_usd_per_sqft",
    },
    {
        "column_name": "Natural Gas Savings",
        "display_name": "Natural Gas Savings",
        "description": "Annual natural-gas savings (kBtu) computed by the 179D surrogate model in SEED",
        "result_key": "savings_naturalgas_kbtu",
    },
    {
        "column_name": "179D Tax Deduction-Energy Only",
        "display_name": "179D Tax Deduction-Energy Only",
        "description": "179D energy-path tax deduction ($/ft^2) computed by the surrogate model in SEED",
        "result_key": "tax_deduction_rate_energy",
    },
    {
        "column_name": "179D Tax Deduction-All Criteria",
        "display_name": "179D Tax Deduction-All Criteria",
        "description": "179D whole-building tax deduction ($/ft^2) computed by the surrogate model in SEED",
        "result_key": "tax_deduction_rate_all",
    },
]

#: Modeled *baseline* (pre-retrofit) absolute-energy columns written to each
#: property's ``extra_data`` so downstream consumers (e.g. the SEED-Agent RFP's
#: "Baseline Energy Profile" section) can report real numbers instead of a
#: placeholder. These are persisted exactly like ``RESULT_COLUMNS`` but are
#: intentionally NOT added to the "179D" inventory display profile, to keep the
#: List/Detail views focused on the headline savings and deduction metrics.
BASELINE_RESULT_COLUMNS = [
    {
        "column_name": "Baseline Electricity Use",
        "display_name": "Baseline Electricity Use (kBtu)",
        "description": "Modeled baseline annual electricity use (kBtu) from the 179D surrogate model in SEED",
        "result_key": "baseline_electricity_kbtu",
    },
    {
        "column_name": "Baseline Natural Gas Use",
        "display_name": "Baseline Natural Gas Use (kBtu)",
        "description": "Modeled baseline annual natural-gas use (kBtu) from the 179D surrogate model in SEED",
        "result_key": "baseline_naturalgas_kbtu",
    },
    {
        "column_name": "Baseline Total Energy Use",
        "display_name": "Baseline Total Energy Use (kBtu)",
        "description": "Modeled baseline annual total energy use (kBtu) from the 179D surrogate model in SEED",
        "result_key": "baseline_total_energy_kbtu",
    },
    {
        "column_name": "Baseline Energy Cost",
        "display_name": "Baseline Energy Cost ($)",
        "description": "Modeled baseline annual energy cost ($) from the 179D surrogate model in SEED",
        "result_key": "baseline_total_usd",
    },
    {
        "column_name": "Baseline Site EUI",
        "display_name": "Baseline Site EUI (kBtu/ft^2)",
        "description": "Modeled baseline site EUI (kBtu/ft^2) from the 179D surrogate model in SEED",
        "result_key": "baseline_total_energy_kbtu_per_sqft",
    },
]


def _get_gross_floor_area_ft2(property_view):
    """Return the property's gross floor area in ft^2 (float) or None."""
    gfa = property_view.state.gross_floor_area
    if gfa is None:
        return None
    if isinstance(gfa, ureg.Quantity):
        return float(gfa.magnitude)
    return float(gfa)


def _climate_zone_for_zip(postal_code):
    """Derive an ASHRAE 90.1 climate zone from a US postal code, or None."""
    if postal_code in (None, ""):
        return None
    zip3 = str(postal_code).strip()[:3]
    return ZIP3_CLIMATE_ZONE.get(zip3)


def _build_calculator_input(property_view):
    """Assemble the calculator_179d input dict from a property's portal fields.

    Reads the 179D-portal export fields (native SEED columns + ``extra_data``),
    derives climate zone from the postal code, and fills the inputs the portal
    does not export from the documented default profile. Per-property
    ``extra_data`` values matching :data:`OVERRIDE_FIELDS` take precedence.

    :returns: (inputs: dict | None, error: str | None)
    """
    state = property_view.state
    extra = state.extra_data or {}

    building_type = (state.property_type or extra.get("Property Type") or "").strip().lower()
    if building_type not in SUPPORTED_BUILDING_TYPES:
        return None, (
            f"Property skipped: Property Type {building_type or '(blank)'!r} is not supported by the "
            "179D surrogate models (supported: 'small office', 'retail stripmall')."
        )

    climate_zone = _climate_zone_for_zip(state.postal_code)
    if climate_zone is None:
        return None, (
            f"Property skipped: could not determine ASHRAE climate zone from postal code "
            f"{state.postal_code or '(blank)'!r}."
        )

    hvac_system = (extra.get(PORTAL_FIELD_HVAC) or "").strip()
    if hvac_system not in SUPPORTED_HVAC_SYSTEMS:
        return None, (
            f"Property skipped: HVAC System {hvac_system or '(blank)'!r} is not supported by the "
            "179D surrogate models."
        )

    gfa_ft2 = _get_gross_floor_area_ft2(property_view)
    if gfa_ft2 is None:
        return None, "Property skipped: no Gross Floor Area."

    try:
        number_of_floors = int(float(extra[PORTAL_FIELD_FLOORS]))
        aspect_ratio = float(extra[PORTAL_FIELD_ASPECT_RATIO])
        vf_pct = float(extra[PORTAL_FIELD_VF_PCT])
    except (KeyError, TypeError, ValueError):
        return None, (
            "Property skipped: missing or invalid 'Number of Floors', 'Aspect Ratio', "
            "or 'Vertical Fenestration Percentage'."
        )

    inputs = {
        **_tax_policy_for_date(extra.get(PORTAL_FIELD_PLACED_IN_SERVICE)),
        **ECONOMICS_DEFAULTS,
        **DEFAULT_ENVELOPE_PROFILE,
        **DEFAULT_HVAC_EFFICIENCY.get(hvac_system, {}),
        "building_type": building_type,
        "climate_zone": climate_zone,
        "hvac_system": hvac_system,
        "gross_floor_area_m2": gfa_ft2 * FT2_TO_M2,
        "number_of_floors": number_of_floors,
        "aspect_ratio": aspect_ratio,
        "window_wall_ratio": vf_pct / 100.0,
        "proposed_lpd_w_per_m2": DEFAULT_LPD_W_PER_M2[building_type],
    }

    # Advanced per-property overrides: let a property supply measured values for
    # any input the default profile otherwise fills.
    for field in OVERRIDE_FIELDS:
        if extra.get(field) not in (None, ""):
            inputs[field] = extra[field]

    # 179D-portal "Building Information (continued)" advanced inputs, collected in
    # the inventory using the portal's labels/IP units. Convert to PropertyInfo
    # (SI) units and override the default profile; blanks fall back to defaults.
    for spec in ADVANCED_INPUT_FIELDS:
        raw = extra.get(spec["column_name"])
        if raw in (None, ""):
            continue
        try:
            inputs[spec["target"]] = float(raw) * spec["factor"]
        except (TypeError, ValueError):
            return None, f"Property skipped: invalid {spec['column_name']!r} value {raw!r}."

    # Fuel classification follows the building's HVAC system: gas-heating systems
    # get natural-gas service hot water; all-electric systems (heat pumps,
    # electric-resistance coil) get electric service hot water, for which the
    # calculator applies a fixed water-heater UA/efficiency and ignores the gas
    # water-heater inputs. An explicit extra_data 'shw_fuel_type' still wins.
    if extra.get("shw_fuel_type") in (None, ""):
        inputs["shw_fuel_type"] = "naturalgas" if _hvac_is_gas(hvac_system) else "electricity"
    if inputs.get("shw_fuel_type") == "electricity":
        for field in GAS_WATER_HEATER_FIELDS:
            inputs.pop(field, None)

    return inputs, None


def _run_calculator(inputs):
    """Invoke the isolated calculator subprocess. Returns the parsed output dict.

    The returned dict contains an ``"error"`` key when the calculation failed.
    """
    python = getattr(settings, "BUILDING_ENERGY_SURROGATE_PYTHON", None)
    if not python:
        raise AnalysisPipelineError(
            "BUILDING_ENERGY_SURROGATE_PYTHON is not configured; cannot run the building energy "
            "surrogate models. Set it to the Python interpreter of a virtualenv that has "
            "calculator_179d installed."
        )

    env = os.environ.copy()
    package_dir = getattr(settings, "BUILDING_ENERGY_SURROGATE_PACKAGE_DIR", None)
    if package_dir:
        env["PYTHONPATH"] = package_dir + os.pathsep + env.get("PYTHONPATH", "")

    timeout = getattr(settings, "BUILDING_ENERGY_SURROGATE_TIMEOUT", 120)
    try:
        proc = subprocess.run(
            [python, str(RUNNER_PATH)],
            input=json.dumps(inputs),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"179D calculator timed out after {timeout}s."}
    except FileNotFoundError:
        return {"error": f"179D calculator interpreter not found: {python}"}

    stdout = (proc.stdout or "").strip()
    if not stdout:
        return {"error": f"179D calculator produced no output. stderr: {(proc.stderr or '').strip()[:500]}"}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"error": f"179D calculator returned unparseable output: {stdout[:500]}"}


class BuildingEnergySurrogatePipeline(AnalysisPipeline):
    def _prepare_analysis(self, property_view_ids, start_analysis=True):
        analysis = Analysis.objects.get(id=self._analysis_id)

        if not getattr(settings, "BUILDING_ENERGY_SURROGATE_PYTHON", None):
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=self._analysis_id,
                analysis_property_view_id=None,
                user_message=(
                    "Building Energy Surrogate Models is not configured on this server "
                    "(BUILDING_ENERGY_SURROGATE_PYTHON is unset)."
                ),
                debug_message="",
            )
            analysis.status = Analysis.FAILED
            analysis.save()
            raise AnalysisPipelineError("BUILDING_ENERGY_SURROGATE_PYTHON is not configured.")

        if not PropertyView.objects.filter(id__in=property_view_ids).exists():
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=self._analysis_id,
                analysis_property_view_id=None,
                user_message="Analysis found no valid properties.",
                debug_message="",
            )
            analysis.status = Analysis.FAILED
            analysis.save()
            raise AnalysisPipelineError("Analysis found no valid properties.")

        progress_data = self.get_progress_data()
        progress_data.total = 3
        progress_data.save()

        chain(
            task_create_analysis_property_views.si(self._analysis_id, property_view_ids),
            _finish_preparation.s(self._analysis_id),
            _run_analysis.s(self._analysis_id),
        ).apply_async()

    def _start_analysis(self):
        return None


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _finish_preparation(self, analysis_view_ids_by_property_view_id, analysis_id):
    pipeline = BuildingEnergySurrogatePipeline(analysis_id)
    pipeline.set_analysis_status_to_ready("Ready to run building energy surrogate model analysis")
    return list(analysis_view_ids_by_property_view_id.values())


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, analysis_property_view_ids, analysis_id):
    pipeline = BuildingEnergySurrogatePipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Running building energy surrogate models")
    analysis = Analysis.objects.get(id=analysis_id)

    existing_columns = _create_analysis_columns(analysis)

    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)

    for analysis_property_view in analysis_property_views:
        property_view = property_views_by_apv_id[analysis_property_view.id]

        inputs, error = _build_calculator_input(property_view)
        if error is not None:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=analysis_id,
                analysis_property_view_id=analysis_property_view.id,
                user_message=error,
                debug_message="",
            )
            continue

        result = _run_calculator(inputs)
        if "error" in result:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=analysis_id,
                analysis_property_view_id=analysis_property_view.id,
                user_message=f"179D calculation failed: {result['error']}",
                debug_message="",
            )
            continue

        qualifies = result.get("tax_deduction_rate_all", 0) > 0 or result.get("tax_deduction_rate_energy", 0) > 0
        analysis_property_view.parsed_results = {
            "Total Energy Cost Savings (%)": result.get("savings_total_cost_percent"),
            "Baseline EUI (kBtu/sqft)": round(result.get("baseline_total_energy_kbtu_per_sqft", 0), 2),
            "Proposed EUI (kBtu/sqft)": round(result.get("proposed_total_energy_kbtu_per_sqft", 0), 2),
            "Total Energy Savings (kBtu)": round(result.get("savings_total_energy_kbtu", 0), 2),
            "Total Cost Savings ($)": round(result.get("savings_total_usd", 0), 2),
            "179D Deduction - Energy ($/sqft)": result.get("tax_deduction_rate_energy"),
            "179D Deduction - Whole Building ($/sqft)": result.get("tax_deduction_rate_all"),
            "Qualifies for 179D": "Yes" if qualifies else "No",
        }
        analysis_property_view.save()

        for col in RESULT_COLUMNS + BASELINE_RESULT_COLUMNS:
            if col["column_name"] in existing_columns:
                value = result.get(col["result_key"])
                if isinstance(value, float):
                    value = round(value, 3)
                property_view.state.extra_data[col["column_name"]] = value
        property_view.state.save()

    pipeline.set_analysis_status_to_completed()


def _add_result_columns_to_profiles(analysis, result_column_names):
    """Append the 179D result columns to the org's "179D" list/detail profiles.

    This makes the analysis output fields appear on the inventory (List View) and
    property detail (Detail View) pages only after the analysis has been run. The
    result columns are not part of the profiles until this runs. Idempotent, and a
    no-op if no profile named ``RESULT_PROFILE_NAME`` exists for the organization.
    """
    columns_by_name = {
        col.column_name: col
        for col in Column.objects.filter(
            organization=analysis.organization,
            table_name="PropertyState",
            column_name__in=result_column_names,
        )
    }

    profiles = ColumnListProfile.objects.filter(
        organization=analysis.organization,
        name=RESULT_PROFILE_NAME,
    )
    for profile in profiles:
        profile_columns = ColumnListProfileColumn.objects.filter(column_list_profile=profile)
        existing_names = set(profile_columns.values_list("column__column_name", flat=True))
        next_order = (profile_columns.aggregate(Max("order"))["order__max"] or 0) + 1
        for name in result_column_names:
            column = columns_by_name.get(name)
            if column is None or name in existing_names:
                continue
            ColumnListProfileColumn.objects.create(
                column_list_profile=profile,
                column=column,
                order=next_order,
                pinned=False,
            )
            next_order += 1


def _create_analysis_columns(analysis):
    """Ensure the result extra_data columns exist. Returns the names available for writing.

    Headline savings/deduction columns (``RESULT_COLUMNS``) are also added to the
    "179D" inventory display profile; the modeled baseline columns
    (``BASELINE_RESULT_COLUMNS``) are created and written but kept off that profile
    so the List/Detail views stay focused on the headline metrics.
    """

    def _ensure(col):
        try:
            Column.objects.get(
                column_name=col["column_name"],
                organization=analysis.organization,
                table_name="PropertyState",
            )
            return True
        except Exception:
            if analysis.can_create():
                column = Column.objects.create(
                    is_extra_data=True,
                    column_name=col["column_name"],
                    organization=analysis.organization,
                    table_name="PropertyState",
                )
                column.display_name = col["display_name"]
                column.column_description = col["description"]
                column.save()
                return True
        return False

    headline_columns = [col["column_name"] for col in RESULT_COLUMNS if _ensure(col)]
    baseline_columns = [col["column_name"] for col in BASELINE_RESULT_COLUMNS if _ensure(col)]

    _add_result_columns_to_profiles(analysis, headline_columns)

    return headline_columns + baseline_columns

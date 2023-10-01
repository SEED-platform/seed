# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import transaction
from typing_extensions import NotRequired, TypedDict

from seed.models import Uniformat


class UniformatEntry(TypedDict):
    code: str
    category: str
    definition: NotRequired[str]
    imperial_units: NotRequired[str]
    metric_units: NotRequired[str]
    quantity_definition: NotRequired[str]


# https://www.wbdg.org/ffc/navy-navfac/design-build-request-proposal/uniformat-structure
uniformat_data: list[UniformatEntry] = [
    {
        'code': 'A',
        'category': 'SUBSTRUCTURE',
        'definition': 'This system includes all work below the lowest floor construction (usually slab-on-grade) and the enclosing horizontal and vertical elements required to form a basement, together with the necessary mass excavation and backfill.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Footprint area at grade'
    }, {
        'code': 'A10',
        'category': 'FOUNDATIONS',
        'definition': 'Foundations includes the following Standard Foundations: wall and column foundations; foundation walls up to level of top of slab on grade; pile caps; foundation excavation, backfill, and compaction; footings and bases; perimeter insulation; perimeter drainage; anchor plates; and dewatering. Special Foundations include pile foundations, caissons, underpinning, dewatering, raft foundations, and pressure injected grouting. Slab on grade includes standard slab on grade, structural slab on grade, inclined slab on grade, trenches, pits and bases, and foundation drainage.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Footprint area at grade'
    }, {
        'code': 'A1010',
        'category': 'STANDARD FOUNDATIONS',
        'definition': 'Continuous footings, spread footings, grade beams, foundation walls, pile caps, and column piers.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Footprint area at grade'
    }, {
        'code': 'A101001',
        'category': 'WALL FOUNDATIONS',
        'definition': 'Continuous Footings - Assemblies include excavation, hand-shaped bottom, compacted backfill, formwork and keyway, reinforcing steel, concrete and screed finish.\nFoundation Walls - Include work items associated with CIP foundation walls, grade beams, or CMU walls. Assemblies include excavation, compacted backfill, perimeter insulation, perimeter drainage, formwork, reinforcing steel, concrete or CMU, and wall finish.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of footings and/or wall foundations'
    }, {
        'code': 'A101002',
        'category': 'COLUMN FOUNDATIONS & PILE CAPS',
        'definition': 'Spread Footings: Individual or part of continuous pier footings. Assemblies include excavation, backfill and compaction, formwork, reinforcing steel, and concrete and screed finish. If structural steel columns set directly on spread footings, anchor bolts are included in this assembly.\nPile Caps - Assemblies include excavation if required (normally due to installation of piles, the subgrade is at desired level for pile cap), hand-shaped bottom, compacted backfill, formwork, reinforcing steel, and concrete and screed finish. If structural steel columns set directly on spread footings, anchor bolts are included in this assembly.\nColumn Piers - Assemblies include formwork, reinforcing steel, concrete or CMU, finish, break ties and patch, and set anchor bolts.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of footings, pile caps and/or piers'
    }, {
        'code': 'A101003',
        'category': 'DEWATERING',
        'definition': 'Dewatering is the removal of water from excavations. The two principle methods of dewatering are by pump or by a system involving the sinking of a series of well-points around the area and extracting the water by suction pump. Assemblies would include pumps or well points and all associated dewatering materials and equipment.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Dewatered area'
    }, {
        'code': 'A101090',
        'category': 'OTHER STANDARD FOUNDATIONS',
        'definition': 'Standard foundations not described by the assembly categories listed above.'
    }, {
        'code': 'A1020',
        'category': 'SPECIAL FOUNDATIONS',
        'definition': 'All work associated with special foundations including piles, caissons, and any other special foundation situation.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Footprint area at grade'
    }, {
        'code': 'A102001',
        'category': 'PILE FOUNDATIONS',
        'definition': 'CIP concrete piles, precast concrete piles, steel pipe piles, steel H-piles, step-tapered steel piles, and treated wood piles. Applicable assemblies would include the material for piles, pile driving, and pile cut-offs if required.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Footprint area at grade'
    }, {
        'code': 'A102002',
        'category': 'CAISSONS',
        'definition': 'Drilled Caissons - Assemblies include drilled caissons, steel casings if required, reinforcing steel, bell bottom excavation, concrete, and loading and hauling of excavated material.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Footprint area at grade'
    }, {
        'code': 'A102003',
        'category': 'UNDERPINNING',
        'definition': 'Underpinning is the provision of permanent support for existing buildings by extending their foundations to a new, lower level containing the desired bearing stratum. Assemblies include excavation, backfill, and underpinning materials.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of underpinning'
    }, {
        'code': 'A102004',
        'category': 'DEWATERING',
        'definition': 'Dewatering is the removal of water from excavations. The two principle methods of dewatering are by pump or by a system involving the sinking of a series of well-points around the area and extracting the water by suction pump. Assemblies would include pumps or well points and all associated dewatering materials and equipment.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Dewatered area'
    }, {
        'code': 'A102005',
        'category': 'RAFT FOUNDATIONS',
        'definition': 'Raft foundations or spread foundations consist of a solid slab of heavily reinforced concrete covering the entire building footprint area.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of raft foundation'
    }, {
        'code': 'A102006',
        'category': 'PRESSURE INJECTED GROUTING',
        'definition': 'Assemblies provide for injecting cement grout for foundation stabilization.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Footprint area at grade'
    }, {
        'code': 'A102090',
        'category': 'OTHER SPECIAL FOUNDATIONS',
        'definition': 'These could include cofferdams, soil compaction foundations, and other special foundations. Assemblies would include all material and labor necessary to perform the work for the special foundation condition.'
    }, {
        'code': 'A1030',
        'category': 'SLAB ON GRADE',
        'definition': 'A slab poured on earth, whether on undisturbed or fill soil.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Footprint area at grade'
    }, {
        'code': 'A103001',
        'category': 'STANDARD SLAB ON GRADE',
        'definition': 'Standard slab-on-grade is supported by compacted earth or gravel fill. The soil bearing capacity is sufficient to support the slab. Assemblies include fine grade, gravel fill, underslab insulation, edge forms, termite treatment (interior slabs only), vapor barrier, reinforcing, expansion joints, control joints, and finish and curing. Assemblies are based on thickness of slab.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of slab'
    }, {
        'code': 'A103002',
        'category': 'STRUCTURAL SLAB ON GRADE',
        'definition': 'A structural slab-on-grade is not supported by compacted earth or gravel fill. The soil bearing capacity is insufficient to support the slab. A structural slab is generally a minimum of eight inches thick and will be reinforced with reinforcing bars rather than welded wire fabric. Assemblies include fine grade, gravel fill, underslab insulation, edge forms, termite treatment, (interior slabs only), vapor barrier, reinforcing, expansion joints, control joints, and finish and curing. Assemblies are based on thickness of slab.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of slab'
    }, {
        'code': 'A103003',
        'category': 'TRENCHES',
        'definition': 'Cast-in-place trenches. Assemblies include excavation, hand-shaped bottoms, compacted backfill, formwork, reinforcing steel, concrete, and concrete finish. Examples include trench drains and dust trenches.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of trench'
    }, {
        'code': 'A103004',
        'category': 'PITS AND BASES',
        'definition': 'Cast-in-place pits and bases. Assemblies include excavation, hand-shaped bottoms, compacted backfill, formwork, reinforcing steel, concrete, and concrete finish. Examples include elevator pits, dock leveler pits, oil change pits, and bases for equipment.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of pits and bases'
    }, {
        'code': 'A103005',
        'category': 'FOUNDATION DRAINAGE',
        'definition': 'Foundation drainage directly associated with draining the foundation. This category does not include storm drainage piping for site. It would include drain pipe or drain tile at foundation or basement for specific purposes of draining foundation or basement. Assemblies would include excavation, hand-shaped bottoms, gravel, compacted backfill, and drain pipe, including accessories.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of foundation'
    }, {
        'code': 'A103090',
        'category': 'OTHER LOWEST FLOOR CONSTRUCTION',
        'definition': 'Lowest floor construction not described by the assembly categories listed above.'
    }, {
        'code': 'A20',
        'category': 'BASEMENT CONSTRUCTION',
        'definition': 'Work Includes basement excavation, and basement walls.',
        'imperial_units': 'CY',
        'metric_units': 'M3',
        'quantity_definition': 'Volume of excavation'
    }, {
        'code': 'A2010',
        'category': 'BASEMENT EXCAVATION',
        'definition': 'Excavation work associated with constructing a basement.',
        'imperial_units': 'CY',
        'metric_units': 'M3',
        'quantity_definition': 'Volume of excavation'
    }, {
        'code': 'A201001',
        'category': 'EXCAVATION FOR BASEMENTS',
        'definition': 'All excavation, stockpiling, and hauling associated with basement excavations are included in this assembly.',
        'imperial_units': 'CY',
        'metric_units': 'M3',
        'quantity_definition': 'Volume of excavation'
    }, {
        'code': 'A201002',
        'category': 'STRUCTURE BACKFILL & COMPACTION',
        'definition': 'All backfill including hauling in of suitable soils and all necessary compaction is included in this assembly.',
        'imperial_units': 'CY',
        'metric_units': 'M3',
        'quantity_definition': 'Volume of backfill'
    }, {
        'code': 'A201003',
        'category': 'SHORING',
        'definition': 'This type of shoring is to resist horizontal pressure and not intended to carry vertical loads. Assemblies would include sheet piling or other material and labor used to hold back earth around the perimeter of an excavation.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Shoring contact area'
    }, {
        'code': 'A201090',
        'category': 'OTHER BASEMENT EXCAVATION',
        'definition': 'Basement excavation not described by the assembly categories listed above.'
    }, {
        'code': 'A2020',
        'category': 'BASEMENT WALLS',
        'definition': 'Assembly includes basement perimeter walls that are below grade and below the ground floor level of the building; this also includes elevator pits and other pits.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of wall'
    }, {
        'code': 'A202001',
        'category': 'BASEMENT WALL CONSTRUCTION',
        'definition': 'This includes work items associated with CIP foundation walls or CMU walls and penetrations. Assemblies include formwork, reinforcing steel, concrete or CMU, and wall finish and curing.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of wall'
    }, {
        'code': 'A202002',
        'category': 'MOISTURE PROTECTION',
        'definition': 'This assembly would be based on the type and square footage of waterproofing used on the foundation wall.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of wall moisture protection'
    }, {
        'code': 'A202003',
        'category': 'BASEMENT WALL INSULATION',
        'definition': 'This assembly would be based on the type and square footage of insulation used on the foundation wall.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of wall insulation'
    }, {
        'code': 'A202090',
        'category': 'OTHER BASEMENT WALLS',
        'definition': 'Basement walls not described by the assembly categories listed above.'
    }, {
        'code': 'B',
        'category': 'SHELL',
        'definition': 'This system includes all structural slabs, and decks and supports within basements and above grade. Note that the structural work will include both horizontal items (slabs, decks, etc.) and vertical structural components (columns and interior structural walls). Exterior load bearing walls are not included in this system but in System B2010, Exterior Walls.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of supported floors'
    }, {
        'code': 'B10',
        'category': 'SUPERSTRUCTURE',
        'definition': 'Work includes floor construction and roof construction.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of supported floors'
    }, {
        'code': 'B1010',
        'category': 'FLOOR CONSTRUCTION',
        'definition': 'This construction can be wood, concrete, CMU, steel frame, etc.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of supported floors'
    }, {
        'code': 'B101001',
        'category': 'STRUCTURAL FRAME',
        'definition': 'The structural frame could consist of structural steel including columns, beams, joists, and all associated items. It could be a concrete frame utilizing concrete or masonry columns and concrete girders and beams. The structural frame could be wood columns with wood beams or wood trusses. The structural frame could be a combination of the above. For example, concrete or masonry columns with structural steel beams and joists. All associated work items should be included in each assembly. Separate assemblies would be used for different types of construction. The unit of measure at the assembly level is the square footage of the supported area. Decks and slabs are not included in this assembly.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of supported floors'
    }, {
        'code': 'B101002',
        'category': 'STRUCTURAL INTERIOR WALLS',
        'definition': 'Assemblies would be CIP or CMU walls or other structural interior walls. The assemblies would include the labor and material required to perform the construction tasks associated with this type of wall.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of wall'
    }, {
        'code': 'B101003',
        'category': 'FLOOR DECKS AND SLABS',
        'definition': 'Slabs above grade should be broken into assemblies according to their particular type of construction (i.e., flat slab, pan slab, precast or pre-stressed slab, four-way slab, slabs on metal or wood decking with concrete fill, etc.). All associated work items should be included in each assembly, such as expansion and contraction joints.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of supported floors'
    }, {
        'code': 'B101004',
        'category': 'INCLINED AND STEPPED FLOORS',
        'definition': 'This assembly should be broken down according to their particular type of construction (i.e., flat slab, pan slab, precast or pre-stressed slab, four-way slab, slabs on metal or wood decking with concrete fill, etc.). All associated work items should be included in each assembly, such as expansion and contraction joints.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of inclined & stepped floors'
    }, {
        'code': 'B101005',
        'category': 'BALCONY CONSTRUCTION',
        'definition': 'Balconies above grade should be broken into assemblies according to their particular type of construction. All associated items including handrails should be included in the assembly.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of supported balconies'
    }, {
        'code': 'B101006',
        'category': 'RAMPS',
        'definition': 'Ramps above grade should be broken into assemblies according to their type of construction. All associated items including handrails should be included in the assembly.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of supported ramps'
    }, {
        'code': 'B101007',
        'category': 'FLOOR RACEWAY SYSTEMS',
        'definition': 'Under floor or in-slab conduit including conduit and all associated devices.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'B101090',
        'category': 'OTHER FLOOR CONSTRUCTION',
        'definition': 'Any type of special floor construction not included above would fall in this category, such as catwalks, space frames, etc. All associated work items would be included in the assembly.'
    }, {
        'code': 'B1020',
        'category': 'ROOF CONSTRUCTION',
        'definition': 'This construction is similar to floor construction except that is applies to the framework supporting the roof and roof decks. (See also System B30 Roofing.)',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of supported roof'
    }, {
        'code': 'B102001',
        'category': 'STRUCTURAL FRAME',
        'definition': 'The structural frame could consist of structural steel including columns, beams, joists, and all associated items. It could be a concrete frame utilizing concrete or masonry columns and concrete girders and beams. The structural frame could be wood columns with wood beams or wood trusses. The structural frame could be a combination of the above. For example, concrete or masonry columns with structural steel beams and joists. All associated work items should be included in each assembly. Separate assemblies would be used for different types of construction. The unit of measure at the assembly level is the square footage of the supported area. Decks and slabs are not included in this assembly.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of supported roof'
    }, {
        'code': 'B102002',
        'category': 'STRUCTURAL INTERIOR WALLS',
        'definition': 'Assemblies would be CIP or CMU walls or other structural interior walls. The assemblies would include the labor and material required to perform the construction tasks associated with this type of wall.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of walls'
    }, {
        'code': 'B102003',
        'category': 'ROOF DECKS AND SLABS',
        'definition': 'Roof decks and slabs should be broken into assemblies according to their particular type of construction (i.e., flat slab, pan slab, precast or pre-stressed slab, four-way slab, slabs on metal or wood decking with concrete fill, etc.). All associated work items should be included in each assembly.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of supported roof'
    }, {
        'code': 'B102004',
        'category': 'CANOPIES',
        'definition': 'Canopies should be broken into assemblies according to their particular type of construction (i.e., flat slab, pan slab, precast or pre-stressed slab, four-way slab, slabs on metal or wood decking with concrete fill, etc.). All associated work items should be included in each assembly.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of supported canopies'
    }, {
        'code': 'B102090',
        'category': 'OTHER ROOF CONSTRUCTION',
        'definition': 'Any type of special roof construction not included above would fall into this category. All associated work items would be included in this assembly.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of supported roof'
    }, {
        'code': 'B20',
        'category': 'EXTERIOR ENCLOSURE',
        'definition': 'This system consists of the exterior facing of the facility, which includes all vertical and horizontal exterior closure such as exterior walls, exterior windows, and exterior doors. This system excludes roofing (See System B30, Roof). Load bearing exterior walls will be included here, and not in System B10, Superstructure. Structural frame elements at exterior such as columns, beams, spandrels, etc., would be included in Superstructure with only the applied exterior finishes (i.e., paint, stucco, etc.) being included here. Finishes to the inside face of walls which are not an integral part of the wall construction will be included in System C30, Interior Finishes.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of exterior walls'
    }, {
        'code': 'B2010',
        'category': 'EXTERIOR WALLS',
        'definition': 'All materials associated with the following construction: exterior load-bearing walls, insulation and vapor barrier, parapets, exterior louvers and screens, sun control devices (exterior), balcony walls and handrails, exterior soffits, screen walls, and exterior coatings.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of exterior walls'
    }, {
        'code': 'B201001',
        'category': 'EXTERIOR CLOSURE',
        'definition': 'Assemblies would include material contained in exterior closure wall, such as masonry with brick veneer. Materials used for interior finishes on exterior walls are not included in this assembly. For example, if the interior side of this masonry wall is sheetrock applied on metal furring strips, the masonry wall is included in this assembly, but the furring strips and sheetrock are categorized as C3010 WALL FINISHES.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of exterior walls'
    }, {
        'code': 'B201002',
        'category': 'EXTERIOR WALL BACKUP CONSTRUCTION',
        'definition': 'Assemblies used to support structure for the exterior skin and/or provide load-bearing walls for the facility. Materials used for interior finishes on exterior walls are not included in this assembly. For example, if the interior side of this masonry wall is sheetrock applied on metal furring strips, the masonry wall is included in this assembly, but the furring strips and sheetrock are categorized as C3010 WALL FINISHES.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of backup walls'
    }, {
        'code': 'B201003',
        'category': 'INSULATION & VAPOR RETARDER',
        'definition': 'Assemblies would include all types of insulation associated with the exterior wall. Rigid, batt and poured insulation should be separated into different assemblies.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of insulation'
    }, {
        'code': 'B201004',
        'category': 'PARAPETS',
        'definition': 'Assemblies include materials used in association with parapets. Parapets are long walls or railings usually along the edge of a roof or balcony.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of parapets'
    }, {
        'code': 'B201005',
        'category': 'EXTERIOR LOUVERS & SCREENS',
        'definition': 'Assemblies include louvers and screens which are located in exterior walls. The unit of measure at the assembly level is each.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of louvers and screens'
    }, {
        'code': 'B201006',
        'category': 'BALCONY WALLS & HANDRAILS',
        'definition': 'Assemblies would include materials associated with balcony walls and handrails. These rails are usually guardrails and not associated with stairs.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of walls and handrails'
    }, {
        'code': 'B201007',
        'category': 'EXTERIOR SOFFITS',
        'definition': 'Assemblies would include all associated materials which make up the soffit and supports for the soffit. Typical materials would include wood, aluminum, exterior grade gypboard, stucco, etc.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of soffits'
    }, {
        'code': 'B201008',
        'category': 'FLASHING',
        'definition': 'Assemblies include all flashings associated with the exterior walls except for thru-wall flashing.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of flashings'
    }, {
        'code': 'B201009',
        'category': 'EXTERIOR PAINTING AND SPECIAL COATINGS',
        'definition': 'Assemblies include paint, stucco, etc. The unit of measure at the assembly level is area of exterior coatings.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of exterior coatings'
    }, {
        'code': 'B201010',
        'category': 'EXTERIOR JOINT SEALANT',
        'definition': 'Exterior application of joint sealants to seal joints and prepare for finish material installation.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of sealants'
    }, {
        'code': 'B201011',
        'category': 'SUN CONTROL DEVICES',
        'definition': 'Assemblies include awnings, shades, and solar panels attached to the exterior of the building. A separate assembly should be used for each type of sun control device.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of sun control devices'
    }, {
        'code': 'B201012',
        'category': 'SCREEN WALLS',
        'definition': 'Exterior screen walls used for security purposes immediately adjacent to the building such as screen walls at a loading dock. Assemblies would include materials associated with all types of walls. This can also include visual barriers on the roof to screen equipment. Note that perimeter fencing that is typically more than five feet from the building\'s exterior is included in sitework rather than in this system.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of screen wall'
    }, {
        'code': 'B201090',
        'category': 'OTHER EXTERIOR WALLS',
        'definition': 'Exterior walls not described by the assembly categories listed above.'
    }, {
        'code': 'B2020',
        'category': 'EXTERIOR WINDOWS',
        'definition': 'All windows located in exterior walls or exterior skin.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of windows'
    }, {
        'code': 'B202001',
        'category': 'WINDOWS',
        'definition': 'Fixed or operable windows located in exterior walls or exterior skin. Assemblies would include frames, glazing, caulking, finishes and other associated work.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of windows'
    }, {
        'code': 'B202002',
        'category': 'STOREFRONTS',
        'definition': 'Fixed storefronts including associated doors in exterior walls or exterior skin. Assemblies would include integral storefront doors, frames, glazing, caulking, finishes, and other associated work.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of storefronts'
    }, {
        'code': 'B202003',
        'category': 'CURTAIN WALLS',
        'definition': 'This applies to glass curtain walls and spandrel glass in exterior walls or exterior skin. Assemblies would include integral curtainwall doors, frames, glazing, caulking, finishes, and other associated work.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of curtain walls'
    }, {
        'code': 'B202004',
        'category': 'EXTERIOR GLAZING',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of Glazing'
    }, {
        'code': 'B202090',
        'category': 'OTHER EXTERIOR WINDOWS',
        'definition': 'Exterior windows not described by the assembly categories listed above.'
    }, {
        'code': 'B2030',
        'category': 'EXTERIOR DOORS',
        'definition': 'All doors located in exterior walls or exterior skin.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of doors'
    }, {
        'code': 'B203001',
        'category': 'SOLID DOORS',
        'definition': 'Assemblies include all exterior solid doors, hollow metal or wood with frames. Solid doors may include glazing lites in doors. Door hardware is located in B203008 EXTERIOR DOOR HARDWARE.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of doors'
    }, {
        'code': 'B203002',
        'category': 'GLAZED DOORS',
        'definition': 'Assemblies include all full glazed exterior doors with glass, frames not included in storefront and curtainwalls. These doors can be made of storefront materials but are not part of a curtainwall or storefront. Door hardware is located in B203008 EXTERIOR DOOR HARDWARE.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of doors'
    }, {
        'code': 'B203003',
        'category': 'REVOLVING DOORS',
        'definition': 'Assemblies include all revolving doors at exterior of the facility.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of doors'
    }, {
        'code': 'B203004',
        'category': 'OVERHEAD AND ROLL-UP DOORS',
        'definition': 'Overhead and roll-up doors installed in exterior walls or exterior skin. Assemblies include frames, hardware, hoisting devices, and finish and other associated work. The unit of measure at the assembly level is each door.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of doors'
    }, {
        'code': 'B203005',
        'category': 'HANGAR DOORS',
        'definition': 'Large aircraft doors used on medium and high bay hangars. Assemblies would include frames, hardware, hoisting devices, and finish and other associated work.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of doors'
    }, {
        'code': 'B203006',
        'category': 'BLAST RESISTANT DOORS',
        'definition': 'Special exterior doors used for blast resistance. Assemblies would include frames, hardware, hoisting devices, and finish and other associated work.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of doors'
    }, {
        'code': 'B203007',
        'category': 'GATES',
        'definition': 'Any special gate type used in the exterior wall or exterior skin of the building. Assemblies would include frames, hardware, hoisting devices, and finish and other associated work. The unit of measure at the assembly level is each gate.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of doors'
    }, {
        'code': 'B203008',
        'category': 'EXTERIOR DOOR HARDWARE',
        'definition': 'Exterior door hardware includes items such as closers, hinges, locksets, panic hardware, etc.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of doors'
    }, {
        'code': 'B203090',
        'category': 'OTHER EXTERIOR SPECIALTY DOORS',
        'definition': 'Any special type door used in the exterior wall or exterior skin of the building. Assemblies would include frames, hardware, hoisting devices, and finish and other associated work. The unit measure at the assembly level is each door, or area of special doors, i.e., hangar doors.'
    }, {
        'code': 'B203091',
        'category': 'OTHER EXTERIOR PERSONNEL DOORS',
        'definition': 'Exterior personnel doors not described by the assembly categories listed above.'
    }, {
        'code': 'B30',
        'category': 'ROOFING',
        'definition': 'This System includes all waterproof roof coverings and insulation, expansion joints, together with skylights, hatches, ventilators, and all required trim. In addition to roof coverings, the system includes all waterproof membranes and traffic toppings over below grade enclosed areas, balconies, and the like.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross area of roof'
    }, {
        'code': 'B3010',
        'category': 'ROOF COVERINGS',
        'definition': 'This System includes all waterproof roof coverings and insulation, expansion joints, together with skylights, hatches, ventilators, and all required trim. In addition to roof coverings, the system includes all waterproof membranes and traffic toppings over below grade enclosed areas, balconies, and the like.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross area of roof'
    }, {
        'code': 'B301001',
        'category': 'STEEP SLOPE ROOF SYSTEMS',
        'definition': 'Assemblies include roof coverings such as shingle, wood shake, structural standing seam, metal roofing, etc.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of roof covering'
    }, {
        'code': 'B301002',
        'category': 'LOW SLOPE ROOF SYSTEMS',
        'definition': 'Assemblies include roof coverings such as built-up, elastomeric, modified bitumen, etc. Also, walkways and work areas (used to gain access to rooftop equipment) will be included here.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of topping or membrane'
    }, {
        'code': 'B301003',
        'category': 'ROOF INSULATION & FILL',
        'definition': 'Assemblies include all types of insulation associated with the roof area.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of insulation'
    }, {
        'code': 'B301004',
        'category': 'FLASHINGS & TRIM',
        'definition': 'Assemblies include all flashings associated with the roof, i.e., eave flashing, gable flashing, etc.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of flashings'
    }, {
        'code': 'B301005',
        'category': 'GUTTERS & DOWNSPOUTS',
        'definition': 'Assemblies include all gutters, downspouts, and associated work including splash blocks.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of gutters and downspouts'
    }, {
        'code': 'B301006',
        'category': 'ROOF OPENINGS AND SUPPORTS',
        'definition': 'All roof penetrations including roof hatches, sky lights, area glazing, gravity roof ventilators, smoke vents, etc.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of openings'
    }, {
        'code': 'B301090',
        'category': 'OTHER ROOFING',
        'definition': 'Roofing not described by the assembly categories listed above.'
    }, {
        'code': 'C',
        'category': 'INTERIOR',
        'definition': 'Construction which takes place inside the exterior wall or exterior closure. The system does not include interior structural walls, which are included in B1010 FLOOR CONSTRUCTION and B1020 ROOF CONSTRUCTION.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'C10',
        'category': 'INTERIOR CONSTRUCTION',
        'definition': 'This assembly includes partitions, interior doors, and specialties.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'C1010',
        'category': 'PARTITIONS',
        'definition': 'Includes all interior partitions.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of partitions'
    }, {
        'code': 'C101001',
        'category': 'FIXED PARTITIONS',
        'definition': 'Interior fixed partitions include metal or wood studs, sheetrock, masonry, and concrete walls.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of fixed partition walls'
    }, {
        'code': 'C101002',
        'category': 'DEMOUNTABLE PARTITIONS',
        'definition': 'Assemblies would include all demountable partitions and associated work including tracks and anchoring systems.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of demountable partition walls'
    }, {
        'code': 'C101003',
        'category': 'RETRACTABLE PARTITIONS',
        'definition': 'Assemblies would include all retractable or folding partitions and associated work including tracks and anchoring systems.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of retractable partition walls'
    }, {
        'code': 'C101004',
        'category': 'INTERIOR GUARDRAILS & SCREENS',
        'definition': 'Assemblies include balustrades (balcony handrails and the row screen of posts that support them) and screens and associated work including tracks and anchoring systems. These balustrades/guardrails are related to interior balconies and are not associated with stairs.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of balustrades and screens'
    }, {
        'code': 'C101005',
        'category': 'INTERIOR WINDOWS',
        'definition': 'Fixed or operable windows. Assemblies would include frames, glazing, caulking and other associated work.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of windows'
    }, {
        'code': 'C101006',
        'category': 'GLAZED PARTITIONS & STOREFRONTS',
        'definition': 'Fixed interior glazed partitions including interior storefronts with doors. Assemblies include frames, glazing, caulking, and other associated work.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of partitions and storefronts'
    }, {
        'code': 'C101007',
        'category': 'INTERIOR GLAZING',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of interior glazing'
    }, {
        'code': 'C101008',
        'category': 'INTERIOR JOINT SEALANT',
        'definition': 'Interior application of sealants to seal joints and prepare for finish material installation. The application shall include partitions, doors and fitting.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of sealants'
    }, {
        'code': 'C101090',
        'category': 'OTHER PARTITIONS',
        'definition': 'Interior partitions not described by the assembly categories listed above.'
    }, {
        'code': 'C1020',
        'category': 'INTERIOR DOORS',
        'definition': 'All interior doors.',
        'imperial_units': 'LEF',
        'metric_units': 'LEF',
        'quantity_definition': 'Number of leaves'
    }, {
        'code': 'C102001',
        'category': 'STANDARD INTERIOR DOORS',
        'definition': 'Assemblies include all standard interior wood or hollow metal doors with frames, finish, etc. Standard interior door may include vision lites. Interior door hardware is located in C102007 INTERIOR DOOR HARDWARE.',
        'imperial_units': 'LEF',
        'metric_units': 'LEF',
        'quantity_definition': 'Number of leaves'
    }, {
        'code': 'C102002',
        'category': 'GLAZED INTERIOR DOORS',
        'definition': 'Assemblies include all glazed interior doors with glass, frames, finish, including storefront, etc. Interior door hardware is located in C102007 INTERIOR DOOR HARDWARE.',
        'imperial_units': 'LEF',
        'metric_units': 'LEF',
        'quantity_definition': 'Number of leaves'
    }, {
        'code': 'C102003',
        'category': 'FIRE DOORS',
        'definition': 'Assemblies include all interior fire doors, including all necessary frames, and sensing devices integral with the door. Interior door hardware is located in C102007 INTERIOR DOOR HARDWARE.',
        'imperial_units': 'LEF',
        'metric_units': 'LEF',
        'quantity_definition': 'Number of leaves'
    }, {
        'code': 'C102004',
        'category': 'SLIDING & FOLDING DOORS',
        'definition': 'Assemblies include all sliding and folding doors with frames, hardware, locking devices, tracks, and supporting systems. The unit of measure at the assembly level is each.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of sliding or folding door'
    }, {
        'code': 'C102005',
        'category': 'INTERIOR OVERHEAD DOORS',
        'definition': 'Overhead doors installed in the interior of a facility. Assemblies include frames, hardware, hoisting devices, and finish and other associated work. The unit of measure at the assembly level is each door.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of doors'
    }, {
        'code': 'C102006',
        'category': 'INTERIOR GATES',
        'definition': 'Any special type gate installed in the interior of a facility. Assemblies include frames, hardware, hoisting devices, and finish and other associated work. The unit measure at the assembly level is each gate.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of gates'
    }, {
        'code': 'C102007',
        'category': 'INTERIOR DOOR HARDWARE',
        'definition': 'Interior door hardware includes items such as closers, hinges, locksets, panic hardware, etc.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of doors'
    }, {
        'code': 'C102090',
        'category': 'OTHER INTERIOR SPECIALTY DOORS',
        'definition': 'Any special type door installed in the interior of a facility. Assemblies include frames, hardware, hoisting devices, and finish and other associated work. The unit measure at the assembly level is each gate.'
    }, {
        'code': 'C102091',
        'category': 'OTHER INTERIOR PERSONNEL DOORS',
        'definition': 'Interior personnel doors not described by the assembly categories listed above.'
    }, {
        'code': 'C1030',
        'category': 'SPECIALTIES',
        'definition': 'Most commonly used specialty items.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'C103001',
        'category': 'COMPARTMENTS, CUBICLES & TOILET PARTITIONS',
        'definition': 'Assemblies include individual compartments, cubicles, toilet partitions, and urinal screens.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of compartments, cubicles, or toilet partitions'
    }, {
        'code': 'C103002',
        'category': 'TOILET & BATH ACCESSORIES',
        'definition': 'Toilet and bath accessories. For example, soap dispensers, toilet paper holder, towel dispensers, grab bars, bathroom mirrors, etc.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of accessories'
    }, {
        'code': 'C103003',
        'category': 'MARKER BOARDS & TACK BOARDS',
        'definition': 'Assemblies include all marker boards, tackboards, and fastening devices. The unit of measure at the assembly level is each.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each Board'
    }, {
        'code': 'C103004',
        'category': 'IDENTIFYING DEVICES',
        'definition': 'Assemblies include all signs, plaques, traffic markers, etc.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of identifying devices'
    }, {
        'code': 'C103005',
        'category': 'LOCKERS',
        'definition': 'Assemblies include all types of lockers, either wood or metal, single or double tier. Special bases used for lockers would be included in this assembly.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of lockers'
    }, {
        'code': 'C103006',
        'category': 'SHELVING',
        'definition': 'Assemblies include all types of shelving with brackets and all supporting materials and finish, if required.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of shelving'
    }, {
        'code': 'C103007',
        'category': 'FIRE EXTINGUISHER CABINETS',
        'definition': 'This assembly would include all types and sizes of fire extinguisher cabinets. Fire extinguishers are not included in this assembly; they are included in D40.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fire extinguisher cabinets'
    }, {
        'code': 'C103008',
        'category': 'COUNTERS',
        'definition': 'Assemblies include all counters and countertops with all necessary brackets and supporting materials and finish, if required.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of counters'
    }, {
        'code': 'C103009',
        'category': 'CABINETS',
        'definition': 'This assembly includes all cabinetry and millwork items with associated accessories and anchoring devices. Cabinet finishes are included in this assembly. Metal cabinets and special use cabinetry (medical, dental, libraries, etc.) are included in C103010 CASEWORK.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of cabinets'
    }, {
        'code': 'C103010',
        'category': 'CASEWORK',
        'definition': 'Assemblies would include built-in premanufactured cabinetry for specialized functions such as labs, libraries, medical and dental facilities.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of casework'
    }, {
        'code': 'C103011',
        'category': 'CLOSETS',
        'definition': 'This assembly includes all built-in closets with all associated work and finishes. These closets are millwork items or prefabricated coat closets for schools and dormitories.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of closets'
    }, {
        'code': 'C103012',
        'category': 'FIRESTOPPING PENETRATIONS',
        'definition': 'Assembly includes sleeve, caulking, and flashing.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each Penetration'
    }, {
        'code': 'C103013',
        'category': 'SPRAYED FIRE-RESISTIVE MATERIALS',
        'definition': 'Sprayed Fire-Resistive Materials includes materials that are applied primarily to a building\'s framework (columns, beams, bracing, metal decking) to prevent structural failure.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of coverage'
    }, {
        'code': 'C103014',
        'category': 'ENTRANCE FLOOR GRILLES AND MATS',
        'definition': 'Assemblies include floor grilles and mats installed in a fixed arrangement at a building entrance.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of grilles/mats'
    }, {
        'code': 'C103015',
        'category': 'ORNAMENTAL METALWORK',
        'definition': 'Building components made from ornamental metals. Ornamental stair handrails are included in B1010 EXTERIOR STAIRS and C20 STAIRS.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of metalwork items'
    }, {
        'code': 'C103090',
        'category': 'OTHER INTERIOR SPECIALTIES',
        'definition': 'Interior specialties not described by the assembly categories listed above.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of specialty items'
    }, {
        'code': 'C20',
        'category': 'STAIRS',
        'definition': 'Work includes all stair construction.',
        'imperial_units': 'FLT',
        'metric_units': 'FLT',
        'quantity_definition': 'Number of flights'
    }, {
        'code': 'C2010',
        'category': 'STAIR CONSTRUCTION',
        'definition': 'All work items located within the building footprint. A flight of stairs is considered to be all the treads and risers with landings required to travel from one floor to the next.',
        'imperial_units': 'FLT',
        'metric_units': 'FLT',
        'quantity_definition': 'Number of flights'
    }, {
        'code': 'C201001',
        'category': 'INTERIOR AND EXTERIOR STAIRS',
        'definition': 'All stair work items associated with non-fire escape stairs. The stairs can be either interior stairs or stairs exposed to the weather. Exterior stairs are exposed to the outside and do not typically require HVAC. A flight of stairs is considered to be all the treads and risers with landings required to travel from one floor to the next.',
        'imperial_units': 'FLT',
        'metric_units': 'FLT',
        'quantity_definition': 'Number of flights'
    }, {
        'code': 'C201002',
        'category': 'FIRE ESCAPE STAIRS',
        'definition': 'Assemblies include exterior stairs which are used for emergency egress. These stairs are exposed to the weather. Handrails, finishes and associated work items are included in this assembly.',
        'imperial_units': 'FLT',
        'metric_units': 'FLT',
        'quantity_definition': 'Number of flights'
    }, {
        'code': 'C201090',
        'category': 'STAIR HANDRAILS, GUARDRAILS AND ACCESSORIES',
        'definition': 'Stair handrails, guardrails, and cast-in-place nosings for interior and exterior stairs.'
    }, {
        'code': 'C30',
        'category': 'INTERIOR FINISHES',
        'definition': 'Includes wall finishes, floor finishes, and ceiling finishes.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of finishing'
    }, {
        'code': 'C3010',
        'category': 'WALL FINISHES',
        'definition': 'Finishes which are applied to interior wall surfaces. For coatings, refer to C3040.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of finished walls'
    }, {
        'code': 'C301001',
        'category': 'CONCRETE WALL FINISHES',
        'definition': 'This assembly would include a concrete finish applied directly to an interior wall surface. This assembly does not include items that directly apply to wall finishes covered elsewhere in this subsystem.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of finished walls'
    }, {
        'code': 'C301002',
        'category': 'PLASTER WALL FINISHES',
        'definition': 'This assembly includes plaster or stucco applied directly to an interior wall surface. Lath and associated work would be included in this assembly. This assembly does not include items that directly apply to wall finishes covered elsewhere in this subsystem.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of finished walls'
    }, {
        'code': 'C301003',
        'category': 'GYPSUM WALLBOARD FINISHES',
        'definition': 'This assembly includes gypsum wallboard applied directly to an interior wall surface. Furring strips or channels are included in this assembly. This assembly also includes taping, sanding, finishing, and sheetrock accessories. This assembly does not include items that directly apply to wall finishes covered elsewhere in this subsystem.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of finished walls'
    }, {
        'code': 'C301004',
        'category': 'TILE & TERRAZZO WALL FINISHES',
        'definition': 'This assembly includes tile and terrazzo applied directly to an interior wall surface. Each type of tile would be a separate assembly.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of finished walls'
    }, {
        'code': 'C301005',
        'category': 'WALL COVERINGS',
        'definition': 'This assembly includes wall coverings and protective strips applied directly to an interior wall surface.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of wall coverings'
    }, {
        'code': 'C301006',
        'category': 'ACOUSTICAL PANELS ADHERED TO WALLS',
        'definition': 'This assembly includes acoustical tiles and panels with associated work applied directly to an interior wall surface.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of acoustical tiles and panels'
    }, {
        'code': 'C301090',
        'category': 'OTHER WALL FINISHES',
        'definition': 'Assemblies include finishes to wall types not included above. These include, but are not limited to, different types of shielding and the work and materials associated with each.'
    }, {
        'code': 'C3020',
        'category': 'FLOOR FINISHES',
        'definition': 'All flooring and floor finishes applied to interior floors. For coatings refer to C3040.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of finished floors'
    }, {
        'code': 'C302001',
        'category': 'TILE FLOOR FINISHES',
        'definition': 'Assemblies include ceramic, quarry, and other non-resilient tile floors.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of tile floors'
    }, {
        'code': 'C302002',
        'category': 'TERRAZZO FLOOR FINISHES',
        'definition': 'Assemblies include terrazzo floors.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of terrazzo floors'
    }, {
        'code': 'C302003',
        'category': 'WOOD FLOORING',
        'definition': 'Assemblies include wood floors.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of wood floors'
    }, {
        'code': 'C302004',
        'category': 'RESILIENT FLOOR FINISHES',
        'definition': 'Assemblies include resilient floors.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of resilient floors'
    }, {
        'code': 'C302005',
        'category': 'CARPETING',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of carpeting'
    }, {
        'code': 'C302006',
        'category': 'MASONRY & STONE FLOORING',
        'definition': 'Assemblies include masonry, concrete pavers, and stone flooring.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of masonry or stone flooring'
    }, {
        'code': 'C302007',
        'category': 'WALL BASE FINISHES',
        'definition': 'Assemblies include wall base, consisting of various materials such as vinyl, ceramic tile, etc.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of wall base'
    }, {
        'code': 'C302008',
        'category': 'STAIR FINISHES',
        'definition': 'Includes field-applied finish materials (other than paint) to surfaces of stairs including treads, risers and landings.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of coverage'
    }, {
        'code': 'C302009',
        'category': 'FLOOR TOPPINGS AND TRAFFIC MEMBRANES',
        'definition': 'Assemblies include floor toppings and membrane systems.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of coverage'
    }, {
        'code': 'C302010',
        'category': 'HARDENERS AND SEALERS',
        'definition': 'Assemblies include floor hardeners and sealers, typically applied on concrete floors.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of coverage'
    }, {
        'code': 'C302011',
        'category': 'RAISED ACCESS FLOORING',
        'definition': 'Assemblies include all types of raised flooring, pedestal access floors and other types of access flooring.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of special flooring'
    }, {
        'code': 'C302090',
        'category': 'OTHER FLOORING & FLOOR FINISHES',
        'definition': 'Assemblies include floor finishes not described by the assembly categories listed above, such as conductive, armored, etc.'
    }, {
        'code': 'C3030',
        'category': 'CEILING FINISHES',
        'definition': 'All ceilings and ceiling finishes applied to interiors. For coatings, refer to C3040.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of ceilings'
    }, {
        'code': 'C303001',
        'category': 'ACOUSTICAL CEILING TILES & PANELS',
        'definition': 'Assemblies include acoustical ceiling tiles and panels. The suspension system, if required, is in Assembly Category C303005. This assembly does not include items that directly apply to ceiling finishes covered elsewhere in this subsystem.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of acoustical ceilings'
    }, {
        'code': 'C303002',
        'category': 'GYPSUM WALLBOARD CEILING FINISHES',
        'definition': 'Assemblies include gypsum wallboard applied to interior ceilings. Furring strips or channels are included in this assembly if they are applied directly to the ceiling surface. If the gypsum board is applied to a suspended ceiling system, the suspended system would be in Assembly Category C303005. This assembly does not include items that directly apply to ceiling finishes covered elsewhere in this subsystem.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of gypsum ceilings'
    }, {
        'code': 'C303003',
        'category': 'PLASTER CEILING FINISHES',
        'definition': 'Assemblies include plaster or stucco finishes applied to interior ceilings. Lath and associated work would apply to this assembly. This assembly does not include items that directly apply to ceiling finishes covered elsewhere in this subsystem.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of plaster ceiling finish'
    }, {
        'code': 'C303004',
        'category': 'WOOD CEILINGS',
        'definition': 'Assemblies include wood ceilings. Different types of wood ceilings should be separated into different assemblies. If the wood ceiling is applied to a suspended ceiling system, the suspended system would be in Assembly Category C303005. This assembly does not include items that directly apply to ceiling finishes covered elsewhere in this subsystem.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of wood ceilings'
    }, {
        'code': 'C303005',
        'category': 'SUSPENSIONS SYSTEMS',
        'definition': 'This assembly includes any suspension system which is suspended or hung from the structure for the purpose of fastening a ceiling.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of suspension system'
    }, {
        'code': 'C303006',
        'category': 'METAL STRIP CEILINGS',
        'definition': 'Assemblies include all metal strip materials applied to ceilings.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of metal ceiling'
    }, {
        'code': 'C303090',
        'category': 'OTHER CEILING & CEILING FINISHES',
        'definition': 'Special ceilings and ceiling finishes not described by the assembly categories listed above.'
    }, {
        'code': 'C3040',
        'category': 'INTERIOR COATINGS AND SPECIAL FINISHES',
        'definition': 'This assembly includes surface preparation and application of coatings to interior surfaces.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of interior coatings'
    }, {
        'code': 'C304001',
        'category': 'GENERAL REQUIREMENTS',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of coatings and finishes'
    }, {
        'code': 'C304002',
        'category': 'CONCRETE FINISHES',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of concrete finishes'
    }, {
        'code': 'C304003',
        'category': 'CONCRETE MASONRY FINISHES',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of concrete masonry finishes'
    }, {
        'code': 'C304004',
        'category': 'METAL FINISHES',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of metal finishes'
    }, {
        'code': 'C304005',
        'category': 'INTERIOR WOOD FINISHES',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of wood finishes'
    }, {
        'code': 'C304006',
        'category': 'GYPSUM WALLBOARD FINISHES',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of gypsum wallboard coatings'
    }, {
        'code': 'C304007',
        'category': 'SPECIAL COATINGS ON WALLS',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of special wall coatings'
    }, {
        'code': 'D',
        'category': 'SERVICES',
        'definition': 'Includes all methods of conveying, plumbing, HVAC, fire protection, and electrical.',
        'imperial_units': 'EA',
        'metric_units': 'EA'
    }, {
        'code': 'D10',
        'category': 'CONVEYING',
        'definition': 'This system includes elevators, escalators, pneumatic tube systems, conveyors, chutes, etc. Foundations for these systems are included in System A, Substructure.',
        'imperial_units': 'STY',
        'metric_units': 'STY',
        'quantity_definition': 'Number of stories'
    }, {
        'code': 'D1010',
        'category': 'ELEVATORS AND LIFTS',
        'definition': 'Includes passenger elevators and freight elevators.',
        'imperial_units': 'STP',
        'metric_units': 'STP',
        'quantity_definition': 'Number of stops'
    }, {
        'code': 'D101001',
        'category': 'GENERAL CONSTRUCTION ITEMS',
        'definition': 'Includes construction work, other than conveying system work, which must be performed in conjunction with this type of work to complete the system.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of items'
    }, {
        'code': 'D101002',
        'category': 'PASSENGER ELEVATORS',
        'definition': 'The unit measure at the assembly level is each stop.',
        'imperial_units': 'STP',
        'metric_units': 'STP',
        'quantity_definition': 'Number of stops'
    }, {
        'code': 'D101003',
        'category': 'FREIGHT ELEVATORS',
        'definition': 'The unit measure at the assembly level is each stop.',
        'imperial_units': 'STP',
        'metric_units': 'STP',
        'quantity_definition': 'Number of stops'
    }, {
        'code': 'D101004',
        'category': 'WHEELCHAIR LIFT',
        'definition': 'Premanufactured lift to gain wheelchair access.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of lifts'
    }, {
        'code': 'D101005',
        'category': 'DUMBWAITERS',
        'definition': 'The unit measure of the assembly is each stop.',
        'imperial_units': 'STP',
        'metric_units': 'STP',
        'quantity_definition': 'Number of stops'
    }, {
        'code': 'D101090',
        'category': 'OTHER VERTICAL TRANSPORTATION EQUIPMENT',
        'definition': 'This includes elevators not described by the assembly categories listed above, such as people lifts.'
    }, {
        'code': 'D1020',
        'category': 'WEIGHT HANDLING EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of items'
    }, {
        'code': 'D102001',
        'category': 'BASIC REQUIREMENTS OF CRANES AND MONORAILS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of items'
    }, {
        'code': 'D102002',
        'category': 'OVERHEAD CRANES',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of items'
    }, {
        'code': 'D102003',
        'category': 'MONORAILS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of items'
    }, {
        'code': 'D1030',
        'category': 'ESCALATORS AND MOVING WALKS',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of stairs or walks'
    }, {
        'code': 'D103001',
        'category': 'ESCALATORS',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of stairs'
    }, {
        'code': 'D103002',
        'category': 'MOVING WALKS',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of walks'
    }, {
        'code': 'D103090',
        'category': 'OTHER MOVING STAIRS & WALKS',
        'definition': 'Moving stairs or walks not described by the assembly categories listed above.'
    }, {
        'code': 'D1090',
        'category': 'OTHER CONVEYING SYSTEMS',
        'definition': 'Other conveying systems includes pneumatic tube systems, conveyor belts, chutes, and transportation systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of systems'
    }, {
        'code': 'D109001',
        'category': 'PNEUMATIC TUBE SYSTEMS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of systems'
    }, {
        'code': 'D109002',
        'category': 'CONVEYORS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of material handling systems'
    }, {
        'code': 'D109003',
        'category': 'LINEN, TRASH, AND MAIL CHUTES',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of chute'
    }, {
        'code': 'D109004',
        'category': 'TURNTABLES',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of turntables'
    }, {
        'code': 'D109005',
        'category': 'OPERABLE SCAFFOLDING',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of scaffolding'
    }, {
        'code': 'D109006',
        'category': 'TRANSPORTATION SYSTEMS',
        'definition': 'This assembly includes baggage handling and aircraft loading systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of systems'
    }, {
        'code': 'D109090',
        'category': 'OTHER MATERIAL HANDLING SYSTEMS',
        'definition': 'Material or handling systems not described by the assembly categories listed above.'
    }, {
        'code': 'D20',
        'category': 'PLUMBING',
        'definition': 'The plumbing system\'s primary function is the transfer of liquids and gases. This system includes all water supply and waste items within the building.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D2010',
        'category': 'PLUMBING FIXTURES',
        'definition': 'All terminal devices on the domestic plumbing system which have water supplied to the fixture. Hot water heaters, hose bibbs, and special equipment are not counted as a fixture.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D201001',
        'category': 'WATERCLOSETS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D201002',
        'category': 'URINALS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D201003',
        'category': 'LAVATORIES',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D201004',
        'category': 'SINKS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D201005',
        'category': 'SHOWERS/TUBS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D201006',
        'category': 'DRINKING FOUNTAINS & COOLERS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D201007',
        'category': 'BIDETS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D201090',
        'category': 'EMERGENCY FIXTURES',
        'definition': 'Emergency fixtures not described by the assembly categories listed above.'
    }, {
        'code': 'D2020',
        'category': 'DOMESTIC WATER DISTRIBUTION',
        'definition': 'This system provides for human health and comfort. The water supply needed is determined by the number of fixtures attached. Hot water heaters, hose bibbs, and special equipment are not counted as a fixture.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D202001',
        'category': 'PIPES & FITTINGS',
        'definition': 'Assemblies include all pipe, fittings, and associated work with regard to domestic water supply. The unit of measure at the assembly level is number of fixtures.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D202002',
        'category': 'VALVES & HYDRANTS',
        'definition': 'Assemblies include all valves and hydrants. Hose bibbs are included in this assembly. The unit of measure at the assembly level is number of valves and hydrants.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of valves and hydrants'
    }, {
        'code': 'D202003',
        'category': 'DOMESTIC WATER EQUIPMENT',
        'definition': 'This assembly includes equipment associated with the domestic water supply, including fittings, and specialties required for hook-up. Assemblies include hot water heaters, water treatment plant, i.e., water softeners, filters, distillers, etc.; pumps directly associated with domestic water supply; and tanks for the potable hot or cold water system. The unit of measure at the assembly level is pieces of equipment.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D202004',
        'category': 'INSULATION & IDENTIFICATION',
        'definition': 'Assemblies include insulation used in association with domestic water supply. The unit of measure at the assembly level is number of fixtures.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D202005',
        'category': 'SPECIALTIES',
        'definition': 'Any other special items associated with domestic water supply. All associated work items, including pipes, fittings, valves, insulation, and hook-up should be included in this assembly. The unit of measure at the assembly level is pieces of special equipment.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'D202090',
        'category': 'OTHER DOMESTIC WATER SUPPLY',
        'definition': 'Domestic water supply not described by the assembly categories listed above.'
    }, {
        'code': 'D2030',
        'category': 'SANITARY WASTE',
        'definition': 'This system provides for human health and comfort. Fixtures include all terminal devices which have a water supply (except water supply equipment and specialties), and also devices that transfer fluids into the sanitary waste system that do not have a water supply. Floor drains (not drain hubs) are included as a sanitary waste fixture.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D203001',
        'category': 'WASTE PIPE & FITTINGS',
        'definition': 'Assemblies include all pipe, fittings, and associated work with regard to sanitary waste pipe and fittings. The unit of measure at the assembly level is number of fixtures.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D203002',
        'category': 'VENT PIPE & FITTINGS',
        'definition': 'Assemblies include all pipe, fittings, and associated work with regard to sanitary vent pipe and fittings. The unit of measure at the assembly level is number of fixtures.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D203003',
        'category': 'FLOOR DRAINS',
        'definition': 'Assemblies include all floor drains. Hub drains are considered to be pipe and are not included in this category. The unit of measure at the assembly level is number of drains.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of floor drains'
    }, {
        'code': 'D203004',
        'category': 'SANITARY AND VENT EQUIPMENT',
        'definition': 'This is equipment associated with the sanitary waste system, including fittings and specialties required for hook-up. Assemblies include waste treatment equipment, i.e., sluice gates, incinerators, etc.; pumps for sewage injection; and holding tanks for the domestic water system. The unit of measure at the assembly level is pieces of equipment.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D203005',
        'category': 'INSULATION & IDENTIFICATION',
        'definition': 'Assemblies include insulation used in association with sanitary waste and vent system. The unit of measure at the assembly level is number of fixtures.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'D203090',
        'category': 'OTHER SANITARY WASTE',
        'definition': 'Sanitary waste and vent not described by the assembly categories listed above.'
    }, {
        'code': 'D2040',
        'category': 'RAIN WATER DRAINAGE',
        'definition': 'Roof drainage system. Gutter and downspouts are not included in this subsystem.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of roof'
    }, {
        'code': 'D204001',
        'category': 'PIPE & FITTINGS',
        'definition': 'Assemblies include pipe and fittings from the roof drains to the discharge points, including supports and other associated work.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of pipe'
    }, {
        'code': 'D204002',
        'category': 'ROOF DRAINS',
        'definition': 'Assemblies include roof drains. The unit of measure at the assembly level is number of drains.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of roof drains'
    }, {
        'code': 'D204003',
        'category': 'RAINWATER DRAINAGE EQUIPMENT',
        'definition': 'This is equipment associated with the rain water drainage, including fittings and specialties required for hook-up. Assemblies include pumps and other associated items for drainage of rain water.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'D204004',
        'category': 'INSULATION & IDENTIFICATION',
        'definition': 'Assemblies include insulation used in association with rain water drainage system.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of pipe insulation'
    }, {
        'code': 'D204090',
        'category': 'OTHER RAIN WATER DRAINAGE SYSTEM',
        'definition': 'Rain water drainage system not described by the assembly categories listed above.'
    }, {
        'code': 'D2090',
        'category': 'OTHER PLUMBING SYSTEMS',
        'definition': 'This subsystem includes all special plumbing systems which are not included in D2010 through D2040.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of special fixtures, etc.'
    }, {
        'code': 'D209001',
        'category': 'SPECIAL PIPING SYSTEMS',
        'definition': 'Assemblies include all special pipe and fittings, excluding acid waste pipe and work with regard to special pipe. Medical gas and vacuum fittings, and associated systems piping are included in this category. The unit of measure at the assembly level is the number of special fixtures, interceptors, outlets, or systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of special fixtures, interceptors, etc.'
    }, {
        'code': 'D209002',
        'category': 'ACID WASTE SYSTEMS',
        'definition': 'Assemblies include all pipe, fittings, special acid waste equipment, and other associated work items with regard to acid waste systems. The unit of measure at the assembly level is the number of special fixtures, interceptors, outlets, or systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of special fixtures, interceptors, etc.'
    }, {
        'code': 'D209003',
        'category': 'INTERCEPTORS',
        'definition': 'Assemblies include all interceptors. The unit of measure at the assembly level is number of interceptors.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of interceptors'
    }, {
        'code': 'D209004',
        'category': 'POOL PIPING AND EQUIPMENT',
        'definition': 'Assemblies include pumps and associated equipment with pools, including specialties required for hook-up. The unit of measure at the assembly level is each.',
        'imperial_units': 'GPM',
        'metric_units': 'M3/S',
        'quantity_definition': 'Gallons per minute'
    }, {
        'code': 'D209005',
        'category': 'COMPRESSED AIR SYSTEM (NON-BREATHING)',
        'imperial_units': 'PSI',
        'metric_units': 'KGM2',
        'quantity_definition': 'Pounds per square inch'
    }, {
        'code': 'D209090',
        'category': 'OTHER SPECIAL PLUMBING SYSTEMS',
        'definition': 'This system includes special plumbing systems not described by the assembly categories listed above, such as fountain piping systems and devices.'
    }, {
        'code': 'D30',
        'category': 'HVAC',
        'definition': 'This system includes all equipment, distribution systems, controls, and energy supply systems required by the heating, ventilating, and air conditioning system.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Total MBH capacity'
    }, {
        'code': 'D3010',
        'category': 'ENERGY SUPPLY',
        'definition': 'The energy input to the facility (other than electrical) in the form of fuels or hot and cold water distributed from a central base facility. Energy received from wind or solar power is included in this subsystem.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Total power of heating system'
    }, {
        'code': 'D301001',
        'category': 'OIL SUPPLY SYSTEM',
        'definition': 'Assemblies include storage equipment, transfer equipment, and distribution piping. The unit of measure at the assembly level is each system.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Calories per gallon'
    }, {
        'code': 'D301002',
        'category': 'GAS SUPPLY SYSTEM',
        'definition': 'This category includes both natural gas and LPG. Assemblies include metering and regulation equipment, storage equipment, transfer equipment, and distribution piping. The unit of measure at the assembly level is each system.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'MBH'
    }, {
        'code': 'D301003',
        'category': 'STEAM SUPPLY SYSTEM (FROM CENTRAL PLANT)',
        'definition': 'Assemblies include meters, valves, heat exchangers, fittings, and specialties required for hook-up and distribution piping, including supports, sleeves, and insulation. The unit of measure at the assembly level is each system.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D301004',
        'category': 'HOT WATER SUPPLY SYSTEM (FROM CENTRAL PLANT)',
        'definition': 'Assemblies include meters, valves, heat exchangers, fittings, and specialties required for hook-up and distribution piping, including supports, sleeves, and insulation. The unit of measure at the assembly level is each system.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D301005',
        'category': 'SOLAR ENERGY SUPPLY SYSTEMS',
        'definition': 'Assemblies include collector panels, heat exchangers, storage tanks, pumps, etc., including pipe and fittings required for hook-up. The unit of measure at the assembly level is each system.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each System'
    }, {
        'code': 'D301006',
        'category': 'WIND ENERGY SUPPLY SYSTEM',
        'definition': 'Wind is used to turn a generator which generates electricity. This energy is either stored in a battery or used to generate hot water in an electric boiler. Assemblies would include the required devices to make this a total electromechanical system. The unit of measure at the assembly level is each system.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each System'
    }, {
        'code': 'D301007',
        'category': 'COAL SUPPLY SYSTEM',
        'definition': 'This category includes storage equipment, transfer equipment, processing equipment, and distribution piping. The unit of measure at the assembly level is each system.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D301090',
        'category': 'OTHER ENERGY SUPPLY',
        'definition': 'Energy supply not described by the assembly categories listed above.'
    }, {
        'code': 'D3020',
        'category': 'HEAT GENERATING SYSTEMS',
        'definition': 'This subsystem includes steam, hot water, furnace, and unit heater systems. Fuels include coal, oil, gas and electric unless otherwise noted.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Total power of heating system'
    }, {
        'code': 'D302001',
        'category': 'BOILERS',
        'definition': 'Assemblies include steam or hot water boilers, expansion tanks, chemical feeders, air separators, pumps, heat exchangers, boiler feed units, etc. This assembly would also include fittings and specialties and the flue stack. The unit of measure at the assembly level is each system.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D302002',
        'category': 'FURNACES',
        'definition': 'This is a system that heats air. Assemblies would include furnace and necessary fittings and specialties required for hook-up, including flue and stack. The unit of measure at the assembly level is each.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D302003',
        'category': 'FUEL-FIRED UNIT HEATERS',
        'definition': 'Assemblies would include unit heaters and the energy supply system hook-up (other than electrical), including all necessary pipe, fittings, and specialties required for hook-up. Flue and stack, if required, are included in this assembly. The unit of measure at the assembly level is each.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D302004',
        'category': 'AUXILIARY EQUIPMENT',
        'definition': 'Assemblies would include any other equipment associated with heat generating systems. The unit of measure at the assembly level is each.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D302005',
        'category': 'EQUIPMENT THERMAL INSULATION',
        'definition': 'Assemblies would include insulation of any component in this subsystem. The unit of measure at the assembly level is each.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of insulation'
    }, {
        'code': 'D302090',
        'category': 'OTHER HEAT GENERATING SYSTEMS',
        'definition': 'Heat generating systems not described in the assembly categories listed above.'
    }, {
        'code': 'D3030',
        'category': 'COOLING GENERATING SYSTEMS',
        'definition': 'Cooling generating equipment of the absorption, centrifugal, reciprocating, and direct expansion types.',
        'imperial_units': 'TON',
        'metric_units': 'KW',
        'quantity_definition': 'Total power of cooling capacity'
    }, {
        'code': 'D303001',
        'category': 'CHILLED WATER SYSTEMS',
        'definition': 'Assemblies include condensers, compressors, chillers, pumps, cooling towers, etc., including fittings and specialties required for hook-up. The unit of measure at the assembly level is each.',
        'imperial_units': 'TON',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D303002',
        'category': 'DIRECT EXPANSION SYSTEMS',
        'definition': 'Assemblies include condensers, compressors, heat pumps, and refrigerant piping. The unit of measure at the assembly level is each.',
        'imperial_units': 'TON',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D303090',
        'category': 'OTHER COOLING GENERATING SYSTEMS',
        'definition': 'Cooling generating systems not described by the assembly categories listed above.'
    }, {
        'code': 'D3040',
        'category': 'DISTRIBUTION SYSTEMS',
        'definition': 'This includes systems that distribute heated and cooled air, ventilating and exhaust air, hot and chilled water, steam, and glycol heating.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D304001',
        'category': 'AIR DISTRIBUTION, HEATING & COOLING',
        'definition': 'Assemblies include heating coils, cooling coils, and fittings and specialties required for water hook-up. This assembly also includes duct heaters, filters, humidifiers, supply and return ductwork, dampers, fire dampers, supply and return grilles, registers and diffusers, turning vanes, sound traps, and all associated insulation. The unit of measure at the assembly level is MCFM.',
        'imperial_units': 'MCFM',
        'metric_units': 'L/S',
        'quantity_definition': 'Volume of air flow'
    }, {
        'code': 'D304002',
        'category': 'STEAM DISTRIBUTION SYSTEMS',
        'definition': 'Assemblies include pipe and fittings, supports, wall and floor sleeves, and pipe insulation. The unit of measure at the assembly level is MBH.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D304003',
        'category': 'HOT WATER DISTRIBUTION SYSTEMS',
        'definition': 'Assemblies include pipe and fittings, supports, wall and floor sleeves, and pipe insulation. The unit of measure at the assembly level is MBH.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D304004',
        'category': 'CHANGE OVER DISTRIBUTION SYSTEMS',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D304005',
        'category': 'GLYCOL DISTRIBUTION SYSTEMS',
        'definition': 'Assemblies include pipe and fittings, supports, wall and floor sleeves, and pipe insulation. The unit of measure at the assembly level is MBH.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D304006',
        'category': 'CHILLED WATER DISTRIBUTION SYSTEMS',
        'definition': 'Assemblies include pipe and fittings, supports, wall and floor sleeves, and pipe insulation. The unit of measure at the assembly level is tons.',
        'imperial_units': 'TON',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D304007',
        'category': 'EXHAUST SYSTEMS',
        'definition': 'Assemblies include ductwork grilles, registers, diffusers, fans, and all associated work. The unit of measure at the assembly level is each system.',
        'imperial_units': 'MCF',
        'metric_units': 'L/S',
        'quantity_definition': 'Volume of air flow'
    }, {
        'code': 'D304008',
        'category': 'AIR HANDLING UNITS',
        'imperial_units': 'MCFM',
        'metric_units': 'L/S',
        'quantity_definition': 'Volume of air flow'
    }, {
        'code': 'D304090',
        'category': 'OTHER DISTRIBUTION SYSTEMS',
        'definition': 'Distribution systems not described by the assembly categories listed above.'
    }, {
        'code': 'D3050',
        'category': 'TERMINAL & PACKAGE UNITS',
        'definition': 'This category includes self-contained heating and cooling units.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D305001',
        'category': 'UNIT VENTILATORS',
        'definition': 'Assemblies include the complete terminal unit and wall sleeve with all controls.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of units'
    }, {
        'code': 'D305002',
        'category': 'UNIT HEATERS',
        'definition': 'Assemblies include the complete terminal unit and wall sleeve with all controls.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of units'
    }, {
        'code': 'D305003',
        'category': 'FAN COIL UNITS',
        'definition': 'Assemblies include the complete terminal unit and wall sleeve with all controls.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of units'
    }, {
        'code': 'D305004',
        'category': 'FIN TUBE RADIATION',
        'definition': 'Assemblies include the complete terminal unit and wall sleeve with all controls.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of units'
    }, {
        'code': 'D305005',
        'category': 'ELECTRIC HEATING',
        'definition': 'Assemblies include the complete terminal unit and wall sleeve with all controls.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of units'
    }, {
        'code': 'D305006',
        'category': 'PACKAGE UNITS',
        'definition': 'Assemblies include complete package units, with integral roof top curbs and all associated devices. A heating system can be selected from hot water, steam coil, or gas furnace and can be a single or multi-zone system. The unit of measure at the assembly level is each.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of units'
    }, {
        'code': 'D305090',
        'category': 'OTHER TERMINAL & PACKAGE UNITS',
        'definition': 'Terminal and package units not described by the assembly categories listed above.'
    }, {
        'code': 'D3060',
        'category': 'CONTROLS & INSTRUMENTATION',
        'definition': 'Includes devices such as thermostats, timers, sensors, control valves, etc., necessary to operate the system as designed.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D306001',
        'category': 'HVAC CONTROLS',
        'definition': 'Includes devices such as thermostats, timers, sensors, control valves, etc., necessary to operate the total system. The unit of measure at the assembly level is each system.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Power'
    }, {
        'code': 'D306002',
        'category': 'ELECTRONIC CONTROLS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of devices'
    }, {
        'code': 'D306003',
        'category': 'PNEUMATIC CONTROLS',
        'definition': 'Assemblies includes ball and butterfly valves, actuators, high pressure chokes, valve positioners, sensors, regulators, etc.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of devices'
    }, {
        'code': 'D306004',
        'category': 'INSTRUMENT AIR COMPRESSORS',
        'definition': 'Assemblies include air compressors, dryers, and distribution tubing, (only used with pneumatic control systems). The unit of measure at the assembly level is each.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of compressors'
    }, {
        'code': 'D306005',
        'category': 'GAS PURGING SYSTEMS',
        'definition': 'Assemblies include the removal of contaminated or unwanted gases from a structure or pipe.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of systems'
    }, {
        'code': 'D306090',
        'category': 'OTHER CONTROLS INSTRUMENTATION',
        'definition': 'Controls and instrumentation not described by the assembly categories listed above.'
    }, {
        'code': 'D3070',
        'category': 'SYSTEMS TESTING & BALANCING',
        'definition': 'This includes operation of all systems to determine capacity and adjustment of water flow in chilled water and hot water systems, air flow of air handling units, supply and exhaust fans, and supply and return, and exhaust registers.',
        'imperial_units': 'MBH',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D307001',
        'category': 'WATER SIDE TESTING & BALANCING - HEATING & COOLING',
        'definition': 'Includes operating and testing of pumps, setting of all control valves, and determining system capacity. The unit of measure at the assembly level is each device, i.e., boiler, chiller, fan coil, and unit heater.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of devices'
    }, {
        'code': 'D307002',
        'category': 'AIR SIDE TESTING & BALANCING - HEATING, COOLING & EXHAUST',
        'definition': 'Includes operating and testing of all air handling devices, adjusting of all fans to set rate of air flow, setting all fan motors at desired operation, setting of air flow at all registers, grilles, diffusers, and louvers to deliver design CFM, and testing and calibrating of thermostats to achieve desired space temperature. The unit of measure at the assembly level is each device.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of devices'
    }, {
        'code': 'D307003',
        'category': 'HVAC COMMISSIONING',
        'definition': 'Final testing of operational system.',
        'imperial_units': 'LS',
        'metric_units': 'LS',
        'quantity_definition': 'Lump sum'
    }, {
        'code': 'D307090',
        'category': 'OTHER SYSTEMS TESTING & BALANCING',
        'definition': 'Systems testing and balancing not described by the assembly categories listed above.'
    }, {
        'code': 'D3090',
        'category': 'OTHER HVAC SYSTEMS AND EQUIPMENT',
        'definition': 'This subsystem includes special mechanical systems that are not normally included as part of standard HVAC systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of special mechanical systems'
    }, {
        'code': 'D309001',
        'category': 'GENERAL CONSTRUCTION ITEMS',
        'definition': 'Includes construction work other than mechanical which must be performed in conjunction with the special mechanical system to make the system complete.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of special system'
    }, {
        'code': 'D309002',
        'category': 'REFRIGERATION SYSTEMS',
        'definition': 'Includes equipment for refrigeration in a cold storage facility. Both low and medium temperature equipment are included. Assemblies include: condensing and compressor units, evaporator blowers, refrigerant piping, and specialties, heat recovery systems (liquid or gas), heat recovery distribution systems (liquid or gas), and system testing and balancing.',
        'imperial_units': 'TON',
        'metric_units': 'KW',
        'quantity_definition': 'Power'
    }, {
        'code': 'D309090',
        'category': 'OTHER SPECIAL MECHANICAL SYSTEMS',
        'definition': 'Any other mechanical system not defined in other categories. Assemblies would include special systems and special devices. The unit of measure at the assembly level is each system or device.'
    }, {
        'code': 'D40',
        'category': 'FIRE PROTECTION',
        'definition': 'This system includes standard and special fire protection systems. Fire alarm systems are included in D503001.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'D4010',
        'category': 'FIRE ALARM AND DETECTION SYSTEMS',
        'definition': 'Assemblies include wire, conduit, conduit support or fastening systems, fire alarm devices, fire detection devices, safety switches, mass notification, all electrical connections and other associated items.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'D401001',
        'category': 'FIRE ALARM DISTRIBUTION',
        'definition': 'Wire, conduit, conduit support or fastening systems, switches and connections.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'D401002',
        'category': 'FIRE ALARM DEVICES',
        'definition': 'Fire alarm and fire detection devices',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of devices'
    }, {
        'code': 'D4020',
        'category': 'FIRE SUPPRESSION WATER SUPPLY AND EQUIPMENT',
        'definition': 'Requirements for water supply design criteria and any items located upstream of the suppression systems such as PIV\'s, backflow preventers, strainers, etc. The water supply distribution system begins 5\'-0" outside the building.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'D402001',
        'category': 'FIRE PROTECTION WATER PIPING AND EQUIPMENT',
        'definition': 'Piping',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'D402002',
        'category': 'FIRE PUMP',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of pumps'
    }, {
        'code': 'D4030',
        'category': 'STANDPIPE SYSTEMS',
        'definition': 'This subsystem includes the complete standpipe system.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of sprinkler heads'
    }, {
        'code': 'D403001',
        'category': 'STANDPIPE EQUIPMENT & PIPING',
        'definition': 'Assemblies include standpipe risers and all other piping, fittings, and supports associated with this category. Siamese connections, roof manifolds, cabinets, hoses, racks, and other fire department connections are included in this assembly. All equipment including pumps, tanks, etc., with all required fittings and specialties for hook-up are included in this assembly.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of sprinkler heads'
    }, {
        'code': 'D4040',
        'category': 'SPRINKLERS',
        'definition': 'This subsystem includes the water supply equipment and related piping from the equipment to the sprinkler head.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of sprinkler heads'
    }, {
        'code': 'D404001',
        'category': 'SPRINKLERS AND RELEASING DEVICES',
        'definition': 'The fixture, device, or sprinkler head that releases the water to suppress the fire. The unit of measure at the assembly level is each sprinkler head.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of sprinkler heads'
    }, {
        'code': 'D404002',
        'category': 'SPRINKLER WATER SUPPLY EQUIPMENT AND PIPING',
        'definition': 'Assemblies include alarm valves, flow control valves, pipe and fittings from equipment to sprinkler heads, including all supports and wall or floor sleeves. All equipment including tanks, pumps, and other associated equipment, fittings and specialties required for hook-up are in this assembly. The unit of measure at the assembly level is each sprinkler head.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of sprinkler heads'
    }, {
        'code': 'D4050',
        'category': 'FIRE PROTECTION SPECIALTIES',
        'definition': 'This subsystem includes fire extinguishing devices.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of extinguishers'
    }, {
        'code': 'D405001',
        'category': 'PORTABLE EXTINGUISHERS',
        'definition': 'Assemblies include all types of fire extinguishers, i.e., water, dry chemical, carbon dioxide, soda acid, etc. The brackets, sleeves, and supporting devices are included in this assembly.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of extinguishers'
    }, {
        'code': 'D4090',
        'category': 'OTHER FIRE PROTECTION SYSTEMS',
        'definition': 'Requirements for all other suppression systems. Water based systems (e.g., foam systems) specified from water supply onwards, complete specification for gas systems, incidental systems such as kitchen hood systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each system'
    }, {
        'code': 'D409001',
        'category': 'CARBON DIOXIDE SYSTEMS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of systems'
    }, {
        'code': 'D409002',
        'category': 'FOAM GENERATING EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'D409003',
        'category': 'CLEAN AGENT SYSTEMS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of systems'
    }, {
        'code': 'D409004',
        'category': 'HOOD & DUCT FIRE PROTECTION',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'D409090',
        'category': 'OTHER SPECIAL FIRE PROTECTION SYSTEMS',
        'definition': 'Assemblies includes other fire protection systems such as halon systems, exhaust hood systems, and special chemical suppression systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each system'
    }, {
        'code': 'D50',
        'category': 'ELECTRICAL',
        'definition': 'This system is defined by the electric current used or regarded as a source of power.',
        'imperial_units': 'AMP',
        'metric_units': 'AMP',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'D5010',
        'category': 'ELECTRICAL SERVICE & DISTRIBUTION',
        'definition': 'This subsystem provides for all electrical devices that are required to deliver the main source of power to the facility and to distribute this power to subpanels.',
        'imperial_units': 'AMP',
        'metric_units': 'AMP',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'D501001',
        'category': 'MAIN TRANSFORMERS',
        'definition': 'Transformers used for primary electrical service and located within the building footprint. Assemblies include transformers, raised pad, trenching, and backfill. This assembly will not likely be used when an exterior transformer is required in G4010 ELECTRICAL DISTRIBUTION.',
        'imperial_units': 'AMP',
        'metric_units': 'AMP',
        'quantity_definition': 'Number of transformers'
    }, {
        'code': 'D501002',
        'category': 'SERVICE ENTRANCE EQUIPMENT',
        'definition': 'This includes the protection equipment and metering devices for main distribution. Assemblies include main distribution panel, breaker, fuses, and meters.',
        'imperial_units': 'AMP',
        'metric_units': 'AMP',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'D501003',
        'category': 'INTERIOR DISTRIBUTION TRANSFORMERS',
        'definition': 'Transformers fed downstream of the service entrance equipment. Assemblies include transformers, conduit, conduit support, and wire.',
        'imperial_units': 'AMP',
        'metric_units': 'AMP',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'D501004',
        'category': 'PANELBOARDS',
        'definition': 'Branch circuit panelboards. Assemblies include panelboards, breakers ,conduit, and wire.',
        'imperial_units': 'AMP',
        'metric_units': 'AMP',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'D501005',
        'category': 'ENCLOSED CIRCUIT BREAKERS',
        'definition': 'Over-current protection device enclosed in its own housing. Assemblies include enclosed circuit breaker, conduit, and wire.',
        'imperial_units': 'AMP',
        'metric_units': 'AMP',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'D501006',
        'category': 'MOTOR CONTROL CENTERS',
        'definition': 'This is a cabinet in which motor starters and operation devices are contained. Assemblies include the motor control center cabinet, motor starters, contacts, switches, conduit, wire, and all associated items.',
        'imperial_units': 'AMP',
        'metric_units': 'AMP',
        'quantity_definition': 'Gross floor area'
    }, {
        'code': 'D501090',
        'category': 'OTHER SERVICE AND DISTRIBUTION',
        'definition': 'Service and distribution not described by the assembly categories listed above.'
    }, {
        'code': 'D5020',
        'category': 'LIGHTING & BRANCH WIRING',
        'definition': 'Lighting systems including light fixtures and devices, i.e., switches, receptacles, and equipment connections.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'D502001',
        'category': 'BRANCH WIRING',
        'definition': 'This assembly includes switches, receptacles, equipment connections, conduit, and wire.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'D502002',
        'category': 'LIGHTING EQUIPMENT',
        'definition': 'This assembly includes fixtures, conduit, wire, and switching devices.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'D502090',
        'category': 'OTHER LIGHTING AND BRANCH WIRING',
        'definition': 'Lighting and branch wiring not described by the assembly categories listed above.'
    }, {
        'code': 'D5030',
        'category': 'COMMUNICATIONS & SECURITY',
        'definition': 'This subsystem includes provisions for communication devices and alarm protection systems.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'D503001',
        'category': 'TELECOMMUNICATIONS SYSTEMS',
        'definition': 'This system would include central switchboards, telephone sets, underground ducts, and manholes. Assemblies include wire, conduit, backboards, cabinets, outlets, and power supply connections.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of outlets'
    }, {
        'code': 'D503002',
        'category': 'PUBLIC ADDRESS SYSTEMS',
        'definition': 'Assemblies include wire, conduit, speakers, monitoring devices, amplifiers, switches, power system tie-in devices, and detection devices.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'D503003',
        'category': 'INTERCOMMUNICATIONS SYSTEMS',
        'definition': 'Assemblies include wire, conduit, speakers, monitoring devices, amplifiers, switches, power system tie-in devices, and detection devices.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of stations'
    }, {
        'code': 'D503004',
        'category': 'TELEVISION SYSTEMS',
        'definition': 'Assemblies include wire, conduit, grounding amplifiers, receivers, video equipment, and outlets grouped according to use.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of outlets'
    }, {
        'code': 'D503005',
        'category': 'SECURITY SYSTEMS',
        'definition': 'Assemblies include wire, conduit, conduit support or fastening systems, security alarm devices, all electrical connections, and other associated items. Intrusion Detection Systems (IDS) are included in this category.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of system control panels'
    }, {
        'code': 'D503006',
        'category': 'NURSE CALL SYSTEMS',
        'definition': 'Assemblies include wire, conduit, speakers, monitoring devices, amplifiers, switches, power system tie-in devices, and detection devices.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of outlets'
    }, {
        'code': 'D503007',
        'category': 'CLOCK & PROGRAM SYSTEMS',
        'definition': 'Assemblies include wire, conduit, power systems tie-in, safety switches, control panels, battery back-up devices, clocks and outlets.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of clocks'
    }, {
        'code': 'D503090',
        'category': 'OTHER COMMUNICATIONS & ALARM SYSTEMS',
        'definition': 'Communication and alarm systems not described by the assembly categories listed above.'
    }, {
        'code': 'D5090',
        'category': 'OTHER ELECTRICAL SERVICES',
        'definition': 'Systems not described in System D5030.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross Floor area'
    }, {
        'code': 'D509001',
        'category': 'GENERAL CONSTRUCTION ITEMS (ELECTRICAL)',
        'definition': 'Includes construction other than electrical which must be performed in conjunction with the special electrical system to make the system complete.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross Floor area'
    }, {
        'code': 'D509002',
        'category': 'EMERGENCY LIGHTING & POWER',
        'definition': 'Assemblies include fixtures, motors used for power generation, connection and testing, transfer switches, conduit, wire, battery chargers, batteries, and solar panels.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross Floor area'
    }, {
        'code': 'D509003',
        'category': 'GROUNDING SYSTEMS',
        'definition': 'This assembly includes grounding protection systems.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross Floor area'
    }, {
        'code': 'D509004',
        'category': 'LIGHTNING PROTECTION',
        'definition': 'Assemblies include lightning protection devices (air terminals, mounting devices), clamps, ground rods, cadwells, conductors, trenching, backfill, and any other items used to ground metal structural frames with conduit and wire.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross Floor area'
    }, {
        'code': 'D509005',
        'category': 'ELECTRIC HEATING',
        'definition': 'Items could include baseboard heaters and wall and ceiling heaters. Assemblies include safety switches, control devices, heaters, conduit, and wire.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross Floor area'
    }, {
        'code': 'D509006',
        'category': 'ENERGY MANAGEMENT CONTROL SYSTEM',
        'definition': 'Assemblies include wire, conduit, conduit support or fastening systems, sensor devices, and all electrical connections.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross Floor area'
    }, {
        'code': 'D509090',
        'category': 'OTHER SPECIAL SYSTEMS AND DEVICES',
        'definition': 'Special systems and devices not described by the assembly categories listed above.'
    }, {
        'code': 'E',
        'category': 'EQUIPMENT & FURNISHINGS',
        'definition': 'The types of equipment included in this assembly consist of the following: commercial, institutional, and vehicular. The types of furnishings found here include artwork, window treatments, seating, furniture, rugs etc.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross Floor Area'
    }, {
        'code': 'E10',
        'category': 'EQUIPMENT',
        'definition': 'This system refers to equipment not found in System C1030 (Fittings).',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Gross Floor area'
    }, {
        'code': 'E1010',
        'category': 'COMMERCIAL EQUIPMENT',
        'definition': 'This equipment is not likely to be used in every building type. Subsystem C1030 includes those items likely to be found in every building type.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'E101001',
        'category': 'CHECKROOM EQUIPMENT',
        'definition': 'All associated work items including keys, tags, and storage cabinets would be included in this assembly.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of coat hanging devices'
    }, {
        'code': 'E101002',
        'category': 'REGISTRATION EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E101003',
        'category': 'VENDING EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E101004',
        'category': 'LAUNDRY EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E101005',
        'category': 'SECURITY & VAULT EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E101006',
        'category': 'TELLER AND SERVICE EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E101007',
        'category': 'MERCANTILE EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E101008',
        'category': 'OFFICE EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E1020',
        'category': 'INSTITUTIONAL EQUIPMENT',
        'definition': 'Institutional equipment includes items that are normally found in hospitals, laboratories, auditoriums, and libraries.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'E102001',
        'category': 'MISCELLANEOUS COMMON FIXED & MOVEABLE EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E102002',
        'category': 'MEDICAL EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E102003',
        'category': 'LABORATORY EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E102004',
        'category': 'MORTUARY EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E102005',
        'category': 'AUDITORIUM & STAGE EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E102006',
        'category': 'LIBRARY EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E102007',
        'category': 'ECCLESIASTICAL EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E102008',
        'category': 'INSTRUMENTAL EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E102009',
        'category': 'AUDIO-VISUAL EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E102010',
        'category': 'DETENTION EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E1030',
        'category': 'VEHICULAR EQUIPMENT',
        'definition': 'Vehicular equipment includes for parking, loading docks, and warehouses.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E103001',
        'category': 'PARKING CONTROL EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E103002',
        'category': 'LOADING DOCK EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of docks'
    }, {
        'code': 'E103003',
        'category': 'WAREHOUSE EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E103004',
        'category': 'AUTOMOTIVE SHOP EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E1040',
        'category': 'GOVERNMENT FURNISHED EQUIPMENT',
        'definition': 'New and existing equipment provided to the Contractor by the Government.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E1090',
        'category': 'OTHER EQUIPMENT',
        'definition': 'The type of equipment found in his category include items for maintenance, food service, and waste handling.'
    }, {
        'code': 'E109001',
        'category': 'BUILT-IN MAINTENANCE EQUIPMENT',
        'definition': 'The unit of measure at the assembly level is each.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'E109002',
        'category': 'FOOD SERVICE EQUIPMENT',
        'definition': 'The unit of measure at the assembly level is the total set of equipment needed in the particular functional space area.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Seating capacity'
    }, {
        'code': 'E109003',
        'category': 'WASTE HANDLING EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E109004',
        'category': 'RESIDENTIAL EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E109005',
        'category': 'UNIT KITCHENS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E109006',
        'category': 'DARKROOM EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E109007',
        'category': 'ATHLETIC, RECREATIONAL, & THERAPEUTIC EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E109008',
        'category': 'PLANETARIUM EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E109009',
        'category': 'OBSERVATORY EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E109010',
        'category': 'AGRICULTURAL EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of equipment'
    }, {
        'code': 'E109090',
        'category': 'OTHER SPECIALIZED FIXED AND MOVEABLE EQUIPMENT',
        'definition': 'Specialized fixed and moveable equipment not described by the assembly categories listed above.'
    }, {
        'code': 'E20',
        'category': 'FURNISHINGS',
        'definition': 'The types of furnishings found here include artwork, window treatments, seating, furniture, rugs, etc.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'E2010',
        'category': 'FIXED FURNISHINGS',
        'definition': 'The types of furnishings found here include artwork, window treatments, and seating.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'E201001',
        'category': 'FIXED ARTWORK',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of art work'
    }, {
        'code': 'E201002',
        'category': 'WINDOW TREATMENTS',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of window treatment'
    }, {
        'code': 'E201003',
        'category': 'SEATING (FIXED)',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of seats'
    }, {
        'code': 'E201004',
        'category': 'FIXED INTERIOR LANDSCAPING',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of items'
    }, {
        'code': 'E201090',
        'category': 'OTHER FIXED INTERIOR FURNISHINGS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of furnishings'
    }, {
        'code': 'E2020',
        'category': 'MOVEABLE FURNISHINGS',
        'definition': 'The types of furnishings found here include moveable artwork, furniture, rugs, etc.'
    }, {
        'code': 'E202001',
        'category': 'MOVEABLE ART WORK',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of art work'
    }, {
        'code': 'E202002',
        'category': 'MODULAR PREFABRICATED FURNITURE',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Pieces of prefabricated furniture'
    }, {
        'code': 'E202003',
        'category': 'FREESTANDING FURNITURE',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Pieces of furniture'
    }, {
        'code': 'E202004',
        'category': 'RUGS & ACCESSORIES',
        'definition': 'Assemblies include rugs and accessories.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of rugs, mats, accessories'
    }, {
        'code': 'E202005',
        'category': 'MOVEABLE MULTIPLE SEATING',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of items'
    }, {
        'code': 'E202006',
        'category': 'MOVEABLE INTERIOR LANDSCAPING',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of items'
    }, {
        'code': 'E202090',
        'category': 'OTHER MOVEABLE FURNISHINGS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of furnishings'
    }, {
        'code': 'F',
        'category': 'SPECIAL CONSTRUCTION & DEMOLITION',
        'definition': 'Special construction includes air-supported structures; pre-engineered structures; special purpose rooms; sound, vibration, and seismic construction; radiation protection; special security systems; aquatic facilities; ice rinks, site constructed incinerators; kennels and animal shelters; liquid and gas storage tanks; recording instrumentation; and building automation systems. Selective building demolition includes demolition of existing buildings, and site demolition.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'F10',
        'category': 'SPECIAL CONSTRUCTION',
        'definition': 'Special construction includes air-supported structures; pre-engineered structures; special purpose rooms; sound, vibration, and seismic construction; radiation protection; special security systems; aquatic facilities; ice rinks, site constructed incinerators; kennels and animal shelters; liquid and gas storage tanks; recording instrumentation; and building automation systems.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'F1010',
        'category': 'SPECIAL STRUCTURES',
        'definition': 'Special structures includes air-supported structures, and pre-engineered structures.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'F101001',
        'category': 'METAL BUILDING SYSTEMS',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'F101002',
        'category': 'EXTERIOR UTILITY BUILDINGS',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area of exterior building'
    }, {
        'code': 'F101003',
        'category': 'AIR-SUPPORTED STRUCTURES',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area of exterior building'
    }, {
        'code': 'F101090',
        'category': 'OTHER SPECIAL CONSTRUCTION'
    }, {
        'code': 'F1020',
        'category': 'INTEGRATED CONSTRUCTION',
        'definition': 'Integrated construction includes integrated assemblies and special purpose rooms.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Floor area'
    }, {
        'code': 'F102001',
        'category': 'SPECIAL PURPOSE ROOMS',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of room'
    }, {
        'code': 'F102002',
        'category': 'INTEGRATED ASSEMBLIES',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of room'
    }, {
        'code': 'F102090',
        'category': 'OTHER INTEGRATED CONSTRUCTION',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of room'
    }, {
        'code': 'F1030',
        'category': 'SPECIAL CONSTRUCTION SYSTEMS',
        'definition': 'Special construction systems includes sound, vibration, and seismic construction; radiation protection; special security systems; and built-in place vaults.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of room'
    }, {
        'code': 'F103001',
        'category': 'VAULTS',
        'definition': 'This is a built-in-place vault. Prefabricated safes are not included in this assembly. The unit of measure at the assembly level is each.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of vault'
    }, {
        'code': 'F103002',
        'category': 'SOUND, VIBRATION, AND SEISMIC CONSTRUCTION',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of room'
    }, {
        'code': 'F103003',
        'category': 'RADIATION PROTECTION',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of room'
    }, {
        'code': 'F103090',
        'category': 'OTHER SPECIAL CONSTRUCTION SYSTEMS',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of room'
    }, {
        'code': 'F1040',
        'category': 'SPECIAL FACILITIES',
        'definition': 'Special facilities includes aquatic facilities; ice rinks, site constructed incinerators; kennels and animal shelters; and liquid and gas storage tanks.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of room'
    }, {
        'code': 'F104001',
        'category': 'INTERIOR SWIMMING POOLS',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of pool'
    }, {
        'code': 'F104002',
        'category': 'LIQUID AND GAS STORAGE TANKS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of storage tanks'
    }, {
        'code': 'F104003',
        'category': 'KENNELS AND ANIMAL SHELTERS',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of kennel or animal shelter'
    }, {
        'code': 'F104004',
        'category': 'SITE CONSTRUCTED INCINERATORS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of incinerators'
    }, {
        'code': 'F104005',
        'category': 'ICE RINKS',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of ice rink'
    }, {
        'code': 'F104090',
        'category': 'OTHER SPECIAL FACILITIES',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of special facilities'
    }, {
        'code': 'F1050',
        'category': 'SPECIAL CONTROLS AND INSTRUMENTATION',
        'definition': 'Special controls and instrumentation includes recording instrumentation and building automation systems.'
    }, {
        'code': 'F105001',
        'category': 'RECORDING INSTRUMENTATION',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of instruments'
    }, {
        'code': 'F105002',
        'category': 'BUILDING AUTOMATION SYSTEMS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of systems'
    }, {
        'code': 'F105090',
        'category': 'OTHER SPECIAL CONTROLS AND INSTRUMENTATION',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of controls and instruments'
    }, {
        'code': 'F20',
        'category': 'SELECTIVE BUILDING DEMOLITION',
        'definition': 'Selective building demolition includes demolition of existing buildings, site demolition, and hazardous components abatement.',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F2010',
        'category': 'BUILDING ELEMENTS DEMOLITION',
        'definition': 'Selective building demolition includes demolition of existing buildings, and site demolition.',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F201001',
        'category': 'SUBSTRUCTURE & SUPERSTRUCTURE',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F201002',
        'category': 'EXTERIOR CLOSURE',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F201003',
        'category': 'ROOFING',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F201004',
        'category': 'INTERIOR CONSTRUCTION & FINISHES',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F201005',
        'category': 'CONVEYING SYSTEMS',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F201006',
        'category': 'MECHANICAL SYSTEMS',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F201007',
        'category': 'ELECTRICAL SYSTEMS',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F201008',
        'category': 'EQUIPMENT & FURNISHINGS',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F201090',
        'category': 'OTHER NON-HAZARDOUS SELECTIVE BUILDING DEMOLITION',
        'definition': 'Non-hazardous selective building demolition not described by the assembly categories listed above.'
    }, {
        'code': 'F2020',
        'category': 'HAZARDOUS COMPONENTS ABATEMENT',
        'definition': 'Hazardous components abatement includes the removal or encapsulation of hazardous building materials and components. Hazardous components include asbestos, lead based paint, paint containing cadmium, chromium and lead, mercury and low level radioactive components, PCBs, ozone depleting substances, animal droppings and molds and spores.',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F202001',
        'category': 'SUBSTRUCTURE & SUPERSTRUCTURE',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F202002',
        'category': 'EXTERIOR CLOSURE',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F202003',
        'category': 'ROOFING',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F202004',
        'category': 'INTERIOR CONSTRUCTION & FINISHES',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F202005',
        'category': 'CONVEYING SYSTEMS',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F202006',
        'category': 'MECHANICAL SYSTEMS',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F202007',
        'category': 'ELECTRICAL SYSTEMS',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F202008',
        'category': 'EQUIPMENT & FURNISHINGS',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'F202090',
        'category': 'OTHER HAZARDOUS SELECTIVE BUILDING DEMOLITION',
        'definition': 'Hazardous selective building demolition not described by the assembly categories listed above.'
    }, {
        'code': 'G',
        'category': 'BUILDING SITEWORK',
        'definition': 'Building sitework includes site preparations, site improvements, site civil/mechanical utilities, site electrical utilities, service and pedestrian tunnels, and other site construction, such as bridges, and railroad spurs.',
        'imperial_units': 'ACR',
        'metric_units': 'Hectare',
        'quantity_definition': 'Total area of site'
    }, {
        'code': 'G10',
        'category': 'SITE PREPARATIONS',
        'definition': 'This system includes assemblies for miscellaneous sitework such as clearing and grubbing, demolition and relocation, various earthwork tasks, and other site preparation and cleanup requirements. Hazardous cleanup is not included but is the subject of another WBS.',
        'imperial_units': 'ACR',
        'metric_units': 'Hectare',
        'quantity_definition': 'Total area of site'
    }, {
        'code': 'G1010',
        'category': 'SITE CLEARING',
        'definition': 'This covers the different assemblies and options available for clearing of a site, tree and stump removal, burning, grubbing, chipping, and load and haul assemblies for removal of the cleared material.',
        'imperial_units': 'ACR',
        'metric_units': 'Hectare',
        'quantity_definition': 'Area to be cleared'
    }, {
        'code': 'G101001',
        'category': 'CLEARING',
        'definition': 'This is the removal of above ground vegetation including stumps. For a wet site, Low Ground Pressure (LGP) equipment is used.',
        'imperial_units': 'ACR',
        'metric_units': 'Hectare',
        'quantity_definition': 'Area to be cleared'
    }, {
        'code': 'G101002',
        'category': 'TREE REMOVAL',
        'definition': 'This is the selective removal of trees on the site. Various options exist for different sizes of trees to be removed.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of trees to be removed'
    }, {
        'code': 'G101003',
        'category': 'STUMP REMOVAL',
        'definition': 'This is the selective removal of stumps on the site. Various options exist for different sizes of stumps to be removed.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of stumps to be removed'
    }, {
        'code': 'G101004',
        'category': 'GRUBBING',
        'definition': 'Grubbing is the removal of sod and other topsoil that contains unsuitable organic material. Various equipment types and size choices are available. Wet grubbing utilizes Low Ground Pressure (LGP) equipment. Haul-off of grubbed material is also included.',
        'imperial_units': 'ACR',
        'metric_units': 'Hectare',
        'quantity_definition': 'Area to be grubbed'
    }, {
        'code': 'G101005',
        'category': 'SELECTIVE THINNING',
        'definition': 'This is the selective removal of trees and underbrush without requiring extensive clearing and/or grubbing of the site.',
        'imperial_units': 'ACR',
        'metric_units': 'Hectare',
        'quantity_definition': 'Area to be thinned'
    }, {
        'code': 'G101006',
        'category': 'DEBRIS DISPOSAL',
        'definition': 'This is the disposal of the material that has been cleared and grubbed. Loading, hauling, and dump charges are included.',
        'imperial_units': 'CY',
        'metric_units': 'M3',
        'quantity_definition': 'Volume of material'
    }, {
        'code': 'G101090',
        'category': 'OTHER SITE CLEARING',
        'definition': 'Site clearing not described by the assembly categories listed above.'
    }, {
        'code': 'G1020',
        'category': 'SITE DEMOLITION & RELOCATIONS',
        'definition': 'This includes the demolition and/or relocation of structures, pavements, fencing, and underground utilities. Disposal of debris or demolished material, including loading and hauling, is also included.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area to be demolished'
    }, {
        'code': 'G102001',
        'category': 'BUILDING MASS DEMOLITION',
        'definition': 'This is the complete demolition of buildings or structures. Options include steel, concrete, masonry, and wood structures.',
        'imperial_units': 'CF',
        'metric_units': 'M3',
        'quantity_definition': 'Interior volume of building'
    }, {
        'code': 'G102002',
        'category': 'ABOVE GROUND SITE DEMOLITION',
        'definition': 'This is the demolition of pavements, fencing, and other non-building structures on a site. Pavement include roads, sidewalks, driveways, and curbs. Fencing types include chain link, barbed wire, and wood. This can also include removal and disposal of above ground storage tanks, including tank contents, associated piping, etc.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area to be demolished'
    }, {
        'code': 'G102003',
        'category': 'UNDERGROUND SITE DEMOLITION',
        'definition': 'This is the demolition of underground utilities such as piping, manholes, and other non-building underground structures. The unit of measure at the assembly level for piping is LF and for manholes is CY. This can also include removal and disposal of under ground storage tanks, including tank contents, associated piping, etc.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area to be demolished'
    }, {
        'code': 'G102004',
        'category': 'BUILDING RELOCATION',
        'definition': 'This is the process of dismantling a structure, and reassembling it on a different site.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area of building to be relocated'
    }, {
        'code': 'G102005',
        'category': 'UTILITY RELOCATION',
        'definition': 'To remove and reset. This is the removal and relocation of underground utilities such as steel and concrete pipe.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of pipe run'
    }, {
        'code': 'G102006',
        'category': 'FENCING RELOCATION',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of fencing'
    }, {
        'code': 'G102007',
        'category': 'SITE CLEANUP',
        'definition': 'Covered in this assembly category are items for site and area cleanup and pavement sweeping. Disposal of the debris is also included.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of site to clean'
    }, {
        'code': 'G102090',
        'category': 'OTHER SITE DEMOLITION & RELOCATIONS',
        'definition': 'Site demolition and relocation not described by the assembly categories listed above.'
    }, {
        'code': 'G1030',
        'category': 'SITE EARTHWORK',
        'definition': 'Included are assemblies and options for site work such as grading, excavation, filling, compaction, stabilization, etc.',
        'imperial_units': 'CY',
        'metric_units': 'M3',
        'quantity_definition': 'Volume of material'
    }, {
        'code': 'G103001',
        'category': 'GRADING',
        'definition': 'Grading is leveling or flattening of the site in preparation for landscaping or other site construction. Includes unlined stormwater collection ponds.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area to be graded'
    }, {
        'code': 'G103002',
        'category': 'COMMON EXCAVATION',
        'definition': 'This is excavation for roads, sidewalks, curbs, and trenching for underground utilities. Excavation may be carried out by a variety of equipment sizes and types. Disposal of the excavated material is also included.',
        'imperial_units': 'CY',
        'metric_units': 'M3',
        'quantity_definition': 'Volume of material to be excavated'
    }, {
        'code': 'G103003',
        'category': 'ROCK EXCAVATION',
        'definition': 'This is excavation of rock by explosives. Different equipment selections and load and haul are included.',
        'imperial_units': 'CY',
        'metric_units': 'M3',
        'quantity_definition': 'Volume of rock to be excavated'
    }, {
        'code': 'G103004',
        'category': 'FILL & BORROW',
        'definition': 'This is filling or replacing the material that was removed during excavation. Either the excavated material may be used or soil and sand may be hauled in from off-site. Filling to basements and foundations is not included in the subsystem.',
        'imperial_units': 'CY',
        'metric_units': 'M3',
        'quantity_definition': 'Volume of material to place'
    }, {
        'code': 'G103005',
        'category': 'COMPACTION',
        'definition': 'Compaction is the process of packing the fill material once it is in place. This may be done by machine or hand. Assemblies exist for both hand and machine compaction of soil, sand, and the excavated material.',
        'imperial_units': 'CY',
        'metric_units': 'M3',
        'quantity_definition': 'Volume of material to compact'
    }, {
        'code': 'G103006',
        'category': 'SOIL STABILIZATION',
        'definition': 'This is stabilization of the soil-in-place by the addition of lime or cement.',
        'imperial_units': 'CY',
        'metric_units': 'M3',
        'quantity_definition': 'Volume of soil to stabilize'
    }, {
        'code': 'G103007',
        'category': 'SLOPE STABILIZATION',
        'definition': 'This is stabilization of the soil-in-place through the use of rip rap, gabions, slope paving, or other forms of soil armoring.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of slope'
    }, {
        'code': 'G103008',
        'category': 'SOIL TREATMENT',
        'definition': 'Treatment of soil prior to final construction for insect protection or other purposes.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of soil to treat'
    }, {
        'code': 'G103009',
        'category': 'SHORING',
        'definition': 'Shoring is the temporary support for existing structures or excavation during construction.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area requiring shoring'
    }, {
        'code': 'G103010',
        'category': 'TEMPORARY DEWATERING',
        'definition': 'This is the dewatering of the site by wellpoints to lower the groundwater table. This will facilitate excavation in areas with high water tables.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area to dewater'
    }, {
        'code': 'G103011',
        'category': 'TEMPORARY EROSION & SEDIMENT CONTROL',
        'definition': 'Interim measures to minimize erosion during construction.',
        'imperial_units': 'SF',
        'metric_units': 'M2',
        'quantity_definition': 'Area to be protected'
    }, {
        'code': 'G103090',
        'category': 'OTHER SITE EARTHWORK',
        'definition': 'Site earthwork not described by the assembly categories listed above.'
    }, {
        'code': 'G1040',
        'category': 'HAZARDOUS WASTE REMEDIATION',
        'definition': 'Hazardous waste remediation, removal, disaposal and restoration of contaminated soil and/or groundwater.',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'G104001',
        'category': 'REMOVAL OF CONTAMINATED SOIL',
        'imperial_units': 'CY',
        'metric_units': 'M3',
        'quantity_definition': 'Volume of contaminated soil'
    }, {
        'code': 'G104002',
        'category': 'SOIL RESTORATION AND TREATMENT',
        'imperial_units': 'CY',
        'metric_units': 'M3',
        'quantity_definition': 'Volume of soil'
    }, {
        'code': 'G104090',
        'category': 'OTHER HAZARDOUS WASTE REMEDIATION',
        'definition': 'Hazardous waste remediation not described by the assembly categories listed above.'
    }, {
        'code': 'G20',
        'category': 'SITE IMPROVEMENTS',
        'definition': 'This includes improvements such as parking lots, sidewalks, roadways, fencing, retaining walls, and landscaping.',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'G2010',
        'category': 'ROADWAYS',
        'definition': 'This subsystem includes options for access, arterial, or interstate roadways. A variety of pavement types and thickness are available.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of roadway'
    }, {
        'code': 'G201001',
        'category': 'BASES & SUBBASES',
        'definition': 'These are the compacted and prepared gravel or soil layers that are placed prior to the installation of the final surface. The subbase is placed and compacted before the base layer is applied.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of roadway'
    }, {
        'code': 'G201002',
        'category': 'CURBS & GUTTERS',
        'definition': 'This is the drainage system for the selected roadway type. Options include curb and gutter drains or area drains with grates.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of drainage pipe'
    }, {
        'code': 'G201003',
        'category': 'PAVED SURFACES',
        'definition': 'This is material that is placed atop the base layer to provide the driving surface.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of roadway'
    }, {
        'code': 'G201004',
        'category': 'MARKING & SIGNAGE',
        'definition': 'This includes roadway signage and pavement painting. Assemblies are included for traffic signs and posts and intersection, crosswalk, or other pavement painting or striping.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of roadway'
    }, {
        'code': 'G201005',
        'category': 'GUARDRAILS & BARRIERS',
        'definition': 'This is any associated guardrails or barriers that are required for the selected roadway type.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of guardrail or barrier'
    }, {
        'code': 'G201006',
        'category': 'RESURFACING',
        'definition': 'This is the placement of an asphalt wearing course over the existing pavement surface. Assemblies exist for resurfacing of gravel, concrete, and asphalt roadways.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of roadway'
    }, {
        'code': 'G201090',
        'category': 'OTHER ROADWAYS',
        'definition': 'Roadways not described by the assembly categories listed above.'
    }, {
        'code': 'G2020',
        'category': 'PARKING LOTS',
        'definition': 'These are the areas required of vehicles parking and include different surfaces and drainage options.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of spaces'
    }, {
        'code': 'G202001',
        'category': 'BASES & SUBBASES',
        'definition': 'These are the compacted and prepared gravel or soil layers that are placed prior to the installation of the final surface. The subbase is placed and compacted before the base layer is applied.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of parking lot'
    }, {
        'code': 'G202002',
        'category': 'CURBS & GUTTERS',
        'definition': 'This is the curb and gutter drains or area drains with grates.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of curbs & gutters'
    }, {
        'code': 'G202003',
        'category': 'PAVED SURFACES',
        'definition': 'This is material that is placed atop the base layer to provide the driving surface.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of parking lot'
    }, {
        'code': 'G202004',
        'category': 'MARKING & SIGNAGE',
        'definition': 'This includes painting of the parking stalls, signage, etc.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of spaces'
    }, {
        'code': 'G202005',
        'category': 'GUARDRAILS & BARRIERS',
        'definition': 'Guardrails, barriers, parking stops and other similar devices.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of guardrail or barrier'
    }, {
        'code': 'G202006',
        'category': 'RESURFACING',
        'definition': 'This is the placement of an asphalt wearing course over the existing parking surface.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of parking lot'
    }, {
        'code': 'G202007',
        'category': 'MISCELLANEOUS STRUCTURES AND EQUIPMENT',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of structures or equipment'
    }, {
        'code': 'G202090',
        'category': 'OTHER PARKING LOTS',
        'definition': 'Parking areas not described by the assembly categories listed above.'
    }, {
        'code': 'G2030',
        'category': 'PEDESTRIAN PAVING',
        'definition': 'This subsystem includes options for sidewalks and other small paved areas.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of pavement'
    }, {
        'code': 'G203001',
        'category': 'BASES & SUBBASES',
        'definition': 'These are the compacted and prepared gravel or soil layers that are placed prior to the installation of the final surface. The subbase is placed and compacted before the base layer is applied.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of pavement'
    }, {
        'code': 'G203002',
        'category': 'CURBS & GUTTERS',
        'definition': 'This is the curb and gutter drains or area drains with grates.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of curbs & gutters'
    }, {
        'code': 'G203003',
        'category': 'PAVED SURFACES',
        'definition': 'This is material that is placed atop the base layer to provide the walking or driving surface.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of pavement'
    }, {
        'code': 'G203004',
        'category': 'GUARDRAILS & BARRIERS',
        'definition': 'This is any associated guardrails or barriers that are required.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of guardrail or barrier'
    }, {
        'code': 'G203005',
        'category': 'RESURFACING',
        'definition': 'This is the placement of an asphalt wearing course over the existing pavement surface.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of pavement'
    }, {
        'code': 'G203090',
        'category': 'OTHER WALKS, STEPS & TERRACES',
        'definition': 'Walks, steps, ramps, terraces not described by the assembly categories listed above.'
    }, {
        'code': 'G2040',
        'category': 'SITE DEVELOPMENT',
        'definition': 'Included are assemblies for on-site construction of fences, retaining walls, playing fields, fountains, and other site improvements.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each Structure'
    }, {
        'code': 'G204001',
        'category': 'FENCING & GATES',
        'definition': 'This includes installation or construction of security, boundary, or barbed wire fencing and all required gates.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of fence'
    }, {
        'code': 'G204002',
        'category': 'RETAINING WALLS AND FREESTANDING WALLS',
        'definition': 'These are structures used to prevent the flow or lateral movement of soil. Assemblies exist for cast-in-place concrete retaining walls.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of wall'
    }, {
        'code': 'G204003',
        'category': 'EXTERIOR FURNISHINGS',
        'definition': 'This includes the addition of such exterior furnishings as benches, planters, etc.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of furnishings'
    }, {
        'code': 'G204004',
        'category': 'SECURITY STRUCTURES',
        'definition': 'This includes the construction or addition of security structures such as guard houses.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of security structures'
    }, {
        'code': 'G204005',
        'category': 'SIGNAGE',
        'definition': 'Signs displayed to convey direction or information such as building function or tenant except for signs included in G201004 and G202004.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of signs'
    }, {
        'code': 'G204006',
        'category': 'FOUNTAINS & POOLS',
        'definition': 'This includes assemblies for swimming pools and decorative fountains.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fountains or pools'
    }, {
        'code': 'G204007',
        'category': 'PLAYING FIELDS',
        'definition': 'Playing fields such as baseball or tennis courts as well as back stops, bleachers, and other playing field requirements are included.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of playing fields'
    }, {
        'code': 'G204008',
        'category': 'TERRACE AND PERIMETER WALLS',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of wall'
    }, {
        'code': 'G204009',
        'category': 'FLAGPOLES',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of flagpoles'
    }, {
        'code': 'G204090',
        'category': 'OTHER SITE IMPROVEMENTS',
        'definition': 'This includes any other miscellaneous structures, such as a car wash, banking system, and theatre equipment located on the site.'
    }, {
        'code': 'G2050',
        'category': 'LANDSCAPING',
        'definition': 'Assemblies are included that improve the appearance of the site by planting, seeding, and sodding.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area to be landscaped'
    }, {
        'code': 'G205001',
        'category': 'FINE GRADING & SOIL PREPARATION',
        'definition': 'Fine grading of the site by hand or machine is required to prepare the soil for planting, seeding, or sodding.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of site'
    }, {
        'code': 'G205002',
        'category': 'EROSION CONTROL MEASURES',
        'definition': 'Soil erosion or deterioration due to wind, rain or other factors can be controlled or remedied in different ways. This includes slope protection by planting or vegetation or grass and/or placement of manmade geotextiles.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of erosion'
    }, {
        'code': 'G205003',
        'category': 'TOPSOIL & PLANTING BEDS',
        'definition': 'Topsoil is placed to provide the nutritious soil bed which is required for plants or grass to grow.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of planting bed'
    }, {
        'code': 'G205004',
        'category': 'SEEDING, SPRIGGING AND SODDING',
        'definition': 'This includes the seeding, sodding, fertilizing, watering, and mowing for the grass required on site.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of site'
    }, {
        'code': 'G205005',
        'category': 'PLANTINGS',
        'definition': 'This includes the planting of trees, shrubs, and other vegetation for site beautification or improvement.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of plants'
    }, {
        'code': 'G205006',
        'category': 'PLANTERS',
        'definition': 'Planters are exterior decorative containers that contain plants or trees.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of planters'
    }, {
        'code': 'G205007',
        'category': 'IRRIGATION SYSTEMS',
        'definition': 'This includes the installation of underground irrigation systems required for watering of trees, shrubs, and grass or other vegetation.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of site to be watered'
    }, {
        'code': 'G205090',
        'category': 'OTHER LANDSCAPING',
        'definition': 'Landscaping not described by the assembly categories listed above.'
    }, {
        'code': 'G2060',
        'category': 'AIRFIELD PAVING',
        'definition': 'Aircraft parking apron and runway paving.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of paving'
    }, {
        'code': 'G206001',
        'category': 'AIRFIELD PAVING CONSTRUCTION',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of paving'
    }, {
        'code': 'G206002',
        'category': 'OTHER PAVING',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of paving'
    }, {
        'code': 'G206003',
        'category': 'JOINTS AND ANCHORAGE',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of paving'
    }, {
        'code': 'G206004',
        'category': 'NAVIGATION AIDS',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'G206005',
        'category': 'AIRFIELD MARKINGS',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'G30',
        'category': 'SITE CIVIL/MECHANICAL UTILITIES',
        'definition': 'Site mechanical utilities includes water supply, sanitary sewer, storm sewer, heating distribution, cooling distribution, fuel distribution, and other site mechanical utilities, such as industrial waste systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each utility'
    }, {
        'code': 'G3010',
        'category': 'WATER SUPPLY',
        'definition': 'This includes installation or construction of water distribution systems and facilities.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G301001',
        'category': 'WELL SYSTEMS',
        'definition': 'This includes all the components necessary to install a well, including drilling, installing casings, pumps, valves, etc.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each system'
    }, {
        'code': 'G301002',
        'category': 'POTABLE WATER DISTRIBUTION',
        'definition': 'This includes construction and installation of underground piping, valve boxes, and valves.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G301003',
        'category': 'POTABLE WATER STORAGE',
        'definition': 'This includes construction and installation of tanks, both at grade and elevated.',
        'imperial_units': 'GAL',
        'metric_units': 'GAL',
        'quantity_definition': 'Amount stored'
    }, {
        'code': 'G301004',
        'category': 'FIRE PROTECTION WATER DISTRIBUTION',
        'definition': 'This includes construction and installation of dedicated water piping for fire protection system only. This does not include potable water distribution systems that are used as a water source for fire protection systems.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G301005',
        'category': 'FIRE PROTECTION WATER STORAGE',
        'definition': 'This includes tanks on grade and elevated for storage of water for fire protection only.',
        'imperial_units': 'GAL',
        'metric_units': 'GAL',
        'quantity_definition': 'Amount stored'
    }, {
        'code': 'G301006',
        'category': 'NON-POTABLE WATER DISTRIBUTION',
        'definition': 'This includes construction and installation of water distribution system not for consumption, such as irrigation or hydro-electric power generation and from reservoirs to treatment facilities.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G301007',
        'category': 'PUMPING STATIONS',
        'definition': 'This includes construction and installation of pumps, valves, and piping.',
        'imperial_units': 'GPM',
        'metric_units': 'L/S',
        'quantity_definition': 'Operating capacity'
    }, {
        'code': 'G301008',
        'category': 'PACKAGED WATER TREATMENT PLANTS',
        'definition': 'This includes installation of completely assembled water treatment plants.',
        'imperial_units': 'GPD',
        'metric_units': 'GPD',
        'quantity_definition': 'Operating capacity'
    }, {
        'code': 'G301090',
        'category': 'OTHER WATER SUPPLY',
        'definition': 'Water supply not described by the assembly categories listed above.'
    }, {
        'code': 'G3020',
        'category': 'SANITARY SEWER',
        'definition': 'This includes all assemblies necessary for sewage collection systems.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G302001',
        'category': 'SANITARY SEWER PIPING',
        'definition': 'This includes installation of piping for collection of sewage.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of piping'
    }, {
        'code': 'G302002',
        'category': 'SANITARY SEWER MANHOLES & CLEANOUTS',
        'definition': 'This includes construction and installation of manholes and cleanouts in sewage collection systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each manhole or cleanout'
    }, {
        'code': 'G302003',
        'category': 'LIFT STATIONS AND PUMPING STATIONS',
        'definition': 'This includes construction and installation of piping and equipment in lift stations.',
        'imperial_units': 'GPM',
        'metric_units': 'L/S',
        'quantity_definition': 'Operating capacity'
    }, {
        'code': 'G302004',
        'category': 'PACKAGED SANITARY SEWER TREATMENT PLANTS',
        'definition': 'This includes installation of pre-assembled sewage treatment plants.',
        'imperial_units': 'GPD',
        'metric_units': 'L/S',
        'quantity_definition': 'Operating capacity'
    }, {
        'code': 'G302005',
        'category': 'SEPTIC TANKS',
        'definition': 'This includes installation of prefabricated septic tanks or the construction of septic tanks.',
        'imperial_units': 'GAL',
        'metric_units': 'L',
        'quantity_definition': 'Volume of tank'
    }, {
        'code': 'G302006',
        'category': 'DRAIN FIELDS',
        'definition': 'This includes installation of drain fields for disposal of effluent from septic tanks.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of field'
    }, {
        'code': 'G302090',
        'category': 'OTHER SANITARY SEWER',
        'definition': 'Sanitary sewers not described by the assembly categories listed above.'
    }, {
        'code': 'G3030',
        'category': 'STORM SEWER',
        'definition': 'This includes construction of storm water collection systems.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G303001',
        'category': 'STORM SEWER PIPING',
        'definition': 'This includes installation of piping for collection of storm water.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of piping'
    }, {
        'code': 'G303002',
        'category': 'STORM SEWER STRUCTURES',
        'definition': 'This includes construction and installation of manholes for storm water collection systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each manhole or cleanout'
    }, {
        'code': 'G303003',
        'category': 'LIFT STATIONS',
        'definition': 'This includes construction of lift stations including piping, pumps, and controls.',
        'imperial_units': 'GPM',
        'metric_units': 'L/S',
        'quantity_definition': 'Operating capacity'
    }, {
        'code': 'G303004',
        'category': 'CULVERTS',
        'definition': 'This includes construction and installation of culverts for storm water systems.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of culvert'
    }, {
        'code': 'G303005',
        'category': 'HEADWALLS',
        'definition': 'This includes construction of headwalls and installation of catch basins for storm water systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each structure'
    }, {
        'code': 'G303006',
        'category': 'EROSION & SEDIMENT CONTROL MEASURES',
        'definition': 'This includes construction to control erosion due to runoff.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area to control'
    }, {
        'code': 'G303007',
        'category': 'STORMWATER MANAGEMENT',
        'imperial_units': 'GAL',
        'metric_units': 'GAL',
        'quantity_definition': 'Volume of collection area'
    }, {
        'code': 'G303090',
        'category': 'OTHER STORM SEWER',
        'definition': 'Storm sewers not described by the assembly categories listed above.'
    }, {
        'code': 'G3040',
        'category': 'HEATING DISTRIBUTION',
        'definition': 'This includes overhead and underground hot water, steam, and condensate piping.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G304001',
        'category': 'OVERHEAD HOT WATER SYSTEMS',
        'definition': 'This includes installation of overhead hot water supply and return piping.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G304002',
        'category': 'OVERHEAD STEAM SYSTEMS',
        'definition': 'This includes installation of overhead steam supply and condensate return piping.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G304003',
        'category': 'UNDERGROUND HOT WATER SYSTEMS',
        'definition': 'This includes installation of underground hot water supply and return piping.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G304004',
        'category': 'UNDERGROUND STEAM DISTRIBUTION SYSTEMS',
        'definition': 'This includes installation of underground steam supply and condensate return piping.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G304005',
        'category': 'REINFORCED CONCRETE MANHOLES & VALVE BOXES',
        'definition': 'This includes installation of prefabricated trench boxes for shoring during installation of piping.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each structure'
    }, {
        'code': 'G304006',
        'category': 'PUMPING STATIONS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each pumping station'
    }, {
        'code': 'G304090',
        'category': 'OTHER HEATING DISTRIBUTION',
        'definition': 'Heating distribution not described by the assembly categories listed above.'
    }, {
        'code': 'G3050',
        'category': 'COOLING DISTRIBUTION',
        'definition': 'This includes construction and installation of chilled water distribution systems.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G305001',
        'category': 'OVERHEAD COOLING SYSTEMS',
        'definition': 'This includes installation of overhead chilled water supply and return piping.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G305002',
        'category': 'UNDERGROUND COOLING SYSTEMS',
        'definition': 'This includes installation of underground chilled water supply and return piping.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G305003',
        'category': 'TRENCHBOXES',
        'definition': 'This includes installation of prefabricated trench boxes for shoring during installation of piping.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of trench'
    }, {
        'code': 'G305004',
        'category': 'WELLS FOR COOLING',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each well'
    }, {
        'code': 'G305005',
        'category': 'PUMPING STATIONS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each pumping station'
    }, {
        'code': 'G305006',
        'category': 'ON-SITE COOLING TOWERS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each cooling tower'
    }, {
        'code': 'G305090',
        'category': 'OTHER COOLING DISTRIBUTION',
        'definition': 'Cooling distribution not described by the assembly categories listed above.'
    }, {
        'code': 'G3060',
        'category': 'FUEL DISTRIBUTION',
        'definition': 'This includes installation of piping and storage tanks for building and aviation fuels.',
        'imperial_units': 'GAL',
        'metric_units': 'L',
        'quantity_definition': 'Volume of storage tank'
    }, {
        'code': 'G306001',
        'category': 'LIQUID FUEL DISTRIBUTION PIPING SYSTEM',
        'definition': 'This includes installation of piping for fuel and oil distribution. This includes equipment related to piping, system leak detection and tightness testing.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of piping'
    }, {
        'code': 'G306002',
        'category': 'AVIATION FUEL DISTRIBUTION PIPING SYSTEM',
        'definition': 'This includes installation of piping for aviation fuel distribution and equipment related to the piping. This also includes system leak detection and tightness testing.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of piping'
    }, {
        'code': 'G306003',
        'category': 'LIQUID FUEL STORAGE TANKS',
        'definition': 'This includes installation of buried or above ground fuel tanks relating to liquid fuel or aviation systems.',
        'imperial_units': 'GAL',
        'metric_units': 'L',
        'quantity_definition': 'Volume of storage tank'
    }, {
        'code': 'G306004',
        'category': 'LIQUID FUEL DISPENSING EQUIPMENT',
        'definition': 'This includes equipment relating to liquid fuel and aviation systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each piece of equipment'
    }, {
        'code': 'G306005',
        'category': 'LIQUID FUEL SYSTEM TRENCHBOXES',
        'definition': 'This includes installation of prefabricated trench boxes for shoring during installation of piping.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of trench'
    }, {
        'code': 'G306006',
        'category': 'GAS DISTRIBUTION PIPING (NATURAL AND PROPANE)',
        'definition': 'This includes piping for distribution of natural or propane gas.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of piping'
    }, {
        'code': 'G306007',
        'category': 'GAS STORAGE TANKS',
        'definition': 'This includes installation of tanks for natural or propane gas.',
        'imperial_units': 'GAL',
        'metric_units': 'L',
        'quantity_definition': 'Volume of storage tank'
    }, {
        'code': 'G306008',
        'category': 'GAS SYSTEM TRENCHBOXES',
        'definition': 'This includes installation of prefabricated trench boxes for shoring during installation of piping.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of trench'
    }, {
        'code': 'G306009',
        'category': 'OTHER GAS DISTRIBUTION',
        'definition': 'Gas distribution not described by the assembly categories listed above.'
    }, {
        'code': 'G306090',
        'category': 'OTHER FUEL DISTRIBUTION',
        'definition': 'Fuel not described by the assembly categories listed above.'
    }, {
        'code': 'G3090',
        'category': 'OTHER SITE MECHANICAL UTILITIES',
        'definition': 'This includes all systems for collection of contaminated waste requiring special treatment.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of system'
    }, {
        'code': 'G309001',
        'category': 'INDUSTRIAL WASTE PIPE',
        'definition': 'This includes construction and installation of all piping for collection of industrial waste.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of piping'
    }, {
        'code': 'G309002',
        'category': 'INDUSTRIAL WASTE MANHOLES & CLEANOUTS',
        'definition': 'This includes construction of manholes and cleanouts for industrial waste.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each manhole or cleanout'
    }, {
        'code': 'G309003',
        'category': 'INDUSTRIAL WASTE LIFT STATIONS',
        'definition': 'This includes construction and installation of industrial waste lift stations and equipment.',
        'imperial_units': 'GPM',
        'metric_units': 'L/S',
        'quantity_definition': 'Operating capacity'
    }, {
        'code': 'G309004',
        'category': 'INDUSTRIAL WASTE HOLDING TANKS & SEPARATORS',
        'definition': 'This includes construction or installation of special tanks such as silver recovery tanks or separators such as oil water separators.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of tanks'
    }, {
        'code': 'G309005',
        'category': 'INDUSTRIAL WASTE TRENCHBOXES',
        'definition': 'This includes installation of prefabricated trench boxes for shoring during installation of piping.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of trench'
    }, {
        'code': 'G309090',
        'category': 'OTHER INDUSTRIAL WASTE',
        'definition': 'Industrial waste not described by the assembly categories listed above, such as petroleum oil and lubricant distribution systems.'
    }, {
        'code': 'G40',
        'category': 'SITE ELECTRICAL UTILITIES',
        'definition': 'This system includes exterior electrical systems and equipment including substations, overhead and underground distribution systems, metering systems and equipment, exterior lighting, lightning protection systems, communication and alarm systems, and cathodic protection.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Systems total'
    }, {
        'code': 'G4010',
        'category': 'ELECTRICAL DISTRIBUTION',
        'definition': 'Electrical distribution includes the following: substations; transformers; switches, controls and devices; overhead electric conductors; towers, poles, crossarms and insulators; underground electric conductors; ductbanks, manholes, handholes and raceways; grounding systems; and metering.',
        'imperial_units': 'KVA',
        'metric_units': 'KVA',
        'quantity_definition': 'Total rated capacity'
    }, {
        'code': 'G401001',
        'category': 'SUBSTATIONS',
        'definition': 'This system includes substation equipment and materials required from the primary power source.',
        'imperial_units': 'KVA',
        'metric_units': 'KVA',
        'quantity_definition': 'Total rated capacity'
    }, {
        'code': 'G401002',
        'category': 'TRANSFORMERS',
        'definition': 'Electrical power transformers used in conjunction with electrical substations. May include pole/tower or pad-mounted transformers located outside the building.',
        'imperial_units': 'KVA',
        'metric_units': 'KVA',
        'quantity_definition': 'Total rated capacity'
    }, {
        'code': 'G401003',
        'category': 'SWITCHES, CONTROLS & DEVICES',
        'definition': 'Includes all components of switchgear, voltage regulators and busbars used with electrical substations.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of separate components'
    }, {
        'code': 'G401004',
        'category': 'OVERHEAD ELECTRIC CONDUCTORS',
        'definition': 'Includes conductors used in conjunction with substations.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of conductor'
    }, {
        'code': 'G401005',
        'category': 'TOWERS, POLES, CROSSARMS & INSULATORS',
        'definition': 'Towers, poles, crossarms, and insulators used in conjunction with substations.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of towers and poles'
    }, {
        'code': 'G401006',
        'category': 'UNDERGROUND ELECTRIC CONDUCTORS',
        'definition': 'Includes conductors used in conjunction with substations.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of conductor'
    }, {
        'code': 'G401007',
        'category': 'DUCTBANKS, MANHOLES, HANDHOLES & RACEWAYS',
        'definition': 'Components used in conjunction with electrical substations.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of ductbanks and access points'
    }, {
        'code': 'G401008',
        'category': 'GROUNDING SYSTEMS',
        'definition': 'Grounding systems used in conjunction with substations. Grounding systems for buildings, power distribution, and other electrical systems and subsystems are included with those other systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of systems'
    }, {
        'code': 'G401009',
        'category': 'METERING',
        'definition': 'Includes components used in conjunction with exterior electrical distribution.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of meters'
    }, {
        'code': 'G401010',
        'category': 'CATHODIC PROTECTION',
        'definition': 'Includes a system used in conjunction with exterior electrical distribution for corrosion control.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Each system'
    }, {
        'code': 'G401011',
        'category': 'EQUIPMENT REQUIREMENTS FOR COASTAL AND HIGH HUMIDITY AREAS'
    }, {
        'code': 'G401090',
        'category': 'OTHER ELECTRIC TRANSMISSION & DISTRIBUTION',
        'definition': 'Substations not described by the assembly categories listed above.'
    }, {
        'code': 'G4020',
        'category': 'SITE LIGHTING',
        'definition': 'Exterior electrical lighting systems including conductors, switches, controls and other devices, supporting structures, grounding systems, and all other equipment required to support a lighting system.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of distribution'
    }, {
        'code': 'G402001',
        'category': 'EXTERIOR LIGHTING FIXTURES & CONTROLS',
        'definition': 'Includes fixtures, controls, and all components used in conjunction with exterior lighting.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'G402002',
        'category': 'SPECIAL SECURITY LIGHTING SYSTEMS',
        'definition': 'Includes all components used for special security lighting.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of systems'
    }, {
        'code': 'G402003',
        'category': 'OTHER AREA LIGHTING',
        'definition': 'Includes components and equipment used for area lighting.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of fixtures'
    }, {
        'code': 'G402004',
        'category': 'LIGHTING POLES',
        'definition': 'Poles used to support lighting fixtures and support equipment.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of towers and poles'
    }, {
        'code': 'G402005',
        'category': 'UNDERGROUND ELECTRIC CONDUCTORS',
        'definition': 'Includes conductors for underground electrical distribution to lighting systems.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of conductor'
    }, {
        'code': 'G402006',
        'category': 'DUCTBANKS, MANHOLES & HANDHOLES',
        'definition': 'Includes all components used in conjunction with exterior lighting.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of ductbanks and access points'
    }, {
        'code': 'G402007',
        'category': 'GROUNDING SYSTEMS',
        'definition': 'Grounding systems used in conjunction with exterior lighting.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of systems'
    }, {
        'code': 'G4030',
        'category': 'SITE COMMUNICATION AND SECURITY',
        'definition': 'This system includes cables, ductbanks, manholes, and all other equipment required to support exterior communication and alarm systems.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of distribution'
    }, {
        'code': 'G403001',
        'category': 'TELECOMMUNICATIONS SYSTEMS',
        'definition': 'Includes all components, cables, and equipment used in conjunction with exterior telephone systems.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of distribution'
    }, {
        'code': 'G403002',
        'category': 'CABLE TV SYSTEMS (CATV)',
        'definition': 'Includes all components, cables, and equipment used in conjunction with exterior cable TV systems.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of distribution'
    }, {
        'code': 'G403003',
        'category': 'CABLES & WIRING',
        'definition': 'Includes cables, wiring, and equipment used in conjunction with exterior security systems.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of conductor'
    }, {
        'code': 'G403004',
        'category': 'DUCTBANKS, MANHOLES & HANDHOLES',
        'definition': 'Includes ductbank, manholes, and handholes used in conjunction with exterior security systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of ductbanks and access points'
    }, {
        'code': 'G403005',
        'category': 'TOWERS, POLES & STANDS',
        'definition': 'Includes towers, poles, stands, and equipment used in conjunction with exterior security systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of towers, poles and stands'
    }, {
        'code': 'G403006',
        'category': 'TV CAMERAS & MONITORS',
        'definition': 'Includes cameras, monitors, and components used in conjunction with exterior security systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of cameras and monitors'
    }, {
        'code': 'G403007',
        'category': 'ELECTRONIC SECURITY SYSTEMS (ESS)',
        'definition': 'Includes components and systems used in conjunction with exterior security systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of systems'
    }, {
        'code': 'G403008',
        'category': 'OTHER COMMUNICATION & ALARM',
        'definition': 'Includes all components, cables, and equipment used in conjunction with other special communication and alarm systems not defined above.'
    }, {
        'code': 'G403009',
        'category': 'GROUNDING SYSTEMS',
        'definition': 'Includes grounding systems used in conjunction with exterior security systems.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of systems'
    }, {
        'code': 'G403090',
        'category': 'OTHER SECURITY SYSTEMS',
        'definition': 'Includes all components and equipment used in conjunction with special security systems not defined above.'
    }, {
        'code': 'G4090',
        'category': 'OTHER SITE ELECTRICAL UTILITIES',
        'definition': 'This system includes alternate energy sources. This system also includes sacrificial anodes, induced current conductors, and components used in conjunction with cathodic protection.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of conductor'
    }, {
        'code': 'G409001',
        'category': 'SACRIFICIAL ANODE CATHODIC PROTECTION SYSTEM',
        'definition': 'Includes all components required in conjunction with sacrificial anode system.',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of anodes'
    }, {
        'code': 'G409002',
        'category': 'INDUCED CURRENT CATHODIC PROTECTION SYSTEM',
        'definition': 'Includes conductors and termination required for cathodic protection.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of conductor'
    }, {
        'code': 'G409003',
        'category': 'EMERGENCY POWER GENERATION',
        'imperial_units': 'KVA',
        'metric_units': 'KVA',
        'quantity_definition': 'Total rated capacity'
    }, {
        'code': 'G409090',
        'category': 'OTHER CATHODIC PROTECTION',
        'definition': 'Includes components and equipment used in conjunction with other cathodic protection systems not defined above.'
    }, {
        'code': 'G90',
        'category': 'OTHER SITE CONSTRUCTION',
        'definition': 'Other site construction includes service and pedestrian tunnels, bridges, railroad spurs, and snow melting systems.',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'G9010',
        'category': 'SERVICE AND PEDESTRIAN TUNNELS',
        'definition': 'This assembly includes service and pedestrian tunnels.'
    }, {
        'code': 'G901001',
        'category': 'CONSTRUCTION OF SERVICE AND PEDESTRIAN TUNNELS',
        'definition': 'This assembly includes construction of service and pedestrian tunnels.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of tunnel'
    }, {
        'code': 'G901002',
        'category': 'PREFABRICATED SERVICE AND PEDESTRIAN TUNNELS',
        'definition': 'This assembly includes prefabricated service and pedestrian tunnels.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of tunnel'
    }, {
        'code': 'G9090',
        'category': 'OTHER SITE CONSTRUCTION',
        'definition': 'Other site construction includes bridges, railroad spurs and snow melting systems.'
    }, {
        'code': 'G909001',
        'category': 'BRIDGES',
        'definition': 'Bridges included here are typically small spans or overpasses that are not meant to be used to estimate spans over large bodies of water. Options exist for cast-in-place concrete T-beam, precast I-beam, precast box, concrete and steel composite, laminated timber deck bridge structures.',
        'imperial_units': 'SY',
        'metric_units': 'M2',
        'quantity_definition': 'Area of structure'
    }, {
        'code': 'G909002',
        'category': 'RAILROAD SPURS',
        'definition': 'Railroad assemblies exist for 110, 115, and 132 lb. tracks and ties. Turnouts, roadway crossings, derailleurs, stops, and bumpers are also included.',
        'imperial_units': 'LF',
        'metric_units': 'M',
        'quantity_definition': 'Length of track'
    }, {
        'code': 'G909003',
        'category': 'SNOW MELTING SYSTEMS',
        'imperial_units': 'EA',
        'metric_units': 'EA',
        'quantity_definition': 'Number of systems'
    }, {
        'code': 'G909090',
        'category': 'OTHER SPECIAL CONSTRUCTION',
        'definition': 'Any special construction not covered in the above categories.'
    }, {
        'code': 'H',
        'category': 'WATERFRONT'
    }, {
        'code': 'H10',
        'category': 'WATERFRONT STRUCTURES',
        'definition': 'Waterfront Structures including wharves, piers, dolphins, trestles, and other structures and appurtenances necessary for the safe mooring of vessels and to support waterfront operations.',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'H1010',
        'category': 'SUBSTRUCTURE',
        'definition': 'This assembly includes substructure components for waterfront structures, such as pile foundations, pile caps, quays, relieving platforms, revetments, seawalls, boat ramps, cut-off walls, firewalls, and hanging panels.'
    }, {
        'code': 'H101001',
        'category': 'PILE FOUNDATIONS',
        'imperial_units': 'VLF',
        'metric_units': 'VM',
        'quantity_definition': 'Length of piles'
    }, {
        'code': 'H101002',
        'category': 'PILE CAPS'
    }, {
        'code': 'H101003',
        'category': 'QUAYS'
    }, {
        'code': 'H101004',
        'category': 'RELIEVING PLATFORMS'
    }, {
        'code': 'H101005',
        'category': 'REVETMENTS'
    }, {
        'code': 'H101006',
        'category': 'SEAWALLS'
    }, {
        'code': 'H101007',
        'category': 'BOAT RAMPS'
    }, {
        'code': 'H101008',
        'category': 'CUT-OFF WALLS'
    }, {
        'code': 'H101009',
        'category': 'FIREWALLS AND HANGING PANELS'
    }, {
        'code': 'H101090',
        'category': 'OTHER SUBSTRUCTURE COMPONENTS'
    }, {
        'code': 'H1020',
        'category': 'SUPERSTRUCTURE',
        'definition': 'This assembly includes superstructure components for waterfront structures, such as beams and girders, columns, utility enclosures, and other features that support the operation deck area.'
    }, {
        'code': 'H102001',
        'category': 'BEAMS AND GIRDERS'
    }, {
        'code': 'H102002',
        'category': 'COLUMNS'
    }, {
        'code': 'H102003',
        'category': 'UTILITY ENCLOSURES'
    }, {
        'code': 'H102090',
        'category': 'OTHER SUPERSTRUCTURE ELEMENTS'
    }, {
        'code': 'H1030',
        'category': 'DECK',
        'definition': 'This assembly includes the components for the deck, including elevated deck, on-grade deck, deck overlays, curbs and bullrails, mooring hardware foundation, high mast lighting foundations, utility mounds, expansion joints, guard post and railings, paint striping and other related features.'
    }, {
        'code': 'H103001',
        'category': 'DECK'
    }, {
        'code': 'H103002',
        'category': 'ON-GRADE SLAB'
    }, {
        'code': 'H103003',
        'category': 'DECK OVERLAY'
    }, {
        'code': 'H103004',
        'category': 'CURBS AND BULLRAILS'
    }, {
        'code': 'H103005',
        'category': 'MOORING FOUNDATIONS'
    }, {
        'code': 'H103006',
        'category': 'HIGH MAST LIGHTING FOUNDATIONS'
    }, {
        'code': 'H103007',
        'category': 'UTILITY MOUNDS'
    }, {
        'code': 'H103008',
        'category': 'EXPANSION JOINTS'
    }, {
        'code': 'H103009',
        'category': 'GUARD POSTS AND RAILING'
    }, {
        'code': 'H103010',
        'category': 'PAINT STRIPING'
    }, {
        'code': 'H103090',
        'category': 'OTHER DECK COMPONENTS'
    }, {
        'code': 'H1040',
        'category': 'MOORING AND BERTHING SYSTEM',
        'definition': 'This assembly includes the components for the mooring hardware and fendering systems, including foundations, anchor bolts, and support systems.'
    }, {
        'code': 'H104001',
        'category': 'PRIMARY FENDER SYSTEM'
    }, {
        'code': 'H104002',
        'category': 'SECONDARY FENDER SYSTEM'
    }, {
        'code': 'H104003',
        'category': 'CORNER FENDER SYSTEM'
    }, {
        'code': 'H104004',
        'category': 'DOLPHINS'
    }, {
        'code': 'H104005',
        'category': 'MOORING HARDWARE'
    }, {
        'code': 'H104090',
        'category': 'OTHER MOORING AND BERTHING COMPONENTS'
    }, {
        'code': 'H1050',
        'category': 'APPURTENANCES',
        'definition': 'This assembly includes the appurtenances such as handrails, brows, cable booms, floats, safety ladders, life rings, oil containment booms, and other similar features.',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'H20',
        'category': 'GRAVING DRYDOCKS',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'H30',
        'category': 'COASTAL PROTECTION',
        'definition': 'Coastal Protection System consists of all waterfront breakwaters, wave protection armor, slope protection, revetments, and other features necessary and required for the protection of waterfront facilities from damage by wave, tide and current.',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'H3010',
        'category': 'WAVE PROTECTION',
        'definition': 'This assembly includes required wave protection features, such as breakwaters, wave protection armor for slope protection, revetment and scour protection.'
    }, {
        'code': 'H301001',
        'category': 'WAVE PROTECTION ARMORS'
    }, {
        'code': 'H301002',
        'category': 'BREAKWATERS'
    }, {
        'code': 'H3020',
        'category': 'SLOPE PROTECTION',
        'definition': 'This assembly includes required slope protection features, such as revetment or embankment dikes.'
    }, {
        'code': 'H302001',
        'category': 'ROCK REVETMENTS'
    }, {
        'code': 'H302002',
        'category': 'GRANULAR FILL REVETMENTS'
    }, {
        'code': 'H302003',
        'category': 'COMBINED ROCK AND GRANULAR FILL REVETMENTS'
    }, {
        'code': 'H40',
        'category': 'NAVIGATION DREDGING AND RECLAMATION',
        'definition': 'Navigation Dredging and Reclamation System consists of all dredging of navigation channels, approaches, turning basins, and berthing areas near piers, wharves, dolphins, and reclamation as necessary to navigate the vessels to the berths and produce reclaimed land to support construction of the waterfront facilities.',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'H4010',
        'category': 'DREDGING'
    }, {
        'code': 'H4020',
        'category': 'DREDGING DISPOSAL'
    }, {
        'code': 'H402001',
        'category': 'OCEAN DISPOSAL'
    }, {
        'code': 'H402002',
        'category': 'NEW CONFINED DISPOSAL FACILITIES'
    }, {
        'code': 'H402003',
        'category': 'EXISTING CONFINED DISPOSAL FACILITIES'
    }, {
        'code': 'H4030',
        'category': 'RECLAMATION'
    }, {
        'code': 'H50',
        'category': 'WATERFRONT UTILITIES',
        'definition': 'The Waterfront Utility System consists of civil/mechanical utilities, electrical utilities, and fire protection to be installed on waterfront structures',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'H5010',
        'category': 'CIVIL/MECHANICAL UTILITIES'
    }, {
        'code': 'H501001',
        'category': 'POTABLE WATER'
    }, {
        'code': 'H501002',
        'category': 'SALTWATER'
    }, {
        'code': 'H501003',
        'category': 'SANITARY SEWER'
    }, {
        'code': 'H501004',
        'category': 'BILGE AND OILY WASTE'
    }, {
        'code': 'H501005',
        'category': 'STEAM'
    }, {
        'code': 'H501006',
        'category': 'COMPRESSED AIR'
    }, {
        'code': 'H501090',
        'category': 'OTHER CIVIL/MECHANICAL UTILITIES'
    }, {
        'code': 'H501091',
        'category': 'MISCELLANEOUS MATERIAL'
    }, {
        'code': 'H5020',
        'category': 'ELECTRICAL UTILITIES'
    }, {
        'code': 'H502001',
        'category': 'POWER DISTRIBUTION SYSTEM'
    }, {
        'code': 'H502002',
        'category': 'TELECOMMUNICATION SYSTEM'
    }, {
        'code': 'H502003',
        'category': 'LIGHTING SYSTEMS'
    }, {
        'code': 'H502004',
        'category': 'LIGHTNING PROTECTION SYSTEM'
    }, {
        'code': 'H502005',
        'category': 'POWER BOOMS'
    }, {
        'code': 'H502090',
        'category': 'OTHER ELECTRICAL UTILITIES'
    }, {
        'code': 'H5030',
        'category': 'WATERFRONT FIRE PROTECTION'
    }, {
        'code': 'H503001',
        'category': 'FIRE PROTECTION WATER DISTRIBUTION SYSTEM'
    }, {
        'code': 'H503002',
        'category': 'FIRE ALARM'
    }, {
        'code': 'H60',
        'category': 'WATERFRONT DEMOLITION',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'H6010',
        'category': 'IN OR OVER-WATER DEMOLITION'
    }, {
        'code': 'H6020',
        'category': 'NON IN OR OVER-WATER DEMOLITION'
    }, {
        'code': 'H6030',
        'category': 'HAZARDOUS COMPONENTS ABATEMENT'
    }, {
        'code': 'H70',
        'category': 'WATERFRONT ATFP',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }, {
        'code': 'H7010',
        'category': 'WATERSIDE ATFP'
    }, {
        'code': 'H7020',
        'category': 'LANDSIDE ATFP'
    }, {
        'code': 'Z',
        'category': 'GENERAL',
        'definition': 'The common or general requirements from the Performance Technical Specification Sections.',
        'imperial_units': 'LS',
        'metric_units': 'LS'
    }
]


def import_uniformat() -> None:
    with transaction.atomic():
        ids: dict[str, Uniformat] = {}
        for entry in uniformat_data:
            code = entry['code']
            parent = {} if len(code) == 1 else {'parent': ids[code[:-2]]}
            ids[code] = Uniformat.objects.create(**entry, **parent)

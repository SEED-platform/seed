# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from typing_extensions import TypedDict


class TKBLEntry(TypedDict):
    name: str
    url: str


class TKBL(TypedDict):
    estcp: dict[str, list[TKBLEntry]]
    sftool: dict[str, list[TKBLEntry]]


scope_one_emission_codes = {
    "D201006",
    "D202003",
    "D301002",
    "D301003",
    "D301090",
    "D302001",
    "D302002",
    "D302003",
    "D302004",
    "D302090",
    "D303001",
    "D303002",
    "D303090",
    "D304008",
    "D305001",
    "D305002",
    "D305006",
    "D305090",
    "D309002",
    "D309090",
}


tkbl_data: TKBL = {
    "estcp": {
        "D202003": [
            {
                "name": "Thermally Assisted High Temperature Heat Pump",
                "url": "https://serdp-estcp.mil/projects/details/549e13ec-eacd-4224-8e61-02e1fbb206fd",
            },
            {
                "name": "Demonstration of NoFoam System Technology for Aircraft Hangar and Fuel Farm Fire Suppression Foam System",
                "url": "https://serdp-estcp.mil/projects/details/87d6af3d-76fb-45d3-8f19-6909c8ca1dc7",
            },
        ],
        "D209005": [
            {
                "name": "PFAS-Free Foam / Compressed Air Foam, Fire Suppression Alternative",
                "url": "https://serdp-estcp.mil/projects/details/8775c73d-ab6e-4f79-a336-b2aa9adfd57e",
            },
            {
                "name": "Validation of PFAS-Free Fire Suppression Alternatives (FF_FSA) against Military Specifications",
                "url": "https://serdp-estcp.mil/projects/details/164cac28-0322-4d7a-8980-80a1146b5afa",
            },
            {
                "name": "Energy Reduction Using Epoxy Coatings for Sealing Leaking Compressed Air Systems",
                "url": "https://serdp-estcp.mil/projects/details/3d18f749-aa14-4bb9-b492-cd9e2d598768",
            },
            {
                "name": "In-Situ Shipboard Heat Exchanger Cleaning and Maintenance Using Innovative i2 Bubble Infusion Technology",
                "url": "https://serdp-estcp.mil/projects/details/495070cb-d6dc-42d3-9c3a-d9af8ee5ab6c",
            },
            {
                "name": "Validation of Fluorine-free AFFF against Military Specification Performance Criteria",
                "url": "https://serdp-estcp.mil/projects/details/38fca959-6af3-41bb-a9cb-88034cc44f37",
            },
            {
                "name": "Development and Delivery of Point-of-use Additives for PFAS-Free Fire Suppressants for Military Use",
                "url": "https://serdp-estcp.mil/projects/details/e5c807c8-f6c5-4270-8528-fa05ae2bd134",
            },
        ],
        "D209090": [
            {
                "name": "Demonstration and Validation of Automated Digital Videography for Inventory and Monitoring of Vertebrate Populations",
                "url": "https://serdp-estcp.mil/projects/details/f89110a3-a411-4265-8908-fefd1bfe0c5c",
            },
            {
                "name": "Isocyanate-Free Organosilane Polymers for Specialty Aircraft Coatings",
                "url": "https://serdp-estcp.mil/projects/details/aae09135-f7a8-4d6a-a44a-5c2bd6beb2e7",
            },
        ],
        "D301005": [
            {
                "name": "Building Integrated Photovoltaic Roofs for Sustainability and Energy Efficiency",
                "url": "https://serdp-estcp.mil/projects/details/3d550e39-5159-40ad-a399-a3c33adacfeb",
            },
            {
                "name": "A Liquid-Desiccant Outdoor Air Conditioner for Low-Electricity Humidity Control",
                "url": "https://serdp-estcp.mil/projects/details/a0ad199f-9a8a-4177-b092-30153ba1e48a",
            },
            {
                "name": "Demonstration of a Solar Thermal Combined Heating, Cooling and Hot Water System Utilizing an Adsorption Chiller for DoD Installations",
                "url": "https://serdp-estcp.mil/projects/details/6ba59fc7-50ef-41f9-95f9-ceaa719940f4",
            },
            {
                "name": "Distributed Power Systems for Sustainable Energy Resources",
                "url": "https://serdp-estcp.mil/projects/details/7aedbf71-3138-49f7-a678-501323008c2d",
            },
            {
                "name": "A Self-Sustaining Solar-Bio-Nano-Based Wastewater Treatment System for Forward Operating Bases",
                "url": "https://serdp-estcp.mil/projects/details/5b49b555-0a81-4033-a040-8de2d1caf42a",
            },
            {
                "name": "Low Energy Baffled Bioreactor-Based Water Re-use System for Energy and Water Security",
                "url": "https://serdp-estcp.mil/projects/details/67914324-01cd-4687-8399-e3f4e3987a79",
            },
            {
                "name": "Demonstration of a Concentrating Photovoltaic System for Distributed, Low-Cost Power Production",
                "url": "https://serdp-estcp.mil/projects/details/f6db7eee-1742-47e7-85b8-21213b7cbf66",
            },
            {
                "name": "Solar Air Heating Metal Roofing for Re-Roofing, New Construction, and Retrofit",
                "url": "https://serdp-estcp.mil/projects/details/ca3992ca-db8b-4317-9395-dc8156efaae5",
            },
        ],
        "D301006": [
            {
                "name": "Middleware Solution for Standardization and Analysis of Disparate Facility Infrastructure",
                "url": "https://serdp-estcp.mil/projects/details/b0d58952-c887-4de4-baeb-338638e5a22b",
            },
            {
                "name": "Validating the Cimetrics Analytika HVAC Commissioning Platform",
                "url": "https://serdp-estcp.mil/projects/details/faccea92-8a9b-4dab-9051-f6d91ef6e28e",
            },
            {
                "name": "Navigator Cloud-Based Predictive Analytics",
                "url": "https://serdp-estcp.mil/projects/details/0ac40589-c25a-46f7-88d6-a755087ab0bb",
            },
            {
                "name": "Fault Detection & Diagnostics (FDD) Demonstration at DoD Facilities",
                "url": "https://serdp-estcp.mil/projects/details/8a08337f-5ede-451d-a16e-90c039d6a40a",
            },
            {
                "name": "Optimizing Facility Operations by Applying Machine Learning to the Army Reserve Enterprise Building Control System",
                "url": "https://serdp-estcp.mil/projects/details/518e4d87-3ffc-4f49-a0bc-9ee556e1d1bd",
            },
            {
                "name": "Better Buildings, Smaller Bootprint - Smart Building Program for DoD",
                "url": "https://serdp-estcp.mil/projects/details/4bbf4ff7-a112-455e-bb59-e90820bfc547",
            },
        ],
        "D301090": [
            {
                "name": "Patch Management/Continuous Monitoring and Detection for Energy Management Control Systems",
                "url": "https://serdp-estcp.mil/projects/details/131e6643-cf95-45e7-a162-5ebd7d2fa031",
            }
        ],
        "D302001": [
            {
                "name": "Packaged Hybrid Combined Heat and Power (CHP) and Hot Water Boiler Solution for Barrack, Dormitory, or Food Service Energy Resiliency",
                "url": "https://serdp-estcp.mil/projects/details/017fd8c0-5b57-4cd3-b43e-43cd3c10b9c5",
            },
            {
                "name": "High Efficiency and Reduced Emissions Boiler System for Steam, Heat, and Processing",
                "url": "https://serdp-estcp.mil/projects/details/d4f06c7f-44af-4212-b25c-0cb8e49a1986",
            },
            {
                "name": "Characterization of Particulate Emission: Size Characterization and Chemical Speciation",
                "url": "https://serdp-estcp.mil/projects/details/e2320922-3046-4062-b556-91c5f9c0c02c",
            },
            {
                "name": "Development of a Catalyzed Ceramic Filter for Combined PM2.5 Removal and VOC and CO Oxidation",
                "url": "https://serdp-estcp.mil/projects/details/99fa0ec2-e182-425f-851c-75333de96e0f",
            },
        ],
        "D302002": [
            {
                "name": "A Quantum Chemical - Machine Learning Approach for the Prediction of Thermal PFAS Destruction",
                "url": "https://serdp-estcp.mil/projects/details/f7aa8a9a-e8e2-46cc-ae24-e7cef899ffd5",
            }
        ],
        "D302004": [
            {
                "name": "Central Plant Optimization for Waste Energy Reduction",
                "url": "https://serdp-estcp.mil/projects/details/739d67ad-03e0-4ae0-ac25-b7ab5db3bdd9",
            }
        ],
        "D302090": [
            {
                "name": "In Situ Thermal Remediation of DNAPL Source Zones",
                "url": "https://serdp-estcp.mil/projects/details/62d59c56-e1ca-4a69-a2a0-5cc85a662cea",
            }
        ],
        "D303001": [
            {
                "name": "Demonstration and Testing of an Energy Efficiency Ratio (EER) Optimizer System for DX Air-Conditioners",
                "url": "https://serdp-estcp.mil/projects/details/b5391992-fc2f-4a3e-894e-8d691eb5ae69",
            },
            {
                "name": "Next Generation Advanced High-efficiency DX Air Conditioner Demonstration",
                "url": "https://serdp-estcp.mil/projects/details/23e70e9b-c621-4dc2-a255-f3eb59acf585",
            },
            {
                "name": "Solving Low Delta T Syndrome in Hydronic Systems",
                "url": "https://serdp-estcp.mil/projects/details/50799bb9-2566-4352-b540-efbc649aaf2b",
            },
            {
                "name": "Utility Energy Service Contracts - The Pathway to Demonstrate Energy Efficiency Technologies",
                "url": "https://serdp-estcp.mil/projects/details/908f8892-f39d-47e1-94e9-b1ac1926b8ee",
            },
        ],
        "D303002": [
            {
                "name": "Demonstration and Testing of ClimaStat® for Improved DX Air-Conditioning Efficiency",
                "url": "https://serdp-estcp.mil/projects/details/e130c118-7879-4a02-b54c-1cb2cdda29bd",
            },
            {
                "name": "Performance-Based Maintenance Pilot for Unitary DX HVAC Equipment",
                "url": "https://serdp-estcp.mil/projects/details/c8dde0c4-f087-4083-9a9f-56c9cce92d21",
            },
        ],
        "D304001": [
            {
                "name": "Naval District Washington Steam Trap Monitoring System",
                "url": "https://serdp-estcp.mil/projects/details/017cbf1b-3245-4e51-9008-d5f6dab9f4ef",
            },
            {
                "name": "Underground Thermal Energy Storage (UTES) as a DoD facilities UESC Energy Conservation Measure",
                "url": "https://serdp-estcp.mil/projects/details/e4e85a3d-8de1-470c-9df0-d65e62410137",
            },
            {
                "name": "Underground Thermal Energy Storage (UTES) Technology Transfer",
                "url": "https://serdp-estcp.mil/projects/details/2d9e285e-c16c-4815-b968-4939883d0a07",
            },
            {
                "name": "Utility Energy Service Contracts - The Pathway to Demonstrate Energy Efficiency Technologies",
                "url": "https://serdp-estcp.mil/projects/details/908f8892-f39d-47e1-94e9-b1ac1926b8ee",
            },
            {
                "name": "Geothermal District Heating and Cooling in Cold Regions",
                "url": "https://serdp-estcp.mil/projects/details/16630626-64f7-4546-88b7-5b6807c21d78",
            },
        ],
        "D304002": [
            {
                "name": "Naval District Washington Steam Trap Monitoring System",
                "url": "https://serdp-estcp.mil/projects/details/017cbf1b-3245-4e51-9008-d5f6dab9f4ef",
            }
        ],
        "D304003": [
            {
                "name": "Solar CHP—Combined Heat and Power Using the Infinia Concentrated Solar Power System",
                "url": "https://serdp-estcp.mil/projects/details/f5de7589-faad-4327-9612-6eaf6e6d4c3e",
            },
            {
                "name": "Climate Management System for Corrosion Control Facilities",
                "url": "https://serdp-estcp.mil/projects/details/01a8bfd2-db1d-448c-838a-ad2d184a5dcf",
            },
            {
                "name": "IoT Smart Shower System to Reduce Shower Utility Costs by 20% and Improve Water Resilience in DoD Facilities",
                "url": "https://serdp-estcp.mil/projects/details/a970e205-8993-4a2c-9b88-30d34ae8d612",
            },
        ],
        "D304008": [
            {
                "name": "Nanofiber-based Low Energy Consuming HVAC Air Filters",
                "url": "https://serdp-estcp.mil/projects/details/fe76919d-36af-4ad8-b601-ccdc37c212ba",
            },
            {
                "name": "Technology Transfer: Converting Multizone HVAC Systems from Constant to Variable Volume",
                "url": "https://serdp-estcp.mil/projects/details/674e4412-fb09-47ed-b2f7-b6423cb43c7d",
            },
            {
                "name": "High Efficiency Dehumidification System (HEDS)",
                "url": "https://serdp-estcp.mil/projects/details/12480881-4c09-4157-90d8-c3487b41241b",
            },
            {"name": "EW-201344 Follow-on", "url": "https://serdp-estcp.mil/projects/details/862d29ba-a4ee-4a5c-8ee4-7923106d6cc7"},
            {
                "name": "Converting Constant Volume, Multizone Air Handling Systems to Energy-Efficient Variable Air Volume Multizone Systems",
                "url": "https://serdp-estcp.mil/projects/details/e1bed4b6-7123-4bc6-8ef5-fd2ea882913d",
            },
            {
                "name": "High Efficiency Dehumidification System - Additional Proof of Concept",
                "url": "https://serdp-estcp.mil/projects/details/f9dca947-8ddb-4821-a5a8-ffa9c68c1f5f",
            },
            {
                "name": "Demonstration of Energy Savings in Commercial Buildings for Tiered Trim and Respond Method in Resetting Static Pressure for VAV Systems",
                "url": "https://serdp-estcp.mil/projects/details/9d044c37-5ee4-4489-8ce7-4cef0f9c59cc",
            },
            {
                "name": "Solving Low Delta T Syndrome in Hydronic Systems",
                "url": "https://serdp-estcp.mil/projects/details/50799bb9-2566-4352-b540-efbc649aaf2b",
            },
            {
                "name": "Advanced HVAC Load Management using Cascade Controls Integrating Chillers, Air Handling Units, and Terminal Boxes",
                "url": "https://serdp-estcp.mil/projects/details/89bfd0a2-b4c0-49dc-bcd4-1bbbd00fb228",
            },
        ],
        "D306001": [
            {
                "name": "Optimizing Operational Efficiency: Integrating Energy Information Systems and Model-Based Diagnostics",
                "url": "https://serdp-estcp.mil/projects/details/d4f06c7f-44af-4212-b25c-0cb8e49a1986",
            },
            {
                "name": "Intelligent Building Management with Holistic Digital Lighting",
                "url": "https://serdp-estcp.mil/projects/details/625a70d1-a751-4889-b41c-997191a79f41",
            },
            {
                "name": "Systems Approach to Improved Facility Energy Performance",
                "url": "https://serdp-estcp.mil/projects/details/e130c118-7879-4a02-b54c-1cb2cdda29bd",
            },
            {
                "name": "Exhaust Hood and Makeup Air Optimization",
                "url": "https://serdp-estcp.mil/projects/details/1276d6f1-16ba-436e-a032-3314f3f79c38",
            },
            {
                "name": "NextGen AC Package Unit as a DoD UESC/ESPC Energy Conservation Measure",
                "url": "https://serdp-estcp.mil/projects/details/4182fba3-1ecc-4239-bcd2-b003102f1734",
            },
            {
                "name": "Central Plant Optimization for Waste Energy Reduction",
                "url": "https://serdp-estcp.mil/projects/details/fe76919d-36af-4ad8-b601-ccdc37c212ba",
            },
            {
                "name": "Demonstration and Testing of ClimaStat® for Improved DX Air-Conditioning Efficiency",
                "url": "https://serdp-estcp.mil/projects/details/9c14701b-cf05-4e3b-a66d-6af05ce798aa",
            },
            {
                "name": "Intelligent HVAC Load Management for Energy Efficient and Disaster Resilient Building Operations",
                "url": "https://serdp-estcp.mil/projects/details/739d67ad-03e0-4ae0-ac25-b7ab5db3bdd9",
            },
            {
                "name": "Technology Transfer: Converting Multizone HVAC Systems from Constant to Variable Volume",
                "url": "https://serdp-estcp.mil/projects/details/169b9fe9-1c95-47c2-b6eb-0aa46f8e0d23",
            },
            {
                "name": "Demonstration of a Building Automation System Embedded Performance Degradation Detector Using Virtual Water/Air Flow Meters",
                "url": "https://serdp-estcp.mil/projects/details/9d044c37-5ee4-4489-8ce7-4cef0f9c59cc",
            },
            {
                "name": "Solving Low Delta T Syndrome in Hydronic Systems",
                "url": "https://serdp-estcp.mil/projects/details/50799bb9-2566-4352-b540-efbc649aaf2b",
            },
            {
                "name": "Comprehensive Information Transfer Approaches for Advanced Building Controls and Management Projects",
                "url": "https://serdp-estcp.mil/projects/details/c97ec8df-5010-4500-a8cc-d8e44a21e852",
            },
            {
                "name": "High Efficiency and Reduced Emissions Boiler System for Steam, Heat, and Processing",
                "url": "https://serdp-estcp.mil/projects/details/3b6a1d7d-6403-40e0-8dc5-af4f41bdc3bf",
            },
            {
                "name": "Energy Performance Monitoring and Optimization System for DoD Campuses",
                "url": "https://serdp-estcp.mil/projects/details/e1bed4b6-7123-4bc6-8ef5-fd2ea882913d",
            },
            {
                "name": "Converting Constant Volume, Multizone Air Handling Systems to Energy-Efficient Variable Air Volume Multizone Systems",
                "url": "https://serdp-estcp.mil/projects/details/55639512-d0a9-4b53-a6d5-15da7fcd00c5",
            },
            {
                "name": "Validating the COOLNOMIX AC and Refrigeration Compressor Control Retrofit",
                "url": "https://serdp-estcp.mil/projects/details/c041a4d7-5582-41b7-bb2d-48f466929940",
            },
            {
                "name": "Demonstration of Energy Savings in Commercial Buildings for Tiered Trim and Respond Method in Resetting Static Pressure for VAV Systems",
                "url": "https://serdp-estcp.mil/projects/details/d9814396-3d00-4ed8-94c6-7fa345cdfb7e",
            },
        ],
        "D306090": [
            {
                "name": "Affordable Multi-Energy Source and Control Solutions for National Guard Sites",
                "url": "https://serdp-estcp.mil/projects/details/7f258a1d-ae79-472b-b88b-5544a58af444",
            }
        ],
        "D509006": [
            {
                "name": "Utilization of Advanced Conservation Voltage Reduction (CVR) for Energy Reduction on DoD Installations",
                "url": "https://serdp-estcp.mil/projects/details/2d5092f7-9191-4503-affe-8f5c80d21cc6",
            },
            {
                "name": "Optimizing Facility Operations by Applying Machine Learning to the Army Reserve Enterprise Building Control System",
                "url": "https://serdp-estcp.mil/projects/details/6b6f5248-7a71-4bb1-b308-30af5e0ee424",
            },
            {
                "name": "Middleware Solution for Standardization and Analysis of Disparate Facility Infrastructure",
                "url": "https://serdp-estcp.mil/projects/details/970bc025-49bb-4d9c-bb2c-b267f3244b03",
            },
            {
                "name": "Fault Detection & Diagnostics (FDD) Demonstration at DoD Facilities",
                "url": "https://serdp-estcp.mil/projects/details/b0d58952-c887-4de4-baeb-338638e5a22b",
            },
            {
                "name": "Validating the Cimetrics Analytika HVAC Commissioning Platform",
                "url": "https://serdp-estcp.mil/projects/details/faccea92-8a9b-4dab-9051-f6d91ef6e28e",
            },
            {
                "name": "Navigator Cloud-Based Predictive Analytics",
                "url": "https://serdp-estcp.mil/projects/details/0ac40589-c25a-46f7-88d6-a755087ab0bb",
            },
            {
                "name": "Better Buildings, Smaller Bootprint - Smart Building Program for DoD",
                "url": "https://serdp-estcp.mil/projects/details/8a08337f-5ede-451d-a16e-90c039d6a40a",
            },
            {
                "name": "Advanced Micro-Grid Energy Management Coupled with Integrated Volt/VAR Control for Improved Energy Efficiency, Energy Security, and Power Quality at DoD Installations",
                "url": "https://serdp-estcp.mil/projects/details/518e4d87-3ffc-4f49-a0bc-9ee556e1d1bd",
            },
            {
                "name": "Wireless Platform for Energy-Efficient Building Control Retrofits",
                "url": "https://serdp-estcp.mil/projects/details/1130b09f-f864-4478-aa85-55dc0636f204",
            },
            {
                "name": "Scalable Deployment of Advanced Building Energy Management Systems",
                "url": "https://serdp-estcp.mil/projects/details/d8445d89-4c7e-4406-b50a-aac5df1e1a37",
            },
            {
                "name": "Energy Performance Monitoring and Optimization System for DoD Campuses",
                "url": "https://serdp-estcp.mil/projects/details/625a70d1-a751-4889-b41c-997191a79f41",
            },
            {
                "name": "Integrated Control for Building Energy Management",
                "url": "https://serdp-estcp.mil/projects/details/fb09b3f2-6cce-4230-89de-0b659a14bd78",
            },
            {
                "name": "Collaborative Building Energy Management and Control",
                "url": "https://serdp-estcp.mil/projects/details/b59d0a83-13f8-4d9b-976f-7df0275abd5d",
            },
            {
                "name": "Demonstrating Enhanced Demand Response Program Participation for Naval District Washington",
                "url": "https://serdp-estcp.mil/projects/details/0d2cb915-d2f8-41cf-8a10-181f12373eec",
            },
            {
                "name": "Building Performance Optimization while Empowering Occupants toward Environmentally Sustainable Behavior through Continuous Monitoring and Diagnostics",
                "url": "https://serdp-estcp.mil/projects/details/8a98c395-71b3-4340-8c95-6d892d2e045f",
            },
            {
                "name": "Rapid Deployment of Optimal Control for Building HVAC Systems Using Innovative Software Tools and a Hybrid Heuristic/Model-Based Control Approach",
                "url": "https://serdp-estcp.mil/projects/details/1e7d6bb8-efad-4c50-8ec9-5c7b5d063a6a",
            },
            {
                "name": "Software-Defined Wireless Decentralized Building Management System",
                "url": "https://serdp-estcp.mil/projects/details/837e2279-2a13-45ea-8d60-ac7bcc08858b",
            },
            {
                "name": "Comprehensive Information Transfer Approaches for Advanced Building Controls and Management Projects",
                "url": "https://serdp-estcp.mil/projects/details/55639512-d0a9-4b53-a6d5-15da7fcd00c5",
            },
            {
                "name": "Applying Semantic Metadata Standardization Demonstration at DoD Facilities",
                "url": "https://serdp-estcp.mil/projects/details/b9d515fa-6924-4841-9eda-9e295df12144",
            },
            {
                "name": "Distributed Power Systems for Sustainable Energy Resources",
                "url": "https://serdp-estcp.mil/projects/details/7aedbf71-3138-49f7-a678-501323008c2d",
            },
            {
                "name": "Converged Energy Management Control System",
                "url": "https://serdp-estcp.mil/projects/details/8231ba53-0c6d-4a86-81ff-2f9fc1bb270b",
            },
            {
                "name": "NDW Cognitive Energy Management System",
                "url": "https://serdp-estcp.mil/projects/details/8b458c23-ca59-438b-a2d1-edae8b73c2b5",
            },
            {
                "name": "Secure Automated Microgrid Energy System",
                "url": "https://serdp-estcp.mil/projects/details/bc023678-f6ba-4057-a020-e9778586a863",
            },
            {
                "name": "Demonstration of a Building Automation System Embedded Performance Degradation Detector Using Virtual Water/Air Flow Meters",
                "url": "https://serdp-estcp.mil/projects/details/169b9fe9-1c95-47c2-b6eb-0aa46f8e0d23",
            },
            {
                "name": "Technologies Integration to Achieve Resilient, Low-Energy Military Installations",
                "url": "https://serdp-estcp.mil/projects/details/3defab5d-a177-41d5-b925-10757d80aa98",
            },
            {
                "name": "Demonstration of Intelligent Circuit Breakers for Energy Management, Verification, and Load Control",
                "url": "https://serdp-estcp.mil/projects/details/2a965401-d176-4bc7-834f-64d799b96ff1",
            },
            {
                "name": "Energy Management and Information Systems (EMIS) Technology Transfer",
                "url": "https://serdp-estcp.mil/projects/details/dbf4a2f5-cd52-4a09-bbe6-5ce71da68d86",
            },
            {
                "name": "Resilient Power Router for Energy Resiliency and Power Management",
                "url": "https://serdp-estcp.mil/projects/details/7c8c888a-18c7-4321-a306-60c68e936fed",
            },
            {
                "name": "Net-Zero Emissions through Tracking Building Performance Standards",
                "url": "https://serdp-estcp.mil/projects/details/9d24fb8b-170f-423f-a25a-ddc4351a8611",
            },
        ],
    },
    "sftool": {
        "B202001": [
            {
                "name": "Storm Windows",
                "url": "https://sftool.gov/greenprocurement/green-products/26/doors-windows/1827/storm-windows/0?addon=False",
            },
            {
                "name": "Window, High R Value",
                "url": "https://sftool.gov/greenprocurement/green-products/26/doors-windows/1578/window-high-r/0?addon=False",
            },
            {"name": "Windows", "url": "https://sftool.gov/greenprocurement/green-products/26/doors-windows/272/windows/0?addon=False"},
        ],
        "B2030": [{"name": "Doors", "url": "https://sftool.gov/greenprocurement/green-products/26/doors-windows/76/doors/0?addon=False"}],
        "D201001": [
            {"name": "Toilets", "url": "https://sftool.gov/greenprocurement/green-products/23/plumbing-systems/255/toilets/0?addon=False"}
        ],
        "D201002": [
            {"name": "Urinals", "url": "https://sftool.gov/greenprocurement/green-products/23/plumbing-systems/259/urinals/0?addon=False"}
        ],
        "D201004": [
            {
                "name": "Bathroom Sink Faucets & Accessories (Residential)",
                "url": "https://sftool.gov/greenprocurement/green-products/23/plumbing-systems/11/bathroom-sink-faucets-accessories-residential/0?addon=False",
            }
        ],
        "D201005": [
            {
                "name": "Showerheads",
                "url": "https://sftool.gov/greenprocurement/green-products/23/plumbing-systems/239/showerheads/0?addon=False",
            }
        ],
        "D202003": [
            {
                "name": "Commercial Gas Water Heaters",
                "url": "https://sftool.gov/greenprocurement/green-products/24/hvacmechanical/108/commercial-gas-water-heaters/0?addon=False",
            },
            {
                "name": "Residential Water Heaters",
                "url": "https://sftool.gov/greenprocurement/green-products/24/hvacmechanical/1378/residential-water-heaters/0?addon=False",
            },
        ],
        "D301005": [
            {
                "name": "Honeycomb Solar Thermal Collector",
                "url": "https://sftool.gov/greenprocurement/green-products/24/hvacmechanical/1747/honeycomb-solar-thermal-collector/0?addon=False",
            }
        ],
        "D302001": [
            {"name": "Boilers", "url": "https://sftool.gov/greenprocurement/green-products/24/hvacmechanical/1321/boilers/0?addon=False"}
        ],
        "D302002": [
            {"name": "Furnaces", "url": "https://sftool.gov/greenprocurement/green-products/24/hvacmechanical/107/furnaces/0?addon=False"}
        ],
        "D303001": [
            {"name": "Chillers", "url": "https://sftool.gov/greenprocurement/green-products/24/hvacmechanical/34/chillers/0?addon=False"}
        ],
        "D303002": [
            {
                "name": "Heat Pumps, Air-Source",
                "url": "https://sftool.gov/greenprocurement/green-products/24/hvacmechanical/6/heat-pumps-air-source/0?addon=False",
            }
        ],
        "D304007": [
            {
                "name": "Ventilation Fans",
                "url": "https://sftool.gov/greenprocurement/green-products/24/hvacmechanical/262/ventilation-fans/0?addon=False",
            }
        ],
        "D304008": [
            {
                "name": "Air Conditioning, Central",
                "url": "https://sftool.gov/greenprocurement/green-products/24/hvacmechanical/1322/air-conditioning-central/0?addon=False",
            },
            {
                "name": "Light Commercial Heating and Cooling",
                "url": "https://sftool.gov/greenprocurement/green-products/24/hvacmechanical/150/light-commercial-heating-cooling/0?addon=False",
            },
        ],
        "D305006": [
            {
                "name": "Air Conditioning, Room",
                "url": "https://sftool.gov/greenprocurement/green-products/24/hvacmechanical/232/air-conditioning-room/0?addon=False",
            }
        ],
        "D3060": [
            {
                "name": "Control Optimization System for Chiller Plants",
                "url": "https://sftool.gov/greenprocurement/green-products/24/hvacmechanical/1758/control-optimization-system-chiller-plants/0?addon=False",
            }
        ],
        "D306001": [
            {
                "name": "Smart Thermostats",
                "url": "https://sftool.gov/greenprocurement/green-products/24/hvacmechanical/1754/smart-thermostats/0?addon=False",
            }
        ],
        "D309002": [
            {
                "name": "Industrial Process Refrigeration Systems",
                "url": "https://sftool.gov/greenprocurement/green-products/14/refrigeration-systems/141/industrial-process-refrigeration-systems/0?addon=False",
            },
            {
                "name": "Very Low Temperature Refrigeration Systems",
                "url": "https://sftool.gov/greenprocurement/green-products/14/refrigeration-systems/263/low-temperature-refrigeration-systems/0?addon=False",
            },
        ],
        "D502002": [
            {
                "name": "Exterior Lighting",
                "url": "https://sftool.gov/greenprocurement/green-products/22/lighting-ceiling-fans/1408/exterior-lighting/0?addon=False",
            },
            {
                "name": "Fluorescent Luminaires",
                "url": "https://sftool.gov/greenprocurement/green-products/22/lighting-ceiling-fans/1410/fluorescent-luminaires/0?addon=False",
            },
            {
                "name": "LED Downlight Lamps for CFL Fixtures",
                "url": "https://sftool.gov/greenprocurement/green-products/22/lighting-ceiling-fans/1759/led-downlight-lamps-cfl-fixtures/0?addon=False",
            },
            {
                "name": "LED Fixtures with Integrated Controls",
                "url": "https://sftool.gov/greenprocurement/green-products/22/lighting-ceiling-fans/1738/led-fixtures-integrated-controls/0?addon=False",
            },
            {
                "name": "LED Luminaires, Commercial and Industrial",
                "url": "https://sftool.gov/greenprocurement/green-products/22/lighting-ceiling-fans/1739/led-luminaires-commercial-industrial/0?addon=False",
            },
            {
                "name": "Light Bulbs",
                "url": "https://sftool.gov/greenprocurement/green-products/22/lighting-ceiling-fans/1414/light-bulbs/0?addon=False",
            },
            {
                "name": "Light Fixtures",
                "url": "https://sftool.gov/greenprocurement/green-products/22/lighting-ceiling-fans/151/light-fixtures/0?addon=False",
            },
            {
                "name": "Linear LED Lighting Retrofits",
                "url": "https://sftool.gov/greenprocurement/green-products/22/lighting-ceiling-fans/1757/linear-led-lighting-retrofits/0?addon=False",
            },
        ],
        "D502003": [
            {
                "name": "Wireless Advanced Lighting Controls",
                "url": "https://sftool.gov/greenprocurement/green-products/22/lighting-ceiling-fans/1737/wireless-advanced-lighting-controls/0?addon=False",
            }
        ],
    },
}

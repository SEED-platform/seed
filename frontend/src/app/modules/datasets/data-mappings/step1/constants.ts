export const dataTypeMap: Record<string, { display: string; units: string }> = {
  None: { display: 'None', units: null },
  number: { display: 'Number', units: null },
  integer: { display: 'Integer', units: null },
  string: { display: 'Text', units: null },
  datetime: { display: 'Datetime', units: null },
  date: { display: 'Date', units: null },
  boolean: { display: 'Boolean', units: null },
  area: { display: 'Area', units: 'ft²' },
  eui: { display: 'EUI', units: 'kBtu/ft²/year' },
  geometry: { display: 'Geometry', units: null },
  ghg: { display: 'GHG', units: 'MtC02e/year' },
  ghg_intensity: { display: 'GHG Intensity', units: 'kgCO2e/ft²/year' },
  // water_use: { display: 'Water Use', units: 'kgal/year' },
  // wui: { display: 'Water Use Intensity', units: 'gal/ft²/year' },
}

const displayDataTypes = [
  'None',
  'Number',
  'Integer',
  'Text',
  'Datetime',
  'Date',
  'Boolean',
  'Area',
  'EUI',
  'Geometry',
  'GHG',
  'GHG Intensity',
] // 'Water Use', 'Water Use Intensity'
const dataTypes = ['None', 'number', 'integer', 'string', 'datetime', 'date', 'boolean', 'area', 'eui', 'geometry', 'ghg', 'ghg_intensity'] // 'water_use', 'wui'

export const displayToDataTypeMap: Record<string, string> = Object.fromEntries(displayDataTypes.map((k, i) => [k, dataTypes[i]]))

export const unitMap: Record<string, string[]> = {
  Area: ['ft²', 'm²'],
  EUI: ['kBtu/ft²/year', 'kWh/m²/year', 'GJ/m²/year', 'MJ/m²/year', 'kBtu/m²/year'],
  GHG: ['MtCO2e/year', 'kgCO2e/year'],
  'GHG Intensity': ['MtCO2e/ft²/year', 'kgCO2e/ft²/year', 'MtCO2e/m²/year', 'kgCO2e/m²/year'],
  'Water Use': ['kgal/year', 'gal/year', 'L/year'],
  'Water Use Intensity': ['kgal/ft²/year', 'gal/ft²/year', 'L/m²/year'],
}

export const dataTypeOptions = [
  'None',
  'Number',
  'Integer',
  'Text',
  'Datetime',
  'Date',
  'Boolean',
  'Area',
  'EUI',
  'Geometry',
  'GHG',
  'GHG Intensity',
  // 'Water Use',
  // 'Water Use Intensity',
]

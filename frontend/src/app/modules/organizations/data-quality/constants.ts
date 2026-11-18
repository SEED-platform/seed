export const CONDITIONS = [
  { key: 'include', value: 'Must Contain' },
  { key: 'exclude', value: 'Must Not Contain' },
  { key: 'not_null', value: 'Not Null' },
  { key: 'range', value: 'Range' },
  { key: 'required', value: 'Required' },
]

export const DATATYPE_LOOKUP = { 0: 'Number', 1: 'Text', 2: 'Date', 3: 'Year', 4: 'Area', 5: 'EUI' }

const allTypes = [
  { key: null, value: null },
  { key: 0, value: 'Number' },
  { key: 1, value: 'Text' },
  { key: 2, value: 'Date' },
  { key: 3, value: 'Year' },
  { key: 4, value: 'Area' },
  { key: 5, value: 'EUI' },
]
const textTypes = [
  { key: null, value: null },
  { key: 1, value: 'Text' },
]
const numericTypes = [
  { key: null, value: null },
  { key: 0, value: 'Number' },
  { key: 2, value: 'Date' },
  { key: 3, value: 'Year' },
  { key: 4, value: 'Area' },
  { key: 5, value: 'EUI' },
]

export const DATATYPES_BY_CONDITION: {
  exclude: typeof textTypes;
  include: typeof textTypes;
  not_null: typeof allTypes;
  range: typeof numericTypes;
  required: typeof allTypes;
} = {
  exclude: textTypes,
  include: textTypes,
  not_null: allTypes,
  range: numericTypes,
  required: allTypes,
}

export const INVENTORY_COLUMNS = ['enabled', 'field', 'condition', 'data_type', 'criteria', 'units', 'severity', 'status_label', 'actions']
export const GOAL_COLUMNS = ['enabled', 'condition', 'field', 'data_type', 'min', 'max', 'units', 'severity', 'status_label', 'actions']

export const SEVERITIES = [
  { key: 0, value: 'Error', class: 'bg-red-200' },
  { key: 1, value: 'Warning', class: 'bg-amber-200' },
  { key: 2, value: 'Valid', class: 'bg-green-200' },
]

export const UNITS = [
  { key: '', value: '' },
  { key: 'ft**2', value: 'ft²' },
  { key: 'm**2', value: 'm²' },
  { key: 'kBtu/ft**2/year', value: 'kBtu/ft²/yr' },
  { key: 'gal/ft**2/year', value: 'gal/ft²/yr' },
  { key: 'GJ/m**2/year', value: 'GJ/m²/yr' },
  { key: 'MJ/m**2/year', value: 'MJ/m²/yr' },
  { key: 'kWh/m**2/year', value: 'kWh/m²/yr' },
  { key: 'kBtu/m**2/year', value: 'kBtu/m²/yr' },
]

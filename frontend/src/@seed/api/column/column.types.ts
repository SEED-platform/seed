export type Column = {
  id: number;
  name: string;
  organization_id: number;
  table_name: 'PropertyState' | 'TaxLotState';
  merge_protection: 'Favor New' | 'Favor Existing';
  shared_field_type: 'None' | 'Public';
  column_name: string;
  is_extra_data: boolean;
  unit_name: null;
  unit_type: null;
  display_name: string;
  data_type:
    | 'number'
    | 'float'
    | 'integer'
    | 'string'
    | 'geometry'
    | 'datetime'
    | 'date'
    | 'boolean'
    | 'area'
    | 'eui'
    | 'ghg_intensity'
    | 'ghg'
    | 'wui'
    | 'water_use';
  is_matching_criteria: boolean;
  is_updating: boolean;
  geocoding_order: number;
  recognize_empty: boolean;
  comstock_mapping: string | null;
  column_description: string;
  derived_column: number | null;
  is_excluded_from_hash: boolean;
  related?: boolean;
  pinnedLeft?: boolean;
}

export type ColumnsResponse = {
  status: string;
  columns: Column[];
}

export type RenameColumnResponse = {
  success: boolean;
  message: string;
}

export type GenericColumn = {
  [key: string]: unknown;
  display_name: string;
  column_name: string;
}

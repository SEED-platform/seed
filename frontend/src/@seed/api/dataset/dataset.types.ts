// Subset type
export type ImportFile = {
  cached_first_row: string | null;
  cached_second_to_fifth_row: string | null;
  created: string;
  cycle: number;
  cycle_name?: string; // used in dataset.component ag-grid
  dataset: Dataset;
  deleted: boolean;
  file: string;
  id: number;
  import_record: number;
  mapping_done: boolean;
  matching_done: boolean;
  modified: string;
  num_rows: number;
  source_type: string;
  uploaded_filename: string;
}

// Subset type
export type Dataset = {
  deleted: boolean;
  name: string;
  app: 'seed';
  owner: number;
  access_level_instance: number;
  start_time: string;
  finish_time: string;
  created_at: string;
  updated_at: number;
  last_modified_by: string;
  matching_done: boolean;
  super_organization: number;
  id: number;
  model: 'data_importer.importrecord';
  importfiles?: ImportFile[];
}

export type ListDatasetsResponse = {
  status: 'success';
  datasets: Dataset[];
}

export type CountDatasetsResponse = {
  status: 'success';
  datasets_count: number;
}

export type DatasetResponse = {
  status: 'success';
  dataset: Dataset;
}

export type ImportFileResponse = {
  status: 'success';
  import_file: ImportFile;
}

export type DataMappingRow = {
  from_field: string;
  from_units: string | null;
  to_data_type: string | null;
  to_field: string | null;
  to_field_display_name: string | null;
  to_table_name: string | null;
  omit?: boolean; // optional, used for omitting columns
  isExtraData?: boolean; // used internally, not part of the API
  isNewColumn?: boolean; // used internally, not part of the API
  hasDuplicate?: boolean; // used internally, not part of the API
}

export type MappedData = {
  mappings: DataMappingRow[];
}

export type MappingResultsResponse = {
  status: string;
  properties: Record<string, unknown>[];
  tax_lots: Record<string, unknown>[];
}

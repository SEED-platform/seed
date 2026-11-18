import type { Column } from '../column'

export type MappingSuggestionsResponse = {
  status: string;
  property_columns: Column[];
  suggested_column_mappings: SuggestedColumnMapping;
  taxlot_columns: Column[];
}

export type SuggestedColumnMapping = Record<string, [table: string, columnName: string, confidence: number]>

export type RawColumnNamesResponse = {
  status: string;
  raw_columns: string[];
}

export type FirstFiveRowsResponse = {
  status: string;
  first_five_rows: Record<string, unknown>[];
}

export type MatchingResultsResponse = {
  import_file_records: number;
  multiple_cycle_upload: boolean;
  properties: MatchingResults;
  tax_lots: MatchingResults;
}

export type MatchingResults = {
  duplicates_against_existing: number;
  duplicates_within_file: number;
  duplicates_within_file_errors: number;
  geocode_not_possible: number;
  geocoded_census_geocoder: number;
  geocoded_high_confidence: number;
  geocoded_low_confidence: number;
  geocoded_manually: number;
  initial_incoming: number;
  merges_against_existing: number;
  merges_against_existing_errors: number;
  merges_between_existing: number;
  merges_within_file: number;
  merges_within_file_errors: number;
  new: number;
  new_errors: number;
}
